import os
from dataclasses import dataclass


_SUPPORTED_PROVIDERS = {"openai", "local"}
_KNOWN_DIMENSIONS_BY_MODEL = {
    "openai/text-embedding-3-small": 1536,
    "openai/text-embedding-3-large": 3072,
    "local/BAAI/bge-large-en-v1.5": 1024,
}


@dataclass(frozen=True)
class EmbeddingConfig:
    model_name: str
    dimension: int
    provider: str


class EmbeddingConfigError(ValueError):
    """Erro de configuração inválida de embeddings."""


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise EmbeddingConfigError(f"Variável obrigatória ausente: {name}")
    return value


def load_embedding_config() -> EmbeddingConfig:
    """
    Carrega e valida a configuração de embeddings de forma estrita.
    Exige apenas um modelo ativo por ambiente/processo.
    """
    model = _require_env("EMBEDDING_MODEL")
    dimension_raw = _require_env("EMBEDDING_DIMENSION")

    try:
        dimension = int(dimension_raw)
    except ValueError as exc:
        raise EmbeddingConfigError("EMBEDDING_DIMENSION deve ser um inteiro válido.") from exc

    if "/" not in model:
        raise EmbeddingConfigError(
            "EMBEDDING_MODEL deve seguir o padrão '<provider>/<model-id>' "
            "(ex: 'openai/text-embedding-3-small')."
        )

    provider = model.split("/", 1)[0].lower()
    if provider not in _SUPPORTED_PROVIDERS:
        raise EmbeddingConfigError(
            f"Provedor de embedding não suportado: '{provider}'. "
            f"Use um de: {sorted(_SUPPORTED_PROVIDERS)}."
        )

    expected_dimension = _KNOWN_DIMENSIONS_BY_MODEL.get(model)
    if expected_dimension is not None and expected_dimension != dimension:
        raise EmbeddingConfigError(
            "Inconsistência entre EMBEDDING_MODEL e EMBEDDING_DIMENSION: "
            f"{model} requer {expected_dimension}, mas recebeu {dimension}."
        )

    if dimension <= 0:
        raise EmbeddingConfigError("EMBEDDING_DIMENSION deve ser maior que zero.")

    return EmbeddingConfig(model_name=model, dimension=dimension, provider=provider)
