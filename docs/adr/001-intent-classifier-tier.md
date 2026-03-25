# ADR 001: Alteração do Tier de Execução do Intent Classifier

**Data:** 2026-03-25  
**Status:** Aceito  
**Contexto:** O roadmap original da Fase 4 especificava o uso de um "modelo T3 leve" para a pontuação de complexidade (Intent Classification). No entanto, modelos T3 (ex: Claude 3.5, GPT-4) possuem alta latência e elevado custo por token. Usar T3 como *gatekeeper* para todas as requisições de entrada inviabilizaria a agilidade do sistema.

**Decisão:** O componente `IntentClassifier` foi rebaixado e fixado permanentemente na camada **T1**.

**Justificativa:** A classificação de intenção, quando bem roteirizada num prompt estrito, é uma tarefa determinística que pode ser executada por modelos menores (ex: Llama-3-8B ou equivalente) em milissegundos. Se o T1 identificar a necessidade, a carga pesada será repassada para T3 posteriormente.

**Consequências:**
- Redução drástica na latência de resposta inicial.
- Tratamento de JSON defensivo exigido (implementado), pois modelos menores podem gerar formatação impura (ex: markdown blocks indesejados).
