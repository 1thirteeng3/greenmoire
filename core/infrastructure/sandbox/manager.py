import json
import uuid
import shutil
import difflib
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ImprovementProposal(BaseModel):
    id: str
    target_file: str
    rationale: str
    status: (
        str  # 'pending', 'testing', 'failed', 'awaiting_approval', 'merged', 'rejected'
    )
    test_logs: str = ""


class SandboxManager:
    """
    Controlador de Quarentena de Código (Air-Gapped Environment simulado).
    Nenhum código gerado por IA entra no 'core/' sem passar por esta classe.

    Security contract:
    - stage_proposal(): rejeita qualquer target_file fora de core/ via Path.relative_to()
    - merge_proposal(): só executa se status == 'awaiting_approval' (tests passaram)
    - Backup automático (.bak) antes de qualquer merge físico
    """

    def __init__(self, root_dir: str = "."):
        self.root_path = Path(root_dir).resolve()
        self.sandbox_dir = self.root_path / "sandbox" / "proposals"
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.sandbox_dir / "registry.json"

        if not self.db_path.exists():
            self._save_db({})

    # ------------------------------------------------------------------
    # Registry helpers
    # ------------------------------------------------------------------

    def _load_db(self) -> Dict[str, Any]:
        with open(self.db_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_db(self, db: Dict[str, Any]) -> None:
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)

    # ------------------------------------------------------------------
    # Core pipeline
    # ------------------------------------------------------------------

    def stage_proposal(
        self, target_file: str, new_code: str, rationale: str
    ) -> ImprovementProposal:
        """
        Cria o ambiente isolado para o código mutante.

        Raises:
            PermissionError: se target_file estiver fora da pasta core/.
        """
        # ── SECURITY GATE (CWE-22) ──────────────────────────────────────
        safe_target = Path(target_file).resolve()
        core_boundary = self.root_path / "core"
        try:
            safe_target.relative_to(core_boundary)
        except ValueError:
            logger.critical(
                "VIOLAÇÃO DE SEGURANÇA INTERCEPTADA: MetaAgent tentou escrever em %s",
                safe_target,
            )
            raise PermissionError(
                f"O MetaAgent está restrito a modificar apenas a pasta 'core/'. "
                f"Caminho rejeitado: {safe_target}"
            )
        # ────────────────────────────────────────────────────────────────

        proposal_id = f"pr-{uuid.uuid4().hex[:8]}"
        proposal_folder = self.sandbox_dir / proposal_id
        proposal_folder.mkdir(parents=True)

        # Grava o código mutante na quarentena
        proposed_file = proposal_folder / safe_target.name
        proposed_file.write_text(new_code, encoding="utf-8")

        proposal = ImprovementProposal(
            id=proposal_id,
            target_file=str(safe_target.relative_to(self.root_path)),
            rationale=rationale,
            status="pending",
        )

        db = self._load_db()
        db[proposal_id] = proposal.model_dump()
        self._save_db(db)

        logger.info(
            "Proposta %s criada em quarentena para %s",
            proposal_id,
            proposal.target_file,
        )
        return proposal

    def run_security_tests(self, proposal_id: str) -> Tuple[bool, str]:
        """
        Executa a suíte de testes (pytest) para garantir que a sintaxe é válida
        e que os contratos (interfaces) não foram quebrados.

        Timeout estrito de 45 s para prevenir loops infinitos gerados pela IA.
        """
        db = self._load_db()
        if proposal_id not in db:
            return False, "Proposta inexistente."

        db[proposal_id]["status"] = "testing"
        self._save_db(db)

        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-q", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=45,
                cwd=str(self.root_path),
            )
            success = result.returncode == 0
            # Guarda os últimos 2 000 chars do log (cabeça + cauda)
            raw_output = result.stdout + result.stderr
            logs = raw_output[-2000:] if len(raw_output) > 2000 else raw_output

            db[proposal_id]["status"] = "awaiting_approval" if success else "failed"
            db[proposal_id]["test_logs"] = logs
            self._save_db(db)

            logger.info(
                "Testes para proposta %s: %s",
                proposal_id,
                "PASSOU" if success else "FALHOU",
            )
            return success, logs

        except subprocess.TimeoutExpired:
            timeout_msg = "Timeout: os testes excederam 45 segundos. Proposta chumbada."
            db[proposal_id]["status"] = "failed"
            db[proposal_id]["test_logs"] = timeout_msg
            self._save_db(db)
            logger.error("Timeout nos testes da proposta %s.", proposal_id)
            return False, timeout_msg

    def merge_proposal(self, proposal_id: str) -> bool:
        """
        Ato de Governança: substitui fisicamente o ficheiro original em core/.
        Só executa se os testes tiverem passado (status == 'awaiting_approval').
        Cria backup automático antes do merge.
        """
        db = self._load_db()
        proposal = db.get(proposal_id)

        if not proposal or proposal["status"] != "awaiting_approval":
            logger.warning(
                "Merge recusado para %s. Status atual: %s",
                proposal_id,
                proposal.get("status", "inexistente") if proposal else "inexistente",
            )
            return False

        original_file = self.root_path / proposal["target_file"]
        proposed_file = (
            self.sandbox_dir / proposal_id / Path(proposal["target_file"]).name
        )

        # Backup de segurança
        backup_path = Path(str(original_file) + ".bak")
        shutil.copy2(original_file, backup_path)
        logger.info("Backup criado em %s", backup_path)

        # Merge físico
        shutil.copy2(proposed_file, original_file)

        db[proposal_id]["status"] = "merged"
        self._save_db(db)

        logger.warning(
            "MERGE EXECUTADO: %s foi substituído. Backup em %s",
            original_file,
            backup_path,
        )
        return True

    def reject_proposal(self, proposal_id: str) -> bool:
        """Marca a proposta como rejeitada pelo humano (sem alteração física)."""
        db = self._load_db()
        if proposal_id not in db:
            return False
        db[proposal_id]["status"] = "rejected"
        self._save_db(db)
        logger.info("Proposta %s rejeitada pelo operador humano.", proposal_id)
        return True

    def get_diff(self, proposal_id: str) -> str:
        """
        Gera o diff unificado (Git-style) entre o ficheiro original e a proposta.
        Retorna string vazia se qualquer ficheiro não for encontrado.
        """
        db = self._load_db()
        proposal = db.get(proposal_id)
        if not proposal:
            return ""

        original_file = self.root_path / proposal["target_file"]
        proposed_file = (
            self.sandbox_dir / proposal_id / Path(proposal["target_file"]).name
        )

        try:
            orig_lines = original_file.read_text(encoding="utf-8").splitlines(
                keepends=True
            )
            prop_lines = proposed_file.read_text(encoding="utf-8").splitlines(
                keepends=True
            )
        except OSError as e:
            logger.error("Erro ao ler ficheiros para diff: %s", e)
            return f"Erro ao gerar diff: {e}"

        diff = list(
            difflib.unified_diff(
                orig_lines,
                prop_lines,
                fromfile=f"CURRENT  {proposal['target_file']}",
                tofile=f"PROPOSED {proposal['target_file']}",
            )
        )
        return "".join(diff)
