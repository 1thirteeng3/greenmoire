# CRITICAL: load .env BEFORE any core imports that validate env vars at module level
import os
from pathlib import Path

# Load .env manually so it works regardless of dotenv being installed
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ[key.strip()] = value.strip()

import asyncio
import logging

from core.bootstrap import ApplicationContainer
from core.infrastructure.event_bus import AsyncRedisEventBus
from core.infrastructure.persistence.session import create_session_factory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Inicializando o Cérebro do Grimoire OS (Orchestrator Worker)...")

    bus = AsyncRedisEventBus()
    session_factory = create_session_factory()

    app_container = ApplicationContainer(bus=bus, session_factory=session_factory)

    # Inicia as rotinas assíncronas do worker
    await app_container.start_all_workers()

    logger.info("Worker ativo e à escuta na stream 'stream:user_input'...")

    # Mantém o processo vivo indefinidamente
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        logger.info("Worker interrompido.")
    except KeyboardInterrupt:
        logger.info("Worker desligado pelo utilizador.")
    finally:
        await bus.close()


if __name__ == "__main__":
    asyncio.run(main())
