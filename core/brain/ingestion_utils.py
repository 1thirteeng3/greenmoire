import re
import os
import logging
import asyncio
import tiktoken
from typing import List, Tuple
from core.integrations.vlm_provider import VLMProvider

logger = logging.getLogger(__name__)


async def _call_opendataloader(file_path: str) -> Tuple[str, List[str]]:
    """
    Executa a extração via opendataloader-pdf.
    Garante a preservação de tabelas e LaTeX.
    """
    logger.info(f"Processando {file_path} via opendataloader-pdf...")

    # Simulação da execução real do opendataloader (que salva imagens num diretório temporário)
    mock_markdown = "Contexto inicial.\n![Gráfico da Q3](/tmp/grafico_vendas.png)\nConclusão do documento."
    mock_images = ["/tmp/grafico_vendas.png"] if os.path.exists("/tmp/grafico_vendas.png") else []

    await asyncio.sleep(1)  # Simula o I/O
    return mock_markdown, mock_images


async def extract_and_enrich_pdf(file_path: str, vlm_provider: VLMProvider) -> str:
    """
    Orquestra a extração estrutural e a injeção semântica multimodal.
    """
    # 1. Extração Estrutural (Markdown + Extração física de imagens)
    markdown_text, extracted_images = await _call_opendataloader(file_path)

    # 2. Processamento VLM para imagens órfãs
    if extracted_images:
        logger.info(f"{len(extracted_images)} imagens detetadas. Iniciando enriquecimento VLM...")

        for img_path in extracted_images:
            img_filename = os.path.basename(img_path)

            # Gera a descrição via VLM (Cloud ou Local)
            semantic_desc = await vlm_provider.describe_image(img_path)

            # Substitui a tag da imagem no markdown pelo texto gerado
            pattern = rf"!\[.*?\]\(.*?{re.escape(img_filename)}.*?\)"
            markdown_text = re.sub(pattern, semantic_desc, markdown_text)

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
