import uuid
import json
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.infrastructure.event_bus import AsyncRedisEventBus
from core.schemas.events import BaseEvent, EventHeader

logger = logging.getLogger(__name__)

router = APIRouter()
bus = AsyncRedisEventBus()


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket):
    """
    Conexão persistente para streaming de eventos cognitivos em tempo real.
    """
    await websocket.accept()
    logger.info("Nova conexão WebSocket estabelecida com o Frontend.")

    # Criamos uma stream de resposta única e temporária para esta conexão
    session_id = f"ws-{uuid.uuid4().hex[:8]}"
    reply_stream = f"stream:frontend_output:{session_id}"

    try:
        while True:
            # 1. Aguarda a mensagem (prompt) do Frontend
            data = await websocket.receive_text()
            payload = json.loads(data)
            user_prompt = payload.get("prompt", "")

            trace_id = f"trc-{uuid.uuid4().hex[:8]}"

            # 2. Injeta o evento no Orquestrador
            event = BaseEvent(
                header=EventHeader(
                    trace_id=trace_id,
                    source_service="api_gateway_ws",
                    event_type="user_prompt_received",
                ),
                payload={"prompt": user_prompt},
                metadata={"reply_to_stream": reply_stream},
            )
            await bus.publish("stream:user_input", event)

            # Avisamos o Frontend que o processamento começou
            await websocket.send_json(
                {
                    "type": "status",
                    "message": "Classificando intenção...",
                    "trace_id": trace_id,
                }
            )

            # 3. Loop de escuta do Redis (Polling na stream de resposta dedicada)
            last_id = "$"
            start_time = asyncio.get_event_loop().time()
            timeout_seconds = 60.0  # Timeout de segurança

            while (asyncio.get_event_loop().time() - start_time) < timeout_seconds:
                # Escuta o Redis sem bloquear totalmente o loop assíncrono
                streams = await bus.client.xread(
                    {reply_stream: last_id}, count=10, block=500
                )

                if streams:
                    for stream_name, messages in streams:
                        for msg_id, msg_data in messages:
                            last_id = msg_id

                            try:
                                reply_event = BaseEvent.model_validate_json(
                                    msg_data["payload"]
                                )
                            except Exception as e:
                                logger.error(f"Erro ao parsear resposta: {e}")
                                continue

                            # Se for a resposta final
                            if (
                                reply_event.header.event_type
                                == "cognitive_response_delivered"
                            ):
                                execution_time = int(
                                    (asyncio.get_event_loop().time() - start_time)
                                    * 1000
                                )

                                await websocket.send_json(
                                    {
                                        "type": "final_response",
                                        "trace_id": reply_event.header.trace_id,
                                        "role": "grimoire",
                                        "content": reply_event.payload.get(
                                            "response", ""
                                        ),
                                        "metadata": {
                                            "tier_used": reply_event.payload.get(
                                                "tier_used"
                                            ),
                                            "primary_intent": reply_event.payload.get(
                                                "primary_intent"
                                            ),
                                            "execution_time_ms": execution_time,
                                            # Podemos adicionar o Auditor Critique aqui no futuro
                                        },
                                    }
                                )
                                break  # Sai do loop de escuta para esta mensagem
                await asyncio.sleep(0.1)  # Previne CPU clipping

    except WebSocketDisconnect:
        logger.info(f"Frontend desconectado da sessão {session_id}.")
    except Exception as e:
        logger.error(f"Erro no WebSocket: {e}")
        await websocket.close()
