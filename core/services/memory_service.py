from integrations.mem0_wrapper import Mem0Wrapper
from integrations.ori_mnemos_wrapper import OriMnemosWrapper
from core.repositories.memory_repository import MemoryRepository
from core.models.memory_models import MemoryEntry, MemoryType


class MemoryService:
    def __init__(self, repo: MemoryRepository, mem0: Mem0Wrapper, mnemos: OriMnemosWrapper):
        self.repo = repo
        self.semantic_store = mem0
        self.episodic_store = mnemos

    def record_interaction(self, input_data: str, output_data: str, trace_id: str):
        """Salva o fluxo natural da conversa na memória episódica."""
        self.episodic_store.add(
            content=f"User: {input_data}\nSystem: {output_data}",
            metadata={"trace_id": trace_id, "type": "interaction"},
        )

    def record_error(self, error_description: str, trace_id: str, context: dict):
        """
        Salva na Error Memory. Regra de Governança:
        'System writes, human governs — system cannot delete its own errors'
        """
        error_entry = MemoryEntry(
            id=context.get("id", f"error::{trace_id}"),
            memory_type=MemoryType.ERROR,
            content=error_description,
            metadata_json={"trace_id": trace_id, **(context or {})},
            is_user_validated=False,
            user_annotation=context.get("user_annotation") if context else None,
        )
        self.repo.save_memory(error_entry)

    def extract_semantic_knowledge(self, payload: str):
        """Ingere conhecimento factual na memória semântica."""
        self.semantic_store.add(content=payload)

    def retrieve_cognitive_context(self, query: str) -> dict:
        """
        Busca contexto respeitando a hierarquia de autoridade.
        1. Busca regras e fatos no Personal Vault (via SyncEngine repo)
        2. Busca falhas conhecidas na Error Memory para evitar repetição
        3. Busca contexto geral Semântico/Episódico
        """
        errors = self.repo.get_error_memories()
        semantic = self.semantic_store.search(query=query, limit=5)
        episodic = self.episodic_store.search(query=query, limit=5)
        return {
            "authority_order": ["personal", "error", "rag"],
            "personal": [],
            "errors": [{"id": item.id, "content": item.content} for item in errors],
            "semantic": semantic,
            "episodic": episodic,
        }
