"""
WebSocket Gateway – Canal Bidirecional de Telemetria Cognitiva
Permite ao frontend receber frames de trace, plano e resposta em tempo real.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
import time
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from core.api.schemas import (
    ChatRequest,
    ConnectedFrame,
    ErrorFrame,
    PlanFrame,
    PlanStep,
    PlanStepUpdateFrame,
    ResponseFrame,
    TraceFrame,
    WsFrameType,
)
from core.api.security import API_SECRET_TOKEN
from core.infrastructure.event_bus import AsyncRedisEventBus
from core.schemas.events import BaseEvent, EventHeader

logger = logging.getLogger(__name__)

router = APIRouter()

# Bus singleton para o WebSocket handler (instâncias são leves)
_bus: Optional[AsyncRedisEventBus] = None


def _get_bus() -> AsyncRedisEventBus:
    global _bus
    if _bus is None:
        _bus = AsyncRedisEventBus()
    return _bus


# ==========================================
# HELPERS DE SERIALIZAÇÃO
# ==========================================


def _ts() -> int:
    return int(time.time() * 1000)


async def _send_safe(ws: WebSocket, frame: dict) -> bool:
    """Envia um frame JSON com tratamento de erros. Retorna False se a conexão morreu."""
    try:
        await ws.send_json(frame)
        return True
    except Exception:
        return False


# ==========================================
# ENDPOINT PRINCIPAL
# ==========================================


@router.websocket("/ws/cognitive-stream")
async def cognitive_stream_ws(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None, alias="token"),
):
    """
    Canal WebSocket bidirecional para o Grimoire UX.

    Autenticação via query param `?token=<API_SECRET_TOKEN>`.
    Protocolo de frames JSON:
        → client envia:  { "prompt": "...", "context_hints": [...] }
        ← server emite:  TraceFrame | PlanFrame | PlanStepUpdateFrame | ResponseFrame | ErrorFrame
    """
    # --- Autenticação precoce (antes de accept) ---
    if not token or token != API_SECRET_TOKEN:
        await websocket.close(
            code=4001, reason="Credenciais inválidas. Token ausente ou incorreto."
        )
        logger.warning("WS: Tentativa de conexão não autorizada rejeitada.")
        return

    await websocket.accept()
    session_id = f"ws-{uuid.uuid4().hex[:8]}"
    bus = _get_bus()

    logger.info("WS Session [%s] estabelecida.", session_id)

    # Handshake inicial
    await _send_safe(websocket, ConnectedFrame(session_id=session_id).model_dump())

    try:
        while True:
            # --- Aguardar mensagem do cliente ---
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
            except asyncio.TimeoutError:
                # Heartbeat para manter a conexão viva
                await _send_safe(
                    websocket, {"type": WsFrameType.HEARTBEAT, "ts": _ts()}
                )
                continue

            # --- Validação do payload ---
            try:
                request = ChatRequest.model_validate_json(raw)
            except Exception as parse_err:
                await _send_safe(
                    websocket,
                    ErrorFrame(
                        trace_id="parse_error",
                        code="INVALID_PAYLOAD",
                        message=f"Payload inválido: {parse_err}",
                    ).model_dump(),
                )
                continue

            trace_id = f"ws-{uuid.uuid4().hex[:10]}"
            reply_stream = f"stream:ws_reply:{trace_id}"
            trace_stream = f"stream:trace:{trace_id}"

            # --- Emitir ao bus ---
            event = BaseEvent(
                header=EventHeader(
                    trace_id=trace_id,
                    source_service="ws_gateway",
                    event_type="user_prompt_received",
                ),
                payload={
                    "prompt": request.prompt,
                    "context_hints": request.context_hints,
                    "session_id": session_id,
                },
                metadata={"reply_to_stream": reply_stream},
            )
            await bus.publish("stream:user_input", event)

            logger.info(
                "WS [%s] → Prompt injetado no bus. trace_id=%s", session_id, trace_id
            )

            # --- Consumir trace + resposta em paralelo ---
            await _stream_cognitive_cycle(
                websocket=websocket,
                bus=bus,
                trace_id=trace_id,
                reply_stream=reply_stream,
                trace_stream=trace_stream,
            )

    except WebSocketDisconnect:
        logger.info("WS Session [%s] desconectada pelo cliente.", session_id)
    except Exception as exc:
        logger.error("WS Session [%s] erro fatal: %s", session_id, exc)
        await _send_safe(
            websocket,
            ErrorFrame(
                trace_id=session_id,
                code="INTERNAL_ERROR",
                message="Falha interna no gateway. Tente reconectar.",
            ).model_dump(),
        )


# ==========================================
# STREAMING DO CICLO COGNITIVO
# ==========================================


async def _stream_cognitive_cycle(
    websocket: WebSocket,
    bus: AsyncRedisEventBus,
    trace_id: str,
    reply_stream: str,
    trace_stream: str,
    timeout_seconds: float = 120.0,
) -> None:
    """
    Loop assíncrono que consome o stream de trace E o stream de resposta final,
    encaminhando cada evento para o WebSocket em tempo real.
    """
    start = asyncio.get_running_loop().time()
    last_trace_id = "0"
    last_reply_id = "$"
    response_delivered = False

    while (
        asyncio.get_running_loop().time() - start
    ) < timeout_seconds and not response_delivered:
        elapsed = asyncio.get_running_loop().time() - start

        # --- Ler do stream de trace (sem bloqueio longo) ---
        try:
            trace_msgs = await asyncio.wait_for(
                bus.client.xread({trace_stream: last_trace_id}, count=10, block=0),
                timeout=0.3,
            )
        except asyncio.TimeoutError:
            trace_msgs = []
        except Exception:
            trace_msgs = []

        if trace_msgs:
            for _stream, messages in trace_msgs:
                for msg_id, msg_data in messages:
                    last_trace_id = msg_id
                    frame = await _parse_trace_frame(msg_data, trace_id)
                    if frame:
                        alive = await _send_safe(websocket, frame)
                        if not alive:
                            return

        # --- Ler do stream de resposta final ---
        try:
            reply_msgs = await asyncio.wait_for(
                bus.client.xread({reply_stream: last_reply_id}, count=5, block=0),
                timeout=0.3,
            )
        except asyncio.TimeoutError:
            reply_msgs = []
        except Exception:
            reply_msgs = []

        if reply_msgs:
            for _stream, messages in reply_msgs:
                for msg_id, msg_data in messages:
                    last_reply_id = msg_id
                    raw_json = msg_data.get("payload")
                    if not raw_json:
                        continue
                    try:
                        reply_event = BaseEvent.model_validate_json(raw_json)
                    except Exception:
                        continue

                    if (
                        reply_event.header.trace_id == trace_id
                        and reply_event.header.event_type
                        == "cognitive_response_delivered"
                    ):
                        p = reply_event.payload
                        frame = ResponseFrame(
                            trace_id=trace_id,
                            content=p.get("response", ""),
                            tier_used=p.get("tier_used", "unknown"),
                            primary_intent=p.get("primary_intent", "unknown"),
                            audit_approved=p.get("audit_approved", True),
                            audit_critique=p.get("audit_critique"),
                            metadata={
                                "tokens_used": p.get("tokens_used"),
                                "elapsed_ms": int(
                                    (asyncio.get_running_loop().time() - start) * 1000
                                ),
                            },
                        )
                        await _send_safe(websocket, frame.model_dump())
                        response_delivered = True
                        logger.info(
                            "WS trace_id=%s → Resposta entregue em %.1fs.",
                            trace_id,
                            elapsed,
                        )
                        return

        await asyncio.sleep(0.05)

    # Timeout sem resposta
    if not response_delivered:
        logger.error(
            "WS trace_id=%s → Timeout aguardando resposta do orquestrador.", trace_id
        )
        await _send_safe(
            websocket,
            ErrorFrame(
                trace_id=trace_id,
                code="ORCHESTRATOR_TIMEOUT",
                message="O orquestrador demorou demasiado. A tarefa pode ainda estar a correr.",
            ).model_dump(),
        )


async def _parse_trace_frame(msg_data: dict, trace_id: str) -> Optional[dict]:
    """Converte mensagens do Redis em frames de trace tipados."""
    raw_json = msg_data.get("payload")
    if not raw_json:
        return None

    try:
        event = BaseEvent.model_validate_json(raw_json)
    except Exception:
        return None

    event_type = event.header.event_type
    p = event.payload

    if event_type == "cognitive_trace":
        return TraceFrame(
            trace_id=trace_id,
            agent=p.get("agent", "System"),
            action=p.get("action", ""),
            tier=p.get("tier"),
            timestamp_ms=p.get("timestamp_ms", _ts()),
        ).model_dump()

    if event_type == "cognitive_plan":
        steps = [
            PlanStep(
                id=s["id"],
                description=s["description"],
                tools=s.get("tools", []),
                status=s.get("status", "pending"),
            )
            for s in p.get("steps", [])
        ]
        return PlanFrame(
            trace_id=trace_id,
            plan_rationale=p.get("plan_rationale", ""),
            steps=steps,
        ).model_dump()

    if event_type == "cognitive_plan_step_update":
        return PlanStepUpdateFrame(
            trace_id=trace_id,
            step_id=p.get("step_id", 0),
            status=p.get("status", "pending"),
        ).model_dump()

    return None
