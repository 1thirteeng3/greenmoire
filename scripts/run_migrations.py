from dotenv import load_dotenv
from alembic import command
from alembic.config import Config

from core.config.embedding import load_embedding_config


def main() -> int:
    load_dotenv()
    # Falha cedo se EMBEDDING_MODEL/EMBEDDING_DIMENSION estiverem inválidos.
    load_embedding_config()

    config = Config("alembic.ini")
    command.upgrade(config, "head")
    print("[alembic] upgrade head completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
