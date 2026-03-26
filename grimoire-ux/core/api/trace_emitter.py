"""
TraceEmitter – Telemetria Cognitiva em Tempo Real
Publica eventos de rastreamento por-trace no Redis para consumo via WebSocket.
"""
from __future__ import annotations

import time
import logging
from typing import Optional

from core.infrastructure.event_bus import AsyncRedisEventBus
from core.schemas.events import BaseEvent, EventHeader

logger = logging.getLogger(__name__)


class TraceEmitter:
    """
    Emite eventos de telemetria para o stream Redis de trace de uma sessão específica.
    Injetado no OrchestratorWorker para transparência total do ciclo cognitivo.
    """

    TRACE_STREAM_PREFIX = "stream:trace:"
    TRACE_STREAM_TTL_SECONDS = 300  # 5 min de retenção

    def __init__(self, bus: AsyncRedisEventBus, trace_id: str):
        self.bus = bus
        self.trace_id = trace_id
        self.stream_name = f"{self.TRACE_STREAM_PREFIX}{trace_id}"

    async def emit(
        self,
        agent: str,
        action: str,
        tier: Optional[str] = None,
    ) -> None:
        """Publica um frame de telemetria no stream dedicado ao trace_id."""
        try:
            payload: dict = {
                "agent": agent,
                "action": action,
                "timestamp_ms": int(time.time() * 1000),
            }
            if tier:
                payload["tier"] = tier

            event = BaseEvent(
                header=EventHeader(
                    trace_id=self.trace_id,
                    source_service=f"tracer:{agent.lower()}",
                    event_type="cognitive_trace",
                ),
                payload=payload,
            )
            await self.bus.publish(self.stream_name, event, maxlen=500)

            # Configura TTL no stream para evitar acumulação de lixo cognitivo
            await self.bus.client.expire(self.stream_name, self.TRACE_STREAM_TTL_SECONDS)

        except Exception as exc:
            # TraceEmitter NUNCA deve quebrar o fluxo principal
            logger.warning("TraceEmitter: Falha ao emitir trace [%s]: %s", self.trace_id, exc)

    async def emit_plan(
        self,
        plan_rationale: str,
        steps: list,
    ) -> None:
        """Publica o plano de execução gerado pelo PlannerAgent."""
        try:
            steps_payload = [
                {
                    "id": s.step_id,
                    "description": s.action_description,
                    "tools": s.required_tools,
                    "status": "pending",
                }
                for s in steps
            ]

            event = BaseEvent(
                header=EventHeader(
                    trace_id=self.trace_id,
                    source_service="tracer:planner",
                    event_type="cognitive_plan",
                ),
                payload={
                    "plan_rationale": plan_rationale,
                    "steps": steps_payload,
                    "timestamp_ms": int(time.time() * 1000),
                },
            )
            await self.bus.publish(self.stream_name, event, maxlen=500)
            await self.bus.client.expire(self.stream_name, self.TRACE_STREAM_TTL_SECONDS)

        except Exception as exc:
            logger.warning("TraceEmitter: Falha ao emitir plano [%s]: %s", self.trace_id, exc)

    async def emit_step_update(self, step_id: int, status: str) -> None:
        """Atualiza o status de um passo do plano em execução."""
        try:
            event = BaseEvent(
                header=EventHeader(
                    trace_id=self.trace_id,
                    source_service="tracer:executor",
                    event_type="cognitive_plan_step_update",
                ),
                payload={
                    "step_id": step_id,
                    "status": status,
                    "timestamp_ms": int(time.time() * 1000),
                },
            )
            await self.bus.publish(self.stream_name, event, maxlen=500)
        except Exception as exc:
            logger.warning("TraceEmitter: Falha ao emitir step update [%s]: %s", self.trace_id, exc)
