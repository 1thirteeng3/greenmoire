import logging
import os
import time

from fastapi import HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

security_scheme = HTTPBearer()
API_SECRET_TOKEN = os.getenv("API_SECRET_TOKEN", "grimoire_super_secret_token_2026")
RATE_LIMIT = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "20"))


async def verify_auth_token(
    credentials: HTTPAuthorizationCredentials = Security(security_scheme),
) -> str:
    """Validacao estrita de identidade via bearer token."""
    if credentials.credentials != API_SECRET_TOKEN:
        logger.warning("Tentativa de acesso nao autorizada ao Grimoire API.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invalidas ou token expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


class RedisRateLimiter:
    """
    Limite de taxa por IP (fixed window/minuto) com Redis.
    Protege contra exaustao de chamadas e abuso do gateway.
    """

    def __init__(
        self, redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    ):
        self.redis = Redis.from_url(redis_url, decode_responses=True)

    async def check_rate_limit(self, request: Request) -> None:
        client_ip = request.headers.get("x-forwarded-for")
        if not client_ip:
            client_ip = request.client.host if request.client else "unknown"
        else:
            client_ip = client_ip.split(",")[0].strip()

        current_minute = int(time.time() // 60)
        redis_key = f"rate_limit:{client_ip}:{current_minute}"

        request_count = await self.redis.incr(redis_key)
        if request_count == 1:
            await self.redis.expire(redis_key, 60)

        if request_count > RATE_LIMIT:
            logger.warning("Rate limit excedido para o IP %s.", client_ip)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Limite de requisicoes excedido. Acalme o fluxo de pensamentos.",
            )
