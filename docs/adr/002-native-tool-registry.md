# ADR 002: Tooling Nativo (Substituicao de bibliotecas de terceiros)

**Data:** 2026-03-26  
**Status:** Aceito  

## Contexto

Na Fase 5, o roadmap previa integracao com bibliotecas de automacao de agentes de terceiros
(ex: openagent/hermes). Durante a evolucao da arquitetura, essa abordagem mostrou riscos
incompativeis com os principios do Grimoire:

- **Vendor lock-in** por contratos opacos e mudancas externas fora do nosso controle.
- **Perda de soberania de dados**, com risco de acoplamento a pipelines nao auditaveis.
- **Baixa previsibilidade operacional** para execucao offline e depuracao em ambiente local.

Ao mesmo tempo, o projeto ja possuia um `ToolRegistry` nativo com contratos explicitos,
RBAC por agente e tratamento fail-safe para operacoes criticas no cofre Obsidian.

## Decisao

Padronizar a camada de ferramentas em um **ToolRegistry nativo**, removendo dependencias
arquiteturais de bibliotecas agentic de terceiros para o ciclo principal de execucao.

## Justificativa

- **Transparencia total**: schemas de ferramentas e dispatch fisico ficam no repositorio.
- **Soberania de dados**: execucao controlada pelo proprio Grimoire, sem caixas-pretas.
- **Offline-first real**: compatibilidade com runtime local (LocalAI + infraestrutura Docker).
- **Evolucao segura**: mudancas de ferramentas ocorrem via PR, com revisao e trilha historica.

## Consequencias

- O custo de manutencao da camada agentic aumenta internamente (mais codigo proprio).
- Em troca, ganhamos controle de protocolo, observabilidade e previsibilidade de runtime.
- Integracoes externas futuras so podem entrar como **adaptadores explicitos**,
  sem substituir o contrato central do `ToolRegistry`.
