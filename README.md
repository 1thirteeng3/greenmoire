# Grimoire OS - Sistema Operacional Cognitivo

O Grimoire OS é um framework de orquestração cognitiva de ponta a ponta, projetado para execução de tarefas complexas através de uma tríade de agentes especializados (Planejador, Executor e Auditor).

## 🚀 Arquitetura de Produção

O sistema é dividido em camadas modulares para garantir escalabilidade e segurança:

- **Frontend (grimoire-ux):** Interface React avançada com visualização de rastreio cognitivo em tempo real e modo transparente.
- **API Gateway (core/api):** Ponto de entrada REST/WebSocket para interação com o cérebro cognitivo.
- **Brain (core/brain):** Lógica de roteamento de modelos (T1/T2/T3), classificação de intenção e resolução de conflitos.
- **Agents (core/agents):** Tríade de agentes com ToolRegistry nativo e Sandbox para execução segura de código.
- **Infrastructure:** Camada de persistência (PostgreSQL + pgvector) e barramento de eventos (Redis Streams).

## 🛠️ Instalação e Configuração

### Pré-requisitos
- Python 3.10 ou superior
- Node.js 18+ e npm
- Docker e Docker Compose (para infraestrutura local)

### Backend (Python)
1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Configure o ambiente:
   ```bash
   cp .env.example .env
   # Edite as chaves de API (OpenAI, Anthropic, DeepSeek)
   ```
3. Execute as migrações:
   ```bash
   alembic upgrade head
   ```
4. Inicie o gateway:
   ```bash
   python -m core.api.main
   ```

### Frontend (React)
1. Entre no diretório:
   ```bash
   cd grimoire-ux
   ```
2. Instale e inicie:
   ```bash
   npm install
   npm run dev
   ```

## 🔒 Segurança e Qualidade
O repositório segue padrões rigorosos de auditoria:
- **Linting:** Ruff (Backend) e ESLint (Frontend).
- **Tipagem:** Mypy (Estrito).
- **Segurança:** Bandit e Safety scans integrados.

---
**Status:** `v1.0.0-rc.1` - Pronto para operação em ambiente de demonstração controlada.
