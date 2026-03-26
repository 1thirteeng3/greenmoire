# Grimoire — Fase 6: API Gateway & Interface UX

> Sistema Operacional Cognitivo com transparência total: do evento Redis à telemetria em tempo real no browser.

---

## O que foi implementado

### Backend — Gateway de API (`core/api/`)

| Arquivo | Responsabilidade |
|---|---|
| `schemas.py` | Contratos Pydantic para todos os frames REST e WebSocket |
| `security.py` | Autenticação Bearer + Rate Limiting por IP via Redis |
| `trace_emitter.py` | Publica telemetria por-trace em streams Redis dedicados |
| `routes/chat.py` | Endpoint REST síncrono (`POST /api/v1/chat/sync`) |
| `routes/websocket.py` | Canal WebSocket bidirecional (`/ws/cognitive-stream`) |
| `main.py` | FastAPI com ambos os routers + CORS |

### Backend — Orquestrador Atualizado (`core/services/`)

O `OrchestratorWorker` foi instrumentado com **23 pontos de emissão de telemetria** cobrindo cada agente do ciclo cognitivo:

```
IntentClassifier → ContextBuilder → AgentSelector →
PlannerAgent → ExecutorAgent (por etapa) → AuditorAgent
```

Cada evento inclui: agente, ação, tier, timestamp_ms — consumidos pelo WebSocket e entregues ao frontend em ~50ms.

### Frontend — Grimoire UX (`grimoire-ux/`)

```
grimoire-ux/
├── src/
│   ├── types/index.ts              # Contratos TypeScript (espelha schemas.py)
│   ├── contexts/UiContext.tsx      # Standard ↔ Advanced mode (persistido em localStorage)
│   ├── hooks/useCognitiveStream.ts # WebSocket client + gestão de estado cognitivo
│   └── components/
│       ├── layout/Header.tsx       # Barra superior com status WS + toggle de modo
│       ├── transparency/
│       │   ├── IterationHistory.tsx    # Histórico de mensagens + metadados (Advanced)
│       │   ├── ExecutionPlan.tsx       # DAG com progresso em tempo real
│       │   └── LiveTracePanel.tsx      # Terminal de telemetria (Advanced only)
│       ├── chat/ChatInput.tsx          # Input com auto-resize + indicador de progresso
│       └── shared/
│           └── CognitiveCycleIndicator.tsx  # Breadcrumb do ciclo (Classificar→Planear→Executar→Auditar)
```

---

## Como executar

### 1. Pré-requisitos
```bash
# Backend (Python 3.11+)
pip install -r requirements.txt

# Frontend (Node 20+)
cd grimoire-ux && npm install
```

### 2. Infra (Docker)
```bash
docker-compose up -d postgres redis localai opendataloader
```

### 3. Backend
```bash
# Variáveis de ambiente
cp .env.example .env
# Edite .env com suas chaves

# Iniciar API Gateway + Workers
uvicorn core.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Frontend
```bash
cd grimoire-ux
cp .env.example .env.local
# Edite VITE_API_TOKEN para corresponder ao backend

npm run dev
# Acesse http://localhost:5173
```

---

## Protocolo de Frames WebSocket

### Autenticação
```
ws://localhost:8000/ws/cognitive-stream?token=<API_SECRET_TOKEN>
```

### Frames do cliente → servidor
```json
{ "prompt": "Pesquise sobre X", "context_hints": [] }
```

### Frames do servidor → cliente

| Tipo | Quando | Dados chave |
|---|---|---|
| `connected` | Handshake inicial | `session_id` |
| `trace` | A cada ação de agente | `agent`, `action`, `tier`, `timestamp_ms` |
| `plan` | PlannerAgent termina | `plan_rationale`, `steps[]` |
| `plan_step_update` | Cada etapa muda de status | `step_id`, `status` |
| `response` | Ciclo concluído | `content`, `tier_used`, `audit_approved` |
| `error` | Qualquer falha | `code`, `message` |
| `heartbeat` | 60s de inatividade | `ts` |

---

## Modos de Interface

### Standard
- Histórico de mensagens limpo
- Visualização do Plano de Execução (quando T3)
- Breadcrumb do ciclo cognitivo

### Advanced (toggle no header)
- **LiveTracePanel** lateral — 300px, estilo terminal, auto-scroll
- **Metadados por mensagem** — Tier, Latência, Tokens, Intent, status de Auditoria
- **trace_id** visível em cada mensagem do Grimoire
- Session ID no header

---

## Decisões de Arquitetura

### WebSocket auth via query param (não header)
O padrão HTTP `Authorization: Bearer` não é suportado durante o handshake WS pelo browser. A solução segura é `?token=` via TLS — o token não aparece nos logs de servidor se HTTPS estiver activo.

### Streams Redis por trace (não por sessão)
Cada ciclo cognitivo cria `stream:trace:<trace_id>` com TTL de 5 minutos. Evita acumulação ilimitada e isola sessões concorrentes.

### TraceEmitter fail-open
Falhas no emitter NUNCA bloqueiam o ciclo cognitivo. A telemetria é best-effort — o raciocínio é primeiro-cidadão.
