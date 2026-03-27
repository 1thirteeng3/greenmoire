import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from core.api.security import RedisRateLimiter, verify_auth_token
from core.infrastructure.event_bus import AsyncRedisEventBus
from core.schemas.events import BaseEvent, EventHeader

logger = logging.getLogger(__name__)

rate_limiter = RedisRateLimiter()
bus = AsyncRedisEventBus()
router = APIRouter(
    dependencies=[
        Depends(verify_auth_token),
        Depends(rate_limiter.check_rate_limit),
    ]
)


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    context_hints: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    trace_id: str
    response: str
    tier_used: str
    primary_intent: str


@router.post("/sync", response_model=ChatResponse)
async def chat_synchronous(request: ChatRequest) -> ChatResponse:
    """
    Ponte HTTP -> Event Bus -> HTTP.
    Injeta prompt no stream de entrada e aguarda resposta correlacionada.
    """
    trace_id = f"req-{uuid.uuid4().hex[:8]}"
    reply_stream = "stream:frontend_output"

    event = BaseEvent(
        header=EventHeader(
            trace_id=trace_id,
            source_service="api_gateway",
            event_type="user_prompt_received",
        ),
        payload={
            "prompt": request.prompt,
            "context_hints": request.context_hints,
        },
        metadata={"reply_to_stream": reply_stream},
    )

    logger.info("[%s] API Gateway: injetando prompt no barramento.", trace_id)
    await bus.publish("stream:user_input", event)

    timeout_seconds = 60.0
    start_time = asyncio.get_running_loop().time()
    last_id = "$"

    while (asyncio.get_running_loop().time() - start_time) < timeout_seconds:
        streams = await bus.client.xread({reply_stream: last_id}, count=20, block=1000)
        if not streams:
            continue

        for _stream_name, messages in streams:
            for msg_id, msg_data in messages:
                last_id = msg_id
                raw_json = msg_data.get("payload")
                if not raw_json:
                    continue

                try:
                    reply_event = BaseEvent.model_validate_json(raw_json)
                except Exception:
                    logger.warning(
                        "[%s] API Gateway: payload invalido no stream de saida.",
                        trace_id,
                    )
                    continue

                if (
                    reply_event.header.trace_id == trace_id
                    and reply_event.header.event_type == "cognitive_response_delivered"
                ):
                    logger.info(
                        "[%s] API Gateway: resposta recebida do orquestrador.", trace_id
                    )
                    return ChatResponse(
                        trace_id=trace_id,
                        response=reply_event.payload.get("response", ""),
                        tier_used=reply_event.payload.get("tier_used", "unknown"),
                        primary_intent=reply_event.payload.get(
                            "primary_intent", "unknown"
                        ),
                    )

    logger.error(
        "[%s] API Gateway: timeout aguardando resposta do orquestrador.", trace_id
    )
    return ChatResponse(
        trace_id=trace_id,
        response=(
            "O sistema demorou demasiado tempo a responder. "
            "A tarefa pode ainda estar a correr em background."
        ),
        tier_used="timeout",
        primary_intent="timeout",
    )
