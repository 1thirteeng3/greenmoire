# Grimoire OS - Sistema Operacional Cognitivo

O Grimoire OS é um framework de orquestração cognitiva de ponta a ponta, projetado para execução de tarefas complexas através de uma tríade de agentes especializados (Planejador, Executor e Auditor).

## 🚀 Arquitetura de Produção

O sistema é dividido em camadas modulares para garantir escalabilidade e segurança:

- **Frontend (grimoire-ux):** Interface React avançada com visualização de rastreio cognitivo em tempo real e modo transparente.
- **API Gateway (core/api):** Ponto de entrada REST/WebSocket para interação com o cérebro cognitivo.
- **Brain (core/brain):** Lógica de roteamento de modelos (T1/T2/T3), classificação de intenção e resolução de conflitos.
- **Agents (core/agents):** Tríade de agentes com ToolRegistry nativo e Sandbox para execução segura de código.
- **Infrastructure:** Camada de persistência (PostgreSQL + pgvector) e barramento de eventos (Redis Streams).

## 🛠️ Instalação e Utilização

A forma recomendada de executar o Grimoire OS de forma estável e segura é através do **Docker Compose**.

Para o guia detalhado incluindo pré-requisitos, configuração de variáveis de ambiente (`.env`) e funcionamento da interface, consulte o nosso guia oficial:

👉 **[GUIA_INSTALACAO_USO.md](./GUIA_INSTALACAO_USO.md)**

### Comandos Rápidos
```bash
cp .env.example .env
# Configure suas chaves no .env
docker-compose up -d --build
```

---
**Status:** `v1.0.0` - Productization Concluída.

