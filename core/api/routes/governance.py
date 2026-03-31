from fastapi import APIRouter, HTTPException
from fastapi import Depends

from core.api.security import verify_auth_token
from core.infrastructure.sandbox.manager import SandboxManager

router = APIRouter(
    prefix="",
    tags=["Governance"],
    dependencies=[Depends(verify_auth_token)],
)

# Module-level sandbox instance (resolved relative to cwd at startup)
sandbox = SandboxManager(root_dir=".")


@router.get("/proposals", summary="Lista todas as propostas de código geradas pela IA")
async def list_proposals():
    """
    Retorna o registo completo de todas as alterações de código pendentes,
    em teste, aprovadas, fundidas ou rejeitadas.
    """
    return sandbox._load_db()


@router.get(
    "/proposals/{proposal_id}",
    summary="Detalhe de uma proposta específica",
)
async def get_proposal(proposal_id: str):
    """Retorna os metadados completos de uma proposta individual."""
    db = sandbox._load_db()
    if proposal_id not in db:
        raise HTTPException(status_code=404, detail="Proposta não encontrada.")
    return db[proposal_id]


@router.get(
    "/proposals/{proposal_id}/diff",
    summary="Diff Git-style entre o código atual e o proposto",
)
async def get_proposal_diff(proposal_id: str):
    """
    Devolve a diferença visual (unified diff) para o humano ler
    e avaliar antes de aprovar o merge.
    """
    db = sandbox._load_db()
    if proposal_id not in db:
        raise HTTPException(status_code=404, detail="Proposta não encontrada.")

    diff_text = sandbox.get_diff(proposal_id)
    if not diff_text:
        # Pode acontecer se os ficheiros foram movidos após a proposta
        raise HTTPException(
            status_code=422,
            detail="Não foi possível gerar o diff. Os ficheiros da proposta podem ter sido removidos.",
        )

    return {
        "proposal_id": proposal_id,
        "status": db[proposal_id]["status"],
        "rationale": db[proposal_id]["rationale"],
        "diff": diff_text,
    }


@router.post(
    "/proposals/{proposal_id}/merge",
    summary="Funde o código aprovado no núcleo do sistema (Veto Humano)",
)
async def merge_proposal(proposal_id: str):
    """
    Executa a fundição física do código aprovado em core/.
    Só é permitido se os testes automáticos tiverem passado (status == 'awaiting_approval').
    Um backup .bak é criado automaticamente antes do merge.
    """
    db = sandbox._load_db()
    if proposal_id not in db:
        raise HTTPException(status_code=404, detail="Proposta não encontrada.")

    proposal_status = db[proposal_id]["status"]
    if proposal_status != "awaiting_approval":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Merge recusado. A proposta está no estado '{proposal_status}'. "
                "Apenas propostas com status 'awaiting_approval' podem ser fundidas."
            ),
        )

    success = sandbox.merge_proposal(proposal_id)
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Falha interna no merge. Verifique os logs do servidor.",
        )

    return {
        "status": "success",
        "message": f"Proposta {proposal_id} fundida com sucesso no núcleo vivo do Grimoire.",
        "warning": "O servidor deve ser reiniciado para que as alterações de código entrem em vigor.",
    }


@router.post(
    "/proposals/{proposal_id}/reject",
    summary="Rejeita uma proposta (nenhuma alteração física é feita)",
)
async def reject_proposal(proposal_id: str):
    """Marca a proposta como rejeitada pelo operador humano. Nenhum ficheiro é alterado."""
    db = sandbox._load_db()
    if proposal_id not in db:
        raise HTTPException(status_code=404, detail="Proposta não encontrada.")

    success = sandbox.reject_proposal(proposal_id)
    if not success:
        raise HTTPException(status_code=500, detail="Falha ao rejeitar a proposta.")

    return {"status": "rejected", "proposal_id": proposal_id}
