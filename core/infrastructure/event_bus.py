import redis
import json
from typing import Callable, List, Dict
from core.schemas.events import BaseEvent

class RedisEventBus:
    def __init__(self, host: str = 'localhost', port: int = 6379):
        self.redis_client = redis.Redis(host=host, port=port, decode_responses=True)

    def publish(self, stream_name: str, event: BaseEvent) -> str:
        """
        Publica um evento em um Redis Stream.
        """
        event_dict = {"data": event.model_dump_json()}
        # MAXLEN limita o tamanho do stream para evitar OOM (Out of Memory)
        message_id = self.redis_client.xadd(stream_name, event_dict, maxlen=100000)
        return message_id

    def setup_consumer_group(self, stream_name: str, group_name: str):
        """
        Cria um Consumer Group. Ignora se já existir.
        """
        try:
            # ID '0-0' cria o grupo a partir do início, '$' a partir dos novos.
            self.redis_client.xgroup_create(stream_name, group_name, id='0-0', mkstream=True)
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    def consume(self, stream_name: str, group_name: str, consumer_name: str, batch_size: int = 10) -> List[Dict]:
        """
        Lê mensagens do stream para este consumer group.
        """
        # '>' significa ler mensagens que nunca foram entregues a outros consumidores neste grupo
        streams = {stream_name: '>'}
        messages = self.redis_client.xreadgroup(group_name, consumer_name, streams, count=batch_size, block=2000)
        
        parsed_events = []
        if messages:
            for stream, msgs in messages:
                for message_id, msg_data in msgs:
                    event_json = msg_data.get('data')
                    parsed_events.append({
                        "id": message_id,
                        "event": BaseEvent.model_validate_json(event_json)
                    })
        return parsed_events

    def acknowledge(self, stream_name: str, group_name: str, message_id: str):
        """
        Confirma que a mensagem foi processada com sucesso.
        """
        self.redis_client.xack(stream_name, group_name, message_id)
