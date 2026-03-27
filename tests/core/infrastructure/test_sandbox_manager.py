"""
Tests para o SandboxManager (Fase 7).
Valida: criação de proposta, bloqueio de path traversal, controlo de estado no merge.
"""

import pytest
from pathlib import Path

from core.infrastructure.sandbox.manager import SandboxManager, ImprovementProposal


@pytest.fixture
def sandbox(tmp_path):
    """SandboxManager com root em tmp_path; cria um core/ falso para testes."""
    # Cria estrutura mínima: root/core/fake_module.py
    core_dir = tmp_path / "core"
    core_dir.mkdir()
    fake_file = core_dir / "fake_module.py"
    fake_file.write_text("# módulo original\nX = 1\n", encoding="utf-8")
    return SandboxManager(root_dir=str(tmp_path)), fake_file


class TestStagingProposal:
    def test_creates_proposal_folder_and_registry(self, sandbox):
        """stage_proposal deve criar ficheiro na sandbox e registo em registry.json."""
        mgr, fake_file = sandbox
        proposal = mgr.stage_proposal(
            str(fake_file), "# código novo\nX = 2\n", "Teste básico"
        )

        assert isinstance(proposal, ImprovementProposal)
        assert proposal.status == "pending"
        assert proposal.id.startswith("pr-")

        # O ficheiro deve existir na sandbox
        proposed = mgr.sandbox_dir / proposal.id / fake_file.name
        assert proposed.exists()
        assert proposed.read_text(encoding="utf-8") == "# código novo\nX = 2\n"

        # O registo deve estar em registry.json
        db = mgr._load_db()
        assert proposal.id in db

    def test_rejects_path_outside_core(self, sandbox):
        """Um caminho fora de core/ deve levantar PermissionError."""
        mgr, _ = sandbox
        outside_path = str(mgr.root_path / "etc" / "passwd")

        with pytest.raises(
            PermissionError, match="restrito a modificar apenas a pasta"
        ):
            mgr.stage_proposal(outside_path, "malicious content", "Tentativa de fuga")

    def test_rejects_path_traversal_attempt(self, sandbox):
        """Sequências '../' não devem conseguir sair do diretório core/."""
        mgr, fake_file = sandbox
        traversal_path = str(mgr.root_path / "core" / ".." / ".." / "etc" / "shadow")

        with pytest.raises(PermissionError):
            mgr.stage_proposal(traversal_path, "payload", "Path traversal attempt")

    def test_proposal_stored_in_db(self, sandbox):
        """A proposta criada deve ser persistida no JSON do registry."""
        mgr, fake_file = sandbox
        proposal = mgr.stage_proposal(str(fake_file), "X = 99\n", "Persistência")
        db = mgr._load_db()
        record = db[proposal.id]
        assert record["rationale"] == "Persistência"
        assert record["status"] == "pending"


class TestMergeProposal:
    def _create_pending_proposal(self, mgr, fake_file):
        proposal = mgr.stage_proposal(str(fake_file), "X = 42\n", "Para merge")
        # Promove manualmente para 'awaiting_approval' (simula testes passados)
        db = mgr._load_db()
        db[proposal.id]["status"] = "awaiting_approval"
        mgr._save_db(db)
        return proposal

    def test_merge_requires_awaiting_approval_status(self, sandbox):
        """merge_proposal deve retornar False se status não for 'awaiting_approval'."""
        mgr, fake_file = sandbox
        proposal = mgr.stage_proposal(str(fake_file), "X = 5\n", "Pending merge")
        # Status é 'pending' — merge deve falhar
        result = mgr.merge_proposal(proposal.id)
        assert result is False

    def test_merge_succeeds_and_updates_original(self, sandbox):
        """merge_proposal deve sobrescrever o ficheiro original e criar .bak."""
        mgr, fake_file = sandbox
        proposal = self._create_pending_proposal(mgr, fake_file)

        result = mgr.merge_proposal(proposal.id)

        assert result is True
        # Ficheiro original deve conter o novo código
        assert fake_file.read_text(encoding="utf-8") == "X = 42\n"
        # Backup deve existir
        assert Path(str(fake_file) + ".bak").exists()

    def test_merge_marks_status_as_merged(self, sandbox):
        """Após merge, o status na DB deve ser 'merged'."""
        mgr, fake_file = sandbox
        proposal = self._create_pending_proposal(mgr, fake_file)
        mgr.merge_proposal(proposal.id)
        db = mgr._load_db()
        assert db[proposal.id]["status"] == "merged"

    def test_merge_nonexistent_proposal_returns_false(self, sandbox):
        mgr, _ = sandbox
        assert mgr.merge_proposal("pr-naoexiste") is False


class TestGetDiff:
    def test_diff_shows_changes(self, sandbox):
        """get_diff deve retornar texto de diff não vazio quando há alterações."""
        mgr, fake_file = sandbox
        proposal = mgr.stage_proposal(str(fake_file), "# novo\nX = 999\n", "Diff test")
        diff = mgr.get_diff(proposal.id)
        assert diff  # não deve ser vazio
        assert "-" in diff or "+" in diff  # deve conter marcadores de diff


class TestRejectProposal:
    def test_reject_marks_status(self, sandbox):
        mgr, fake_file = sandbox
        proposal = mgr.stage_proposal(str(fake_file), "X = 0\n", "Para rejeitar")
        result = mgr.reject_proposal(proposal.id)
        assert result is True
        db = mgr._load_db()
        assert db[proposal.id]["status"] == "rejected"

    def test_reject_nonexistent_returns_false(self, sandbox):
        mgr, _ = sandbox
        assert mgr.reject_proposal("pr-inexistente") is False
