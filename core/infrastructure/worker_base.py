import asyncio
import logging
import traceback
from typing import Callable, Awaitable
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.exc import IntegrityError
from core.infrastructure.event_bus import AsyncRedisEventBus
from core.schemas.events import BaseEvent

logger = logging.getLogger(__name__)

DLQ_STREAM = "stream:dlq:core"


class BaseEventWorker:
    def __init__(
        self,
        bus: AsyncRedisEventBus,
        session_factory: async_sessionmaker[AsyncSession],
        stream_name: str,
        group_name: str,
        consumer_name: str
    ):
        self.bus = bus
        self.session_factory = session_factory
        self.stream_name = stream_name
        self.group_name = group_name
        self.consumer_name = consumer_name
        self._running = False

    async def start(self, handler_func: Callable[[BaseEvent, AsyncSession], Awaitable[None]]):
        await self.bus.setup_consumer_group(self.stream_name, self.group_name)
        self._running = True
        logger.info(f"Worker {self.consumer_name} iniciado no stream {self.stream_name}.")

        while self._running:
            await self._process_batch(handler_func, is_recovery=False)
            await self._process_batch(handler_func, is_recovery=True)
            await asyncio.sleep(0.1)

    async def stop(self):
        self._running = False
        await self.bus.close()

    async def _process_batch(self, handler_func: Callable, is_recovery: bool):
        if is_recovery:
            messages = await self.bus.reclaim_pending_messages(self.stream_name, self.group_name, self.consumer_name)
        else:
            messages = await self.bus.consume(self.stream_name, self.group_name, self.consumer_name)

        for message_id, event in messages:
            async with self.session_factory() as session:
                try:
                    await handler_func(event, session)
                    await session.commit()
                    await self.bus.acknowledge(self.stream_name, self.group_name, message_id)

                except (ValidationError, IntegrityError) as fatal_error:
                    await session.rollback()
                    await self._send_to_dlq(event, message_id, fatal_error, "FATAL_DB_OR_CONTRACT")
                    await self.bus.acknowledge(self.stream_name, self.group_name, message_id)

                except Exception as e:
                    await session.rollback()
                    logger.warning(f"Erro transiente no evento {message_id}: {e}. Retentativa gerenciada pelo PEL.")

    async def _send_to_dlq(self, event: BaseEvent, original_message_id: str, exception: Exception, error_type: str):
        dlq_payload = {
            "original_stream": self.stream_name,
            "original_message_id": original_message_id,
            "error_type": error_type,
            "error_message": str(exception),
            "traceback": traceback.format_exc(),
            "event_dump": event.model_dump()
        }
        try:
            dlq_event = BaseEvent(header=event.header, payload=dlq_payload, metadata={"status": "poison_pill"})
            dlq_event.header.event_type = "system_error_dlq"
            await self.bus.publish(DLQ_STREAM, dlq_event)
            logger.error(f"Evento {original_message_id} movido para DLQ.")
        except Exception as dlq_e:
            logger.critical(f"Falha ao escrever na DLQ: {dlq_e}")
