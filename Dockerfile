# /Dockerfile (Backend)
FROM python:3.11-slim AS builder

# Variáveis de ambiente para otimizar o Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalação de dependências do sistema necessárias para compilação (se houver)
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Instalação das dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# --- STAGE 2: Produção ---
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Cria um utilizador de sistema para não rodar como root (Segurança)
RUN addgroup --system grimoire && adduser --system --ingroup grimoire grimoire

# Copia as rodas compiladas do Stage 1 e instala
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Copia o código-fonte (Soberania de Código)
COPY ./core ./core
# Cria pastas necessárias e ajusta permissões
RUN mkdir -p /app/sandbox/proposals /app/vault && chown -R grimoire:grimoire /app

USER grimoire

EXPOSE 8000

# O Entrypoint que liga o Maestro e o FastAPI
CMD ["uvicorn", "core.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
