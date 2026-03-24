import logging
from typing import List, Tuple
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import ResponseError
from core.schemas.events import BaseEvent

logger = logging.getLogger(__name__)

class AsyncRedisEventBus:
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.pool = ConnectionPool.from_url(redis_url, decode_responses=True)
        self.client = Redis(connection_pool=self.pool)

    async def publish(self, stream_name: str, event: BaseEvent, maxlen: int = 100000) -> str:
        """Publica evento de forma assíncrona com limite de tamanho de stream."""
        event_data = {"payload": event.model_dump_json()}
        message_id = await self.client.xadd(
            name=stream_name,
            fields=event_data,
            maxlen=maxlen,
            approximate=True
        )
        return message_id

    async def setup_consumer_group(self, stream_name: str, group_name: str) -> None:
        """Garante a existência do stream e do Consumer Group."""
        try:
            await self.client.xgroup_create(name=stream_name, groupname=group_name, id='0-0', mkstream=True)
        except ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    async def consume(self, stream_name: str, group_name: str, consumer_name: str, batch_size: int = 10, block_ms: int = 2000) -> List[Tuple[str, BaseEvent]]:
        """Lê novas mensagens destinadas a este consumidor."""
        try:
            streams = {stream_name: '>'}
            messages = await self.client.xreadgroup(
                groupname=group_name, consumername=consumer_name, streams=streams, count=batch_size, block=block_ms
            )
            return self._parse_messages(messages)
        except Exception as e:
            logger.error(f"Erro na leitura do stream {stream_name}: {e}")
            return []

    async def acknowledge(self, stream_name: str, group_name: str, message_id: str) -> None:
        """Confirma o processamento, removendo a mensagem da PEL."""
        await self.client.xack(stream_name, group_name, message_id)

    async def reclaim_pending_messages(self, stream_name: str, group_name: str, consumer_name: str, min_idle_time_ms: int = 60000, batch_size: int = 10) -> List[Tuple[str, BaseEvent]]:
        """Recupera mensagens pendentes de workers mortos via XAUTOCLAIM."""
        try:
            claim_result = await self.client.xautoclaim(
                name=stream_name, groupname=group_name, consumername=consumer_name, min_idle_time=min_idle_time_ms, start_id='0-0', count=batch_size
            )
            claimed_messages = claim_result[1] 
            if claimed_messages:
                return self._parse_messages([[stream_name, claimed_messages]])
            return []
        except Exception as e:
            logger.error(f"Erro ao reivindicar mensagens pendentes no stream {stream_name}: {e}")
            return []

    def _parse_messages(self, raw_messages: list) -> List[Tuple[str, BaseEvent]]:
        parsed_events = []
        if not raw_messages:
            return parsed_events
        for stream, msgs in raw_messages:
            for message_id, msg_data in msgs:
                try:
                    raw_json = msg_data.get('payload')
                    event = BaseEvent.model_validate_json(raw_json)
                    parsed_events.append((message_id, event))
                except Exception as e:
                    logger.critical(f"Falha fatal de serialização na mensagem {message_id}: {e}")
        return parsed_events

    async def close(self):
        await self.pool.disconnect()
