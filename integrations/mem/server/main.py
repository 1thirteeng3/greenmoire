import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from core.api.routes import chat, stream
from core.infrastructure.event_bus import AsyncRedisEventBus
from core.bootstrap import ApplicationContainer

# Configuração global de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# ==========================================
# GESTÃO DO CICLO DE VIDA (O Botão de Energia)
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando o Sistema Operacional Cognitivo Grimoire...")
    
    # 1. Preparar a Infraestrutura Base
    bus = AsyncRedisEventBus()
    
    # (Nota: Usando SQLite em memória/arquivo local para testes rápidos. 
    # Em produção, altere para o seu PostgreSQL/pgvector real)
    engine = create_async_engine("sqlite+aiosqlite:///./grimoire_local.db")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    
    # 2. Instanciar o Cérebro (Injeção de Dependências)
    container = ApplicationContainer(bus, session_factory)
    
    # 3. Ligar os Agentes em Background (Crucial para não bloquear o servidor web)
    worker_task = asyncio.create_task(container.start_all_workers())
    logger.info("Cérebro (OrchestratorWorker) acordado e a escutar o Redis.")

    yield # O Servidor Web (FastAPI) fica a rodar aqui

    # 4. Desligamento Limpo
    logger.info("Encerrando o sistema...")
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    await engine.dispose()
    logger.info("Grimoire desligado com segurança.")

# ==========================================
# CONFIGURAÇÃO DA API
# ==========================================
app = FastAPI(
    title="Grimoire Cognitive OS",
    description="API Gateway para o Sistema Operacional Cognitivo End-to-End",
    version="1.0.0",
    lifespan=lifespan # Injetamos o ciclo de vida aqui
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registo de Rotas
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Cognitive REST"])
app.include_router(stream.router, prefix="/api/v1/stream", tags=["Cognitive Streaming"])

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "online", "system": "Grimoire API Gateway & Workers are active."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("core.api.main:app", host="0.0.0.0", port=8000, reload=True)