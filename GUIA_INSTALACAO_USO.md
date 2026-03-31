# 🧙‍♂️ Guia de Instalação e Utilização — Grimoire OS v1.0.0

Bem-vindo ao **Grimoire OS**, o Sistema Operacional Cognitivo para orquestração de Agentes AI de última geração. Este guia fornece instruções passo a passo para colocar a sua instância em funcionamento usando Docker e como navegar na interface.

---

## 📋 1. Pré-requisitos

Antes de começar, certifique-se de que tem as seguintes ferramentas instaladas:

*   **Docker Desktop** (ou Docker Engine no Linux)
*   **Docker Compose v2.0+**
*   **Git** (para clonar o repositório)

---

## 🚀 2. Instalação Passo a Passo

### Etapa 1: Clonar o Repositório
Abra o seu terminal e execute:
```bash
git clone https://github.com/seu-usuario/greenmoire.git
cd greenmoire
```

### Etapa 2: Configurar Variáveis de Ambiente
O Grimoire OS utiliza um ficheiro `.env` para gerir chaves de API e ligações de base de dados.

1. Copie o exemplo:
   ```bash
   cp .env.example .env
   ```
2. Edite o ficheiro `.env` e preencha as suas chaves:
   *   `ANTHROPIC_API_KEY`: Necessária para o Agente de Tier 3 (Claude 3.5 Sonnet).
   *   `OPENAI_API_KEY`: Necessária para o Agente de Tier 2 (GPT-4o).
   *   `DATABASE_URL`: No Docker, use `postgresql+asyncpg://grimoire_admin:grimoire_secure_password@postgres:5432/grimoire_core`.

> [!IMPORTANT]
> **Segurança de Sandbox**: O Grimoire OS utiliza uma pasta local `./sandbox` para isolar execuções de código. Certifique-se de que o Docker tem permissões de escrita nesta pasta.

### Etapa 3: Iniciar o Ecossistema (Docker Compose)
Toda a infraestrutura (Banco de Dados, Redis, LocalAI, Backend e Frontend) é iniciada com um único comando:

```bash
docker-compose up -d --build
```

Este comando irá:
1. Compilar o **Frontend (Nginx + React)**.
2. Compilar o **Backend (FastAPI + Maestro Worker)**.
3. Inicializar o **PostgreSQL com pgvector** (para memória a longo prazo).
4. Subir o **LocalAI** para embeddings locais (privacidade total).

---

## 🖥️ 3. Como Utilizar a Aplicação

### Acesso à Interface (Grimoire UX)
Uma vez que os contentores estejam ativos, abra o seu navegador em:
👉 **[http://localhost:3000](http://localhost:3000)**

### Funcionalidades Principais:

#### 🧠 1. Cognitive Stream (Chat)
Na página principal, você interage com o **Maestro**. Diferente de um chat comum:
*   **Rastreio em Tempo Real**: Você verá o "pensamento" dos três agentes (Planejador, Executor, Auditor) em tempo real conforme eles colaboram.
*   **Decisões de Roteamento**: O sistema decide automaticamente se usa um modelo local leve (T1) ou um modelo comercial pesado (T3) dependendo da complexidade da pergunta.

#### 🗄️ 2. Vault (O Segundo Cérebro)
No menu lateral, aceda ao **Vault**:
*   Aqui ficam armazenadas as notas geradas pelo agente.
*   O Agente pode ler e escrever ficheiros markdown que são sincronizados com a memória vetorial do sistema.

#### 🧪 3. Sandbox de Código
Quando solicitada uma tarefa de análise de dados ou automação:
*   O Agente Executor gera scripts Python.
*   Os resultados aparecem diretamente na interface como propostas de execução.

---

## 🛠️ 4. Gestão e Manutenção

### Verificar se tudo está a correr bem (Logs)
Se encontrar problemas, verifique os logs do cérebro (Backend):
```bash
docker-compose logs -f backend
```

### Reiniciar o Sistema
```bash
docker-compose restart
```

### Limpeza de Dados (Reset Total)
> [!CAUTION]
> Isto apagará todas as memórias e bases de dados do sistema.
```bash
docker-compose down -v
```

---

## 🔍 5. Troubleshooting (Resolução de Problemas)

*   **"Não consigo conectar à API"**: Verifique se o container `grimoire_core` está ativo (`docker ps`).
*   **"Erro de Embeddings"**: O container `localai` pode demorar alguns minutos a carregar o modelo `bge-large` na primeira execução.
*   **"Porta 3000 já em uso"**: Edite o `docker-compose.yml` e mude a porta do `frontend` de `3000:80` para `3001:80`.

---
**Versão:** 1.0.0 — *The Enterprise-Grade Cognitive OS*
**Suporte:** Abra uma issue no repositório GitHub.
