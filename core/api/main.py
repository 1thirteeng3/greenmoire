import logging

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.api.routes import chat, stream, governance

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Grimoire Cognitive OS",
    description="API Gateway para o Sistema Operacional Cognitivo End-to-End",
    version="1.0.0",
)

origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost,http://127.0.0.1:3000")
allow_origins = [o.strip() for o in origins_str.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/v1/chat", tags=["Cognitive Operations"])
app.include_router(
    stream.router, prefix="/api/v1/stream", tags=["Cognitive Operations"]
)
app.include_router(governance.router, prefix="/api/v1/governance", tags=["Governance"])


@app.get("/health", tags=["System"])
async def health_check():
    """Endpoint vital para monitorização de uptime do gateway."""
    return {"status": "online", "system": "Grimoire API Gateway is active."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("core.api.main:app", host="0.0.0.0", port=8000, reload=True)
