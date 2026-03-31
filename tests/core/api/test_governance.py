"""
Tests de integração para a Governance API (Fase 7).
Valida autenticação, listagem, diff e rejeição de merge inválido.
"""

import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient

from core.api.main import app

# Token correcto para testes (deve corresponder ao valor por defeito em security.py)
VALID_TOKEN = "grimoire_super_secret_token_2026"
HEADERS = {"Authorization": f"Bearer {VALID_TOKEN}"}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def populated_sandbox(tmp_path):
    """
    Cria um SandboxManager com um registo falso já populado.
    Retorna (manager, proposal_id).
    """
    from core.infrastructure.sandbox.manager import SandboxManager

    # Cria core/ e ficheiro alvo
    core_dir = tmp_path / "core"
    core_dir.mkdir()
    fake_file = core_dir / "target.py"
    fake_file.write_text("X = 1\n", encoding="utf-8")

    mgr = SandboxManager(root_dir=str(tmp_path))
    proposal = mgr.stage_proposal(str(fake_file), "X = 2\n", "Teste de governança")
    return mgr, proposal.id


class TestAuthenticationGuard:
    def test_list_proposals_without_token_returns_401(self, client):
        resp = client.get("/api/v1/governance/proposals")
        assert resp.status_code == 401

    def test_list_proposals_with_wrong_token_returns_401(self, client):
        resp = client.get(
            "/api/v1/governance/proposals",
            headers={"Authorization": "Bearer wrong_token"},
        )
        assert resp.status_code == 401

    def test_merge_without_token_returns_401(self, client):
        resp = client.post("/api/v1/governance/proposals/pr-fake/merge")
        assert resp.status_code == 401


class TestMergeValidation:
    def test_merge_nonexistent_proposal_returns_404(self, client):
        resp = client.post(
            "/api/v1/governance/proposals/pr-naoexiste/merge",
            headers=HEADERS,
        )
        assert resp.status_code == 404

    def test_merge_pending_proposal_returns_400(self, client, populated_sandbox):
        """Uma proposta em status 'pending' (testes não correram) não pode ser fundida."""
        mgr, proposal_id = populated_sandbox

        # Substitui o sandbox do módulo governance temporariamente
        with patch("core.api.routes.governance.sandbox", mgr):
            resp = client.post(
                f"/api/v1/governance/proposals/{proposal_id}/merge",
                headers=HEADERS,
            )
        assert resp.status_code == 400
        assert "awaiting_approval" in resp.json()["detail"]


class TestDiffEndpoint:
    def test_diff_nonexistent_returns_404(self, client):
        resp = client.get(
            "/api/v1/governance/proposals/pr-inexistente/diff",
            headers=HEADERS,
        )
        assert resp.status_code == 404

    def test_diff_valid_proposal_returns_diff(self, client, populated_sandbox):
        """Um diff válido deve retornar os campos esperados."""
        mgr, proposal_id = populated_sandbox

        with patch("core.api.routes.governance.sandbox", mgr):
            resp = client.get(
                f"/api/v1/governance/proposals/{proposal_id}/diff",
                headers=HEADERS,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "diff" in data
        assert "proposal_id" in data
        assert data["proposal_id"] == proposal_id


class TestRejectEndpoint:
    def test_reject_valid_proposal(self, client, populated_sandbox):
        mgr, proposal_id = populated_sandbox

        with patch("core.api.routes.governance.sandbox", mgr):
            resp = client.post(
                f"/api/v1/governance/proposals/{proposal_id}/reject",
                headers=HEADERS,
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    def test_reject_nonexistent_returns_404(self, client):
        resp = client.post(
            "/api/v1/governance/proposals/pr-ghost/reject",
            headers=HEADERS,
        )
        assert resp.status_code == 404
