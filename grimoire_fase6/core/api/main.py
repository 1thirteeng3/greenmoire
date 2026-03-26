import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.api.routes import chat
from core.api.routes import websocket as ws_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Grimoire Cognitive OS",
    description="API Gateway para o Sistema Operacional Cognitivo End-to-End",
    version="6.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST endpoints (autenticados via Bearer)
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Cognitive Operations"])

# WebSocket endpoint (autenticado via query param ?token=)
app.include_router(ws_router.router, tags=["Real-Time Stream"])


@app.get("/health", tags=["System"])
async def health_check():
    """Endpoint vital para monitorização de uptime do gateway."""
    return {
        "status": "online",
        "system": "Grimoire API Gateway v6 is active.",
        "endpoints": {
            "rest": "/api/v1/chat/sync",
            "websocket": "/ws/cognitive-stream?token=<API_SECRET_TOKEN>",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("core.api.main:app", host="0.0.0.0", port=8000, reload=True)
