import re
import os
import logging
import asyncio
import tiktoken
from typing import List
from core.integrations.vlm_provider import VLMProvider
from core.integrations.opendataloader_provider import OpenDataLoaderProvider

logger = logging.getLogger(__name__)


async def extract_and_enrich_pdf(
    file_path: str, vlm_provider: VLMProvider, pdf_provider: OpenDataLoaderProvider
) -> str:
    """
    Orquestra a extração estrutural e a injeção semântica multimodal.
    """
    # 1. Extração via Microsserviço Real
    logger.info(f"Enviando {file_path} para o OpenDataLoader...")
    markdown_text, extracted_images = await pdf_provider.extract_pdf(file_path)

    # 2. Processamento VLM para imagens órfãs
    if extracted_images:
        logger.info(f"Enriquecendo {len(extracted_images)} imagens via VLM...")

        for img_path in extracted_images:
            img_filename = os.path.basename(img_path)

            # Gera a descrição via VLM (Cloud ou Local)
            semantic_desc = await vlm_provider.describe_image(img_path)

            # Substitui a tag da imagem no MD pela descrição do modelo
            pattern = rf"!\[.*?\]\(.*?{re.escape(img_filename)}.*?\)"
            markdown_text = re.sub(pattern, semantic_desc, markdown_text)

            # Limpeza do ficheiro temporário para não entupir o disco
            try:
                os.remove(img_path)
            except OSError as e:
                logger.warning(f"Falha ao apagar imagem temporária {img_path}: {e}")

    return markdown_text


# ==========================================
# FRAGMENTAÇÃO SEMÂNTICA (CHUNKING)
# ==========================================


def _chunk_text_sync(text: str, max_tokens: int = 400) -> List[str]:
    """Fragmentação inteligente baseada em parágrafos e contagem de tokens."""
    encoding = tiktoken.get_encoding("cl100k_base")
    paragraphs = text.split("\n\n")
    chunks, current_chunk = [], []
    current_length = 0

    for paragraph in paragraphs:
        paragraph_tokens = len(encoding.encode(paragraph))

        if paragraph_tokens > max_tokens:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk, current_length = [], 0
            chunks.append(paragraph)
            continue

        if current_length + paragraph_tokens > max_tokens:
            chunks.append("\n\n".join(current_chunk))
            overlap = current_chunk[-1] if current_chunk else ""
            current_chunk = [overlap, paragraph] if overlap else [paragraph]
            current_length = len(encoding.encode(overlap)) + paragraph_tokens
        else:
            current_chunk.append(paragraph)
            current_length += paragraph_tokens

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


async def chunk_document(text: str, max_tokens: int = 400) -> List[str]:
    return await asyncio.to_thread(_chunk_text_sync, text, max_tokens)
