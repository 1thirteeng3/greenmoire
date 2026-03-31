import os
import hashlib
import logging
import asyncio
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.infrastructure.worker_base import BaseEventWorker
from core.infrastructure.event_bus import AsyncRedisEventBus
from core.schemas.events import BaseEvent, EventHeader
from core.models.memory_models import SemanticMemory, ObsidianSyncState

logger = logging.getLogger(__name__)


class SyncEngineWorker(BaseEventWorker):
    """
    Daemon responsável pela sincronização unidirecional (DB -> Obsidian) e
    garantia da Soberania Cognitiva Humana via bloqueios de escrita e deteção de conflitos.
    """

    def __init__(
        self,
        bus: AsyncRedisEventBus,
        session_factory: async_sessionmaker[AsyncSession],
        vault_path: str = os.getenv("OBSIDIAN_VAULT_PATH", "./2ndBrain"),
        stream_name: str = "stream:memory",
        group_name: str = "sync_engine_group",
        consumer_name: str = "sync_worker_1",
    ):
        super().__init__(bus, session_factory, stream_name, group_name, consumer_name)
        self.vault_path = Path(vault_path)

        # Garante que o cofre existe
        self.vault_path.mkdir(parents=True, exist_ok=True)

    async def start_service(self):
        logger.info(
            f"Inicializando SyncEngine Daemon apontado para o cofre: {self.vault_path}"
        )
        await self.start(self.handle_event)

    async def handle_event(self, event: BaseEvent, session: AsyncSession):
        """Interceta eventos de gravação/atualização de memória para espelhar no Obsidian."""
        event_type = event.header.event_type

        # O SyncEngine só reage a memórias semânticas persistidas
        if event_type in ["semantic_memory_stored", "semantic_memory_updated"]:
            memory_id = event.payload.get("memory_id")
            if not memory_id:
                raise ValueError("O payload do evento deve conter o 'memory_id'.")

            await self._process_sync(memory_id, event.header.trace_id, session)
        elif event_type == "error_memory_resolved":
            await self._process_error_audit_sync(event.payload, session)

    # ==========================================
    # LÓGICA CORE DE SINCRONIZAÇÃO E CONFLITO
    # ==========================================

    async def _process_sync(self, memory_id: str, trace_id: str, session: AsyncSession):
        # 1. Recuperar a memória e o estado de sincronização
        memory_stmt = select(SemanticMemory).where(SemanticMemory.id == memory_id)
        memory_result = await session.execute(memory_stmt)
        memory = memory_result.scalar_one_or_none()

        if not memory:
            logger.error(
                f"Memória {memory_id} não encontrada no banco. Abortando sync."
            )
            return

        sync_stmt = select(ObsidianSyncState).where(
            ObsidianSyncState.semantic_memory_id == memory_id
        )
        sync_result = await session.execute(sync_stmt)
        sync_state = sync_result.scalar_one_or_none()

        # 2. Gerar o conteúdo Markdown com Frontmatter Injetado
        markdown_content = self._generate_markdown(memory, trace_id)
        new_hash = self._calculate_hash(markdown_content)

        # 3. Ramificação Lógica: Novo ficheiro vs Atualização
        if not sync_state:
            await self._create_new_file(memory, markdown_content, new_hash, session)
        else:
            await self._update_existing_file(
                sync_state, memory, markdown_content, new_hash, trace_id, session
            )

    async def _create_new_file(
        self,
        memory: SemanticMemory,
        content: str,
        content_hash: str,
        session: AsyncSession,
    ):
        """Cria um novo ficheiro Markdown no cofre e regista o estado inicial."""
        # Sanitização simples para o nome do ficheiro (Domínio + ID parcial)
        file_name = f"{memory.domain}_{str(memory.id)[:8]}.md".replace(" ", "_")
        file_path = self.vault_path / memory.domain / file_name

        # Garante que o diretório de domínio existe
        file_path.parent.mkdir(parents=True, exist_ok=True)

        await self._write_file(file_path, content)

        new_sync_state = ObsidianSyncState(
            semantic_memory_id=memory.id,
            file_path=str(file_path),
            last_sync_hash=content_hash,
            is_locked=False,
        )
        session.add(new_sync_state)
        logger.debug(f"Novo ficheiro criado e sincronizado: {file_path}")

    async def _update_existing_file(
        self,
        sync_state: ObsidianSyncState,
        memory: SemanticMemory,
        new_content: str,
        new_hash: str,
        trace_id: str,
        session: AsyncSession,
    ):
        """Aplica o protocolo rigoroso de Write Lock e SHA-256."""
        if sync_state.is_locked:
            logger.warning(
                f"Ficheiro {sync_state.file_path} está bloqueado. Sync abortado."
            )
            return

        target_path = Path(sync_state.file_path)

        # Mecanismo de Auto-Cura (Self-Healing)
        if not target_path.exists():
            logger.info(
                f"Ficheiro {target_path} não encontrado. Iniciando varredura de cura (Self-Healing)..."
            )
            found_path = await self._scan_for_grimoire_id(str(memory.id))
            if found_path:
                logger.info(
                    f"Ficheiro reencontrado em: {found_path}. Atualizando path no banco."
                )
                sync_state.file_path = str(found_path)
                target_path = found_path
            else:
                logger.warning(
                    "Ficheiro deletado pelo utilizador. Recriando no local original."
                )

        # Se o ficheiro existe, verificar edição manual (SHA-256)
        if target_path.exists():
            disk_content = await self._read_file(target_path)
            disk_hash = self._calculate_hash(disk_content)

            if disk_hash != sync_state.last_sync_hash:
                # O protocolo de Soberania Cognitiva foi acionado
                await self._handle_conflict(
                    sync_state, target_path, new_content, trace_id
                )
                return

        # Caminho Feliz: Ficheiro intacto, sobrescrever com novos dados do banco
        await self._write_file(target_path, new_content)
        sync_state.last_sync_hash = new_hash
        logger.debug(f"Ficheiro atualizado com sucesso: {target_path}")

    async def _handle_conflict(
        self,
        sync_state: ObsidianSyncState,
        original_path: Path,
        new_content: str,
        trace_id: str,
    ):
        """Gera nota de bifurcação, tranca a tabela e notifica o barramento."""
        logger.warning(
            f"CONFLITO DETETADO no ficheiro: {original_path}. Edição manual humana sobrepôs-se ao sistema."
        )

        # 1. Trancar o estado de sincronização
        sync_state.is_locked = True

        # 2. Criar a nota de bifurcação
        conflict_file_path = original_path.with_name(
            f"{original_path.stem}_(Grimoire_Update){original_path.suffix}"
        )
        await self._write_file(conflict_file_path, new_content)

        # 3. Emitir evento de conflito para a UI e resolução futura
        conflict_event = BaseEvent(
            header=EventHeader(
                trace_id=trace_id,
                source_service="sync_engine",
                event_type="sync_conflict_detected",
            ),
            payload={
                "memory_id": str(sync_state.semantic_memory_id),
                "original_file": str(original_path),
                "conflict_file": str(conflict_file_path),
            },
        )
        await self.bus.publish("stream:core_alerts", conflict_event)

    # ==========================================
    # UTILITÁRIOS DE I/O E HASHING (Assíncronos)
    # ==========================================

    def _generate_markdown(self, memory: SemanticMemory, trace_id: str) -> str:
        """Injeta o Frontmatter YAML obrigatório como âncora imutável."""
        metadata = memory.metadata_json or {}
        frontmatter = {
            "grimoire_id": str(memory.id),
            "trace_id": trace_id,
            "domain": memory.domain,
            "human_verified": memory.human_verified,
            "updated_at": memory.updated_at.isoformat(),
            **metadata,  # Expande as tags/aliases adicionais
        }

        yaml_block = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        return f"---\n{yaml_block}---\n\n{memory.content}\n"

    def _calculate_hash(self, content: str) -> str:
        """Hash SHA-256 para deteção cirúrgica de adulterações."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def _write_file(self, path: Path, content: str):
        """Delega a escrita no disco a uma thread para não bloquear o event loop."""

        def write():
            path.write_text(content, encoding="utf-8")

        await asyncio.to_thread(write)

    async def _read_file(self, path: Path) -> str:
        """Delega a leitura no disco a uma thread."""

        def read():
            return path.read_text(encoding="utf-8")

        return await asyncio.to_thread(read)

    async def _scan_for_grimoire_id(self, target_id: str) -> Optional[Path]:
        """
        Mecanismo de Auto-Cura: Varre os ficheiros markdown no cofre
        à procura do `grimoire_id` no bloco Frontmatter.
        """

        def scan() -> Optional[Path]:
            for root, _, files in os.walk(self.vault_path):
                for file in files:
                    if file.endswith(".md"):
                        file_path = Path(root) / file
                        try:
                            # Lemos apenas os primeiros 1000 caracteres para ser rápido
                            with open(file_path, "r", encoding="utf-8") as f:
                                header = f.read(1000)
                                if f"grimoire_id: {target_id}" in header:
                                    return file_path
                        except Exception:
                            continue
            return None

        return await asyncio.to_thread(scan)

    async def _process_error_audit_sync(
        self, payload: Dict[str, Any], session: AsyncSession
    ):
        """Mantém um log de auditoria física contínuo no Obsidian."""
        _ = session  # reservado para futura consistência transacional com estado relacional
        audit_file_path = (
            self.vault_path / "System_Meta" / "Grimoire_Auditoria_Cognitiva.md"
        )
        audit_file_path.parent.mkdir(parents=True, exist_ok=True)

        error_id = payload.get("error_id")
        original_output = payload.get("original_output")
        human_correction = payload.get("human_correction")
        timestamp = payload.get("resolved_at")

        # Formatação do bloco de auditoria
        audit_entry = (
            f"\n## Resolução: {timestamp}\n"
            f"- **ID do Erro:** `{error_id}`\n"
            f"- **Saída Alucinada/Incorreta:** {original_output}\n"
            f"- **Correção Humana Aplicada:** {human_correction}\n"
            f"---\n"
        )

        # Append assíncrono ao ficheiro
        def _append_audit():
            # Se o ficheiro não existir, cria com um cabeçalho
            if not audit_file_path.exists():
                audit_file_path.write_text(
                    "# Registro de Calibração e Correções do Grimoire\n\n"
                    "Este ficheiro documenta a evolução cognitiva do sistema baseada na intervenção humana.\n",
                    encoding="utf-8",
                )

            with open(audit_file_path, "a", encoding="utf-8") as f:
                f.write(audit_entry)

        await asyncio.to_thread(_append_audit)
        logger.info(f"Auditoria de erro {error_id} sincronizada no Obsidian.")
