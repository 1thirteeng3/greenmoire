import os
import aiohttp
import aiofiles
import base64
import logging
from pathlib import Path
from typing import Tuple, List

logger = logging.getLogger(__name__)


class OpenDataLoaderProvider:
    """Comunica com o contêiner local do Marker-API para extrair texto estruturado e imagens de PDFs."""

    def __init__(self):
        self.base_url = os.getenv("OPENDATALOADER_URL", "http://localhost:8000")
        self.timeout = aiohttp.ClientTimeout(total=300.0)
        self.tmp_img_dir = Path("/tmp/grimoire_ingestion")
        self.tmp_img_dir.mkdir(parents=True, exist_ok=True)

    async def extract_pdf(self, file_path: str) -> Tuple[str, List[str]]:
        endpoint = f"{self.base_url}/api/v1/extract"
        extracted_image_paths = []

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF não encontrado: {file_path}")

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            data = aiohttp.FormData()
            with open(file_path, "rb") as pdf_file:
                data.add_field(
                    "file",
                    pdf_file,
                    filename=os.path.basename(file_path),
                    content_type="application/pdf",
                )

                async with session.post(endpoint, data=data) as response:
                    if response.status != 200:
                        raise RuntimeError(
                            f"Erro OpenDataLoader: {await response.text()}"
                        )

                    result = await response.json()
                    markdown_content = result.get("markdown", "")
                    images_data = result.get("images", [])

                    # Salva imagens extraídas para processamento posterior do VLM
                    for img in images_data:
                        img_path = self.tmp_img_dir / img["filename"]
                        async with aiofiles.open(img_path, "wb") as f:
                            await f.write(base64.b64decode(img["base64"]))
                        extracted_image_paths.append(str(img_path))

                    return markdown_content, extracted_image_paths
