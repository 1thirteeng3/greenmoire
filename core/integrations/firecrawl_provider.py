import os
import logging
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class FirecrawlProvider:
    """Adaptador assíncrono para a API do Firecrawl (Scrape e Crawl em lote)."""

    def __init__(self):
        self.api_key = os.getenv("FIRECRAWL_API_KEY")
        self.base_url = os.getenv("FIRECRAWL_BASE_URL", "https://api.firecrawl.dev/v1")
        self.timeout = aiohttp.ClientTimeout(total=60.0)

    def _get_headers(self) -> dict:
        if not self.api_key:
            raise ValueError("Firecrawl API Key ausente.")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def scrape_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Extrai o Markdown limpo de uma única URL."""
        endpoint = f"{self.base_url}/scrape"
        payload = {"url": url, "formats": ["markdown"], "onlyMainContent": True}

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                endpoint, json=payload, headers=self._get_headers()
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"Falha no Firecrawl: {await response.text()}")

                data = await response.json()
                if not data.get("success"):
                    raise RuntimeError(f"Erro na extração: {data.get('error')}")

                return {
                    "markdown": data["data"].get("markdown", ""),
                    "metadata": data["data"].get("metadata", {}),
                    "source_url": url,
                }

    async def crawl_website(
        self, url: str, max_depth: int = 2, max_pages: int = 10
    ) -> List[Dict[str, Any]]:
        """Submete um job de crawl profundo e faz polling até a conclusão."""
        endpoint = f"{self.base_url}/crawl"
        payload = {
            "url": url,
            "limit": max_pages,
            "maxDepth": max_depth,
            "scrapeOptions": {"formats": ["markdown"], "onlyMainContent": True},
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                endpoint, json=payload, headers=self._get_headers()
            ) as response:
                if response.status != 200:
                    raise RuntimeError(
                        f"Falha ao iniciar Crawl: {await response.text()}"
                    )
                job_id = (await response.json()).get("id")

            if not job_id:
                raise RuntimeError("Firecrawl não retornou Job ID.")

            logger.info(f"Crawl iniciado: {url} (Job ID: {job_id})")
            status_endpoint = f"{endpoint}/{job_id}"

            # Polling Assíncrono
            while True:
                await asyncio.sleep(5)
                async with session.get(
                    status_endpoint, headers=self._get_headers()
                ) as status_resp:
                    status_data = await status_resp.json()
                    status = status_data.get("status")

                    if status == "completed":
                        logger.info(f"Crawl concluído: {url}")
                        pages = []
                        for item in status_data.get("data", []):
                            if item.get("markdown"):
                                pages.append(
                                    {
                                        "markdown": item["markdown"],
                                        "source_url": item.get("metadata", {}).get(
                                            "sourceURL", url
                                        ),
                                    }
                                )
                        return pages
                    elif status in ["failed", "cancelled"]:
                        raise RuntimeError(f"Crawl abortado: {status_data}")
