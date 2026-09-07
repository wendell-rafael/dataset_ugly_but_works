# Comparativo — Ensemble multi-modelo para triagem LLM em escala

Documento de apoio para a reunião de quarta-feira (2026-08-05). Reúne preço,
abordagem técnica já implementada e o que ainda precisa ser decidido.

---

## 1. Situação atual (bloqueio real, não hipotético)

Duas coisas impedem rodar a validação completa agora:

- **Os 200 itens de medição ainda não têm rótulo humano.** As colunas
  `is_ubw`/`confidence`/`observacao` em `validation/batches_3anotadores/*.csv`
  estão vazias — Wendell, Miguel e Bruno ainda não preencheram. Sem isso, não
  dá para comparar modelo contra humano, só modelo contra modelo.
- **`ANTHROPIC_API_KEY` está vazia no `.env`.** `OPENROUTER_API_KEY` está
  preenchida. Ou seja, hoje só dá para rodar modelos via OpenRouter
  (DeepSeek, Qwen, Kimi, GLM), não Claude.

O que dá para fazer agora, sem esperar nada: rodar `ensemble-triage` nos 200
itens de medição só com modelos OpenRouter, deixando os rótulos prontos.
Quando a anotação humana voltar, `ensemble-validate` cruza os dois na hora —
sem precisar rodar a triagem de novo.

---

## 2. Comparativo de preço (corpus inteiro, 91.458 itens — exclui `issue_body`)

Estimativa de tokens por chamada baseada no tamanho real dos artefatos em
`data/full_run/ubw_collected_consolidated.csv`: ~500 tokens de entrada, ~150
de saída.

| Modelo | Origem | Preço in/out ($/1M tokens) | Custo full-corpus | Custo nos 200 de medição |
|---|---|---|---|---|
| Claude Fable 5 | Anthropic | $10 / $50 | $1.143 | $1,37 |
| Claude Sonnet 5 (intro) | Anthropic | $2 / $10 | $229 | $0,27 |
| Claude Haiku 4.5 | Anthropic | $1 / $5 | $114 | $0,14 |
| Kimi K2.5 | Moonshot | $0,375 / $2,025 | $45 | $0,05 |
| GLM-4.6 | Zhipu | $0,43 / $1,75 | $44 | $0,05 |
| Qwen3.6 Plus | Alibaba | $0,325 / $1,95 | $42 | $0,05 |
| Qwen3 Coder | Alibaba | $0,30 / $1,00 | $27 | $0,03 |
| **DeepSeek V3.2** | DeepSeek | $0,21 / $0,32 | **$14** | **$0,03** |

Free tier (`:free` no OpenRouter): existe, mas o catálogo roda muito rápido
(perdeu 7 endpoints gratuitos em 9 dias em julho/2026) e tem teto de 50
req/dia (1.000/dia com $10 de crédito prévio). Nos 200 itens de medição cabe
folgado e sem custo. No corpus inteiro (91.458 itens), 1.000/dia levaria 91
dias — inviável para o cronograma. Nos 200 itens, sai de graça; no resto,
paga-se sempre.

Com Batch API da Anthropic (50% de desconto, assíncrono), o custo dos
modelos Claude no full-corpus cai pela metade (ex.: Sonnet 5 vai de $229
para ~$114). OpenRouter não tem desconto de batch equivalente documentado
até agora.

---

## 3. Abordagem já implementada (`scripts/03_metrics_llm_triage.py`)

Dois subcomandos novos, além dos três que já existiam (`sample`,
`llm-triage`, `metrics`):

- **`ensemble-triage`** — roda N modelos (`--models provider:model
  provider:model ...`) no mesmo candidato. Cada modelo grava sua própria
  coluna de rótulo. Regra de decisão: só aceita direto se **todos** os
  modelos concordarem no binário UBW/não-UBW; qualquer "incerto" de
  qualquer modelo, ou divergência entre eles, marca
  `requires_human_review = True` — mesmo tratamento que "incerto" sozinho
  já recebia no modo de um modelo só. Incremental e retomável: interrompe e
  continua de onde parou, sem reprocessar o que já foi feito.

- **`ensemble-validate`** — roda sobre a saída de `ensemble-triage` já
  cruzada com o rótulo humano (join feito por fora, antes de chamar o
  comando). Reporta κ de cada modelo contra o humano (mesmo critério de
  descarte já usado no plano: κ < 0,61 descarta) e κ par a par entre os
  modelos — dois modelos concordando muito entre si mas pouco com o humano
  é sinal de viés sistemático compartilhado, não confiabilidade real
  (Zheng et al., 2023, já citado em `A2_CRITICA_LLM_ANOTADOR.md`).

Fluxo completo: gate nos 200 de medição → decide se libera o full-corpus →
full-corpus vira camada descritiva/exploratória da dissertação, nunca
substitui os 385 anotados como âncora de precisão (isso continua fixo,
Trilho A já documentado em `PLANO_AVALIACAO_PRECISAO.md`).

---

## 4. Fundamentação na literatura — outros fazem isso? é o melhor jeito?

**Sim, tem precedente direto no domínio SATD**, mas não do jeito que estamos
fazendo. Um estudo já comparou três LLMs (Claude 3 Haiku, GPT-3.5 Turbo,
Gemini 1.0 Pro) contra o modelo estado-da-arte para identificação de SATD,
usando MCC como métrica. Resultado: os LLMs chegam perto do especializado,
mas com desbalanceamento maior na matriz de confusão; engenharia de prompt
cuidadosa melhora o viés. Esse estudo comparou os três modelos **de forma
independente**, sem ensemble nem votação entre eles — é o precedente mais
próximo, mas não é a mesma técnica.

**Ensemble de múltiplos LLMs para classificação de texto é linha de
pesquisa ativa em 2025/2026**, fora do domínio SATD. "Majority Rules: LLM
Ensemble is a Winning Approach for Content Categorization" (arXiv
2511.15714) testa 10 LLMs em conjunto contra taxonomia hierárquica do IAB:
o ensemble ganha até 65% de F1 sobre o melhor modelo individual, porque
reduz inconsistência, alucinação e erro de categoria que cada modelo sozinho
carrega. Suporta a ideia geral, mas não usa exatamente nossa regra de
decisão (unanimidade → aceita, senão humano).

**Nossa regra (unanimidade ou revisão humana) é conservadora, não é a mais
sofisticada que a literatura recente oferece.** Dois pontos relevantes:

- "Beyond Majority Voting: Agreement-Based Clustering..." (arXiv
  2605.09955) argumenta que voto majoritário simples **não é ótimo** para
  tarefas subjetivas — clustering por perfil de concordância entre
  anotadores captura melhor a variação real de julgamento do que só contar
  votos. `is_ubw` tem exatamente esse componente subjetivo (near-misses do
  guideline, Seção 6).
- O método mais estabelecido para combinar **múltiplos rotuladores ruidosos
  sem gabarito** é o modelo de Dawid-Skene (1979, EM), hoje adaptado
  explicitamente para múltiplos LLMs como anotadores, e o Snorkel/weak
  supervision (Ratner et al.) — em vez de exigir unanimidade, aprende a
  confiabilidade de cada modelo/rotulador e devolve um rótulo probabilístico
  ponderado por essa confiabilidade. Isso é estatisticamente mais principiado
  que nossa regra binária de unanimidade.
- Contraponto que já vale considerar antes de aumentar o ensemble: existe
  achado de que repetir consultas ao mesmo modelo (ou empilhar mais modelos)
  segue uma curva **não-monotônica** — melhora até certo ponto, depois piora,
  porque adiciona ruído nos itens difíceis mesmo enquanto ajuda nos fáceis.
  Ensemble maior não é sempre melhor.

**Conclusão honesta para a quarta:** nossa regra atual (unanimidade → aceita,
qualquer divergência ou "incerto" → humano) é defensável e está alinhada com
o desenho responsável que Ziems et al. (2024) recomenda — já citado em
`A2_CRITICA_LLM_ANOTADOR.md` — mas não é o estado da arte. O upgrade mais
rigoroso seria Dawid-Skene/Snorkel no lugar da regra de unanimidade, trocando
"todos concordam" por um modelo estatístico de confiabilidade por modelo.
Fica pra decidir na quarta se vale o esforço extra de implementar isso, ou
se a regra simples já é suficiente dado que os 385 humanos continuam sendo a
âncora de precisão de qualquer forma.

---

## 5. O que falta decidir na quarta

1. **Qual combinação de modelos usar no full-corpus.** Cotação pronta em
   cima; a inclinação atual é DeepSeek V3.2 como segundo modelo (mais
   barato, laboratório diferente da âncora Claude), mas a decisão final e a
   âncora Claude (Sonnet 5 ou Haiku 4.5) ficam para quarta.
2. **Se libera orçamento para `ANTHROPIC_API_KEY`.** A chave está vazia
   hoje — sem ela, o lado Claude do ensemble não roda, nem no gate dos 200
   nem no full-corpus.
3. **Se vale esperar a anotação humana antes de gastar no full-corpus,** ou
   rodar o full-corpus em paralelo e só cruzar depois (risco: gastar no
   full-corpus e o gate reprovar o ensemble por baixa concordância com o
   humano — aí o dinheiro do full-corpus não vira dado, só uma triagem já
   feita mas invalidada como *ground truth* adicional).
4. **Prazo real:** full-corpus com Batch API dura horas a poucos dias,
   dependendo do provedor; o gargalo verdadeiro é a anotação humana dos 200
   de medição, que ainda não voltou.
5. **Regra de decisão do ensemble: unanimidade simples (atual) ou
   Dawid-Skene/Snorkel (mais rigoroso, mais esforço de implementação)?**
   Ver Seção 4 — a regra simples já está implementada e rodou nos 200 itens;
   trocar por agregação probabilística é possível, mas não é trivial e só
   vale o esforço se o orientador achar que a defesa metodológica exige.

---

## 6. Resultado real da rodada nos 200 de medição (2026-07-31)

Já rodado, antes da anotação humana voltar (fica pronto pra cruzar assim que
ela chegar): DeepSeek V3.2 + Qwen3 Coder, `validation/ensemble_medicao_200.csv`.

- 118/200 (59%) os dois modelos concordam entre si → aceito direto do LLM.
- 23/200 (11,5%) modelos divergem entre si → força revisão humana.
- 61/200 pelo menos um modelo disse "incerto" → força revisão humana.
- Total na fila de revisão humana: 82/200 (41%).
- Distribuição bruta: DeepSeek 145 UBW-verdadeiro / 51 incerto / 4 não-UBW;
  Qwen3 Coder 151 / 44 / 5 — parecidos entre si, mas isso sozinho não prova
  confiabilidade (pode ser viés compartilhado, só o cruzamento com o rótulo
  humano decide — Seção 3 e 4 acima).
- Custo real: ~$0,05 nos dois modelos juntos.
