from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field


def current_utc() -> datetime:
    return datetime.now(timezone.utc)


class SyncLockStatus(str, Enum):
    UNLOCKED = "unlocked"
    LOCKED = "locked"
    STALE_LOCK = "stale_lock"


class SyncJobStatus(str, Enum):
    PENDING = "pending"
    SYNCED = "synced"
    CONFLICT = "conflict"
    IO_ERROR = "io_error"


class ObsidianSyncState(BaseModel):
    """
    Projeção de infraestrutura para sincronização com sistema de arquivos.
    Separado de SemanticMemory para manter pureza do domínio cognitivo.
    """

    memory_id: str = Field(..., description="ID da memória semântica de referência.")
    file_path: str = Field(..., description="Caminho absoluto/relativo no vault Obsidian.")
    lock_status: SyncLockStatus = Field(default=SyncLockStatus.UNLOCKED)
    write_lock: bool = Field(default=False, description="True quando o arquivo está em seção crítica de escrita.")
    last_sync_hash: str | None = Field(
        default=None,
        description="Hash do conteúdo sincronizado por último para detectar divergência manual.",
    )
    status: SyncJobStatus = Field(default=SyncJobStatus.PENDING)
    last_synced_at: datetime | None = Field(default=None)
    updated_at: datetime = Field(default_factory=current_utc)
