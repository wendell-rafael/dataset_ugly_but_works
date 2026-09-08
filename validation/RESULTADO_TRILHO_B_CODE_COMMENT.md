# Trilho B — triagem automática de falsos positivos por LLM

**Escopo:** comentários de código · **Data:** 08/09/2026 · **Custo:** US$ 5,59 em 5.944 chamadas

## Resumo

Doze configurações de juiz LLM foram avaliadas contra um gabarito de 371
comentários de código anotados por três humanos. **Nenhuma atingiu o critério de
publicação.** O melhor resultado — precisão de alerta de 50%, IC95 [31% – 69%] —
fica abaixo dos 60% que o plano fixou como piso, e a barra de κ ≥ 0,75 não foi
alcançada por nenhum juiz.

A recomendação é **não publicar a marcação automática** e reportar o
experimento como limitação. Isso não afeta o dataset: a precisão do léxico em
comentários de código é de **92,6%** (IC95 [89,5% – 94,8%]), medida por anotação
humana independente.

## 1. O que foi medido

| | |
|---|---|
Conjunto de avaliação | 371 comentários de código, 347 positivos / 24 negativos |
Origem | 261 de amostra aleatória simples (set/2026) + 110 herdados do teste de 385 |
Gabarito | maioria de três anotadores; κ par a par 0,787–0,829 |
Prompt | few-shot fixo, inglês, 8 exemplos, específico de comentário de código |
Métrica principal | precisão do alerta — dos itens que o juiz marcou como falso positivo, quantos o humano confirma |

Acurácia não decide nada aqui: com 93,5% de positivos, responder "é UBW" em tudo
já acerta 93,5% com κ zero. Foi exatamente o comportamento do `gemma-3-4b`.

Os 8 itens usados como exemplo no prompt foram **removidos** do conjunto de
avaliação (379 → 371), senão a medida seria otimista por construção.

## 2. Resultado por juiz

| juiz | parâmetros | alertas | precisão | IC95 | cobertura | κ |
|---|---|---|---|---|---|---|
`claude-sonnet-5` | — | 32 | 50,0% | [31 – 69] | 66,7% | **0,537** |
`grok-4.3` | — | 32 | 50,0% | [31 – 69] | 66,7% | **0,537** |
`minimax-m2.5` | — | 45 | 40,0% | [24 – 56] | 75,0% | 0,478 |
`llama-3.3-70b` | 70 B | 38 | 42,1% | [26 – 58] | 66,7% | 0,474 |
`qwen3-14b` | 14 B | 24 | 50,0% | [29 – 71] | 50,0% | 0,465 |
`qwen3-8b` | 8 B | 19 | 47,4% | [26 – 68] | 37,5% | 0,383 |
`qwen3-32b` | 32 B | 24 | 41,7% | [25 – 63] | 41,7% | 0,376 |
`qwen3-235b-a22b` | 235 B | 79 | 25,3% | [16 – 35] | 83,3% | 0,321 |
`gemma-3-12b` | 12 B | 6 | 83,3% | [50 – 100] | 20,8% | 0,316 |
`gemma-3-27b` | 27 B | 9 | 44,4% | [11 – 78] | 16,7% | 0,215 |
`llama-3.1-8b` | 8 B | 20 | 25,0% | [10 – 45] | 20,8% | 0,179 |
`gemma-3-4b` | 4 B | 0 | — | — | 0% | 0,000 |

Todos com cobertura de 371/371 itens.

## 3. Quatro achados

### 3.1 O teto é da tarefa, não do modelo

Quatro famílias independentes — Anthropic, xAI, MiniMax e Meta — param entre
**0,474 e 0,537**. O `claude-sonnet-5` e o `grok-4.3` chegam ao **mesmo κ, à
mesma precisão, ao mesmo número de alertas e ao mesmo MCC** (0,537214 nos dois).

E 0,537 é o mesmo valor que o `llama-3.3-70b` havia alcançado na rodada anterior
(200 itens, multi-artefato, prompt em português). Entre as duas rodadas mudaram o
idioma do prompt, o escopo do artefato, a taxonomia da classe negativa — extraída
das justificativas escritas pelos anotadores — e a família do melhor modelo.
**O número não se moveu.**

Isso encerra a hipótese de "modelo insuficiente". O modelo mais caro testado
custa 25× o `qwen3-14b` e empata com ele dentro do intervalo de confiança.

### 3.2 Tamanho não prediz desempenho

Na família Qwen, densa e de mesma geração: 8 B → 0,383, **14 B → 0,465**,
32 B → 0,376, 235 B → 0,321. Na Gemma: 4 B → 0,000, 12 B → 0,316, 27 B → 0,215.
A curva sobe e desce nas duas.

Isso replica Sheikhaei et al. (EMSE 2024), onde um modelo de 11 B em zero-shot
era competitivo com o estado da arte em **identificação binária** de SATD, e
Li et al. (TOSEM 2026), que registram que "identification is relatively
straightforward" — em contraste com a classificação multi-classe, onde LLM
colapsa.

Os dois extremos falham de formas opostas. O `gemma-3-4b` respondeu
`UBW-TRUE` nos 371 itens: nunca alerta. O `qwen3-235b` alerta 79 vezes, acha
83,3% dos negativos e cai a 25,3% de precisão: três falsos alarmes por acerto.
Modelo grande não ficou melhor, ficou mais desconfiado.

### 3.3 O erro é correlacionado entre os juízes

Sobreposição dos vetores de erro (índice de Jaccard):

| par | erros de cada | comuns | Jaccard |
|---|---|---|---|
`sonnet-5` × `grok-4.3` | 24 e 24 | 21 | **0,778** |
`sonnet-5` × `qwen3-14b` | 24 e 24 | 17 | 0,548 |
`sonnet-5` × `minimax` | 24 e 33 | 19 | 0,500 |
`sonnet-5` × `llama-3.3-70b` | 24 e 30 | 11 | 0,256 |
`grok-4.3` × `llama-3.3-70b` | 24 e 30 | 11 | 0,256 |

`sonnet-5` e `grok-4.3` concordam em **98,4%** dos itens e erram nos **mesmos 21
de 24**. Dois modelos de empresas diferentes cometendo o mesmo erro.

Consequência para o painel: κ juiz-juiz de 0,897 entre eles, correlação média de
erro de 0,709, e **1,24 votos efetivamente independentes de 3**. Agregar é
cosmético — a regra de maioria dá exatamente o mesmo resultado do melhor juiz
sozinho (32 alertas, 50% de precisão, 66,7% de cobertura).

Este é o cenário que o plano descreve na quarta linha do critério de decisão:
*concordância alta entre juízes com concordância baixa contra o humano é indício
de viés compartilhado, não de acerto*. Ahmed et al. (MSR 2025) alertam para
exatamente isso.

Uma nuance que vale registrar: o `llama-3.3-70b` erra em itens **diferentes**
(Jaccard 0,256 contra os dois melhores). Há diversidade a explorar, mas ela não
resolve o problema — ver 3.4.

### 3.4 Nenhuma composição de painel alcança o critério

Testando as 20 combinações de três juízes entre os seis melhores, com regra de
maioria (análise **exploratória**, não pré-registrada — a regra fixada antes da
execução era "os três melhores por κ"):

| painel | alertas | precisão | cobertura |
|---|---|---|---|
`grok` + `llama70` + `qwen14` | 27 | 55,6% | 62,5% |
`sonnet` + `grok` + `llama70` | 31 | 54,8% | 70,8% |
`sonnet` + `llama70` + `qwen14` | 26 | 53,8% | 58,3% |
| *(pré-registrado)* `sonnet`+`grok`+`minimax` | 32 | 50,0% | 66,7% |

O melhor painel exploratório chega a **55,6%** — ainda abaixo dos 60%. O
resultado negativo sobrevive até à seleção mais favorável possível, que seria
metodologicamente ilegítima por escolher o painel olhando o desfecho.

## 4. Comparação com o desempenho humano

κ par a par entre os anotadores, neste conjunto:

| par | κ |
|---|---|
Wendell × Miguel | 0,829 |
Wendell × Bruno | 0,811 |
Bruno × Miguel | 0,787 |

O melhor juiz, medido da mesma forma (par a par contra cada anotador, não contra
a maioria):

| juiz | vs Wendell | vs Bruno | vs Miguel | média |
|---|---|---|---|---|
`grok-4.3` | 0,529 | 0,628 | 0,602 | **0,586** |
`claude-sonnet-5` | 0,529 | 0,628 | 0,562 | 0,573 |
`qwen3-14b` | 0,463 | 0,568 | 0,444 | 0,492 |

O melhor juiz alcança **~72% do acordo humano** nessa régua (0,586 contra a média
humana de 0,809).

**Assimetria por anotador.** Todos os juízes concordam mais com Bruno que com
Wendell. O padrão já havia aparecido na rodada anterior, com prompt, escopo e
modelos diferentes, e é consistente com a assimetria observada na própria
anotação humana: Wendell aplica um limiar mais restritivo, com 7 itens
"Wendell não-UBW / outro UBW" contra 1 no sentido inverso.

## 5. Decisão

Pelo critério da Seção 6 do plano, fixado antes da execução:

| resultado no teste | decisão | situação |
|---|---|---|
precisão ≥ 80% | publica marcação completa | não atingido |
60% a 80% | publica só o subconjunto de ≥ 2 juízes | não atingido |
**abaixo de 60%** | **não publica; reporta como limitação** | **é o caso** |
juízes concordantes entre si e discordantes do humano | não publica: viés compartilhado | **também é o caso** |

**Duas das quatro linhas apontam para não publicar**, por caminhos
independentes. A recomendação é reportar o Trilho B como resultado negativo, com
os números acima como contribuição — não como tentativa frustrada.

O valor científico do achado está em 3.1 e 3.3: mostrar com doze configurações,
seis famílias de modelo e três ordens de magnitude de tamanho que a tarefa tem
um teto, e que ele não cede a mais parâmetro nem a prompt melhor. A literatura
tem o resultado análogo em métrica balanceada (MCC), mas não com esta amplitude
de escada de tamanho.

## 6. Ameaças à validade

**Poder estatístico limitado pelos negativos.** São 24 no conjunto, e é neles
que a cobertura é medida. Mesmo usando todos, o IC da cobertura tem ~35 pontos
de largura. Foi por isso que o pool de exemplos gastou apenas 4 dos 28
negativos disponíveis.

**Um alerta contra o κ da rodada anterior.** Na fatia de comentários de código
do conjunto de 200, havia **1 negativo em 57 itens**, e 24 de 53 juízes
obtiveram κ = 1,000 — todos emitindo exatamente 1 alerta que calhava de acertar.
Entre eles, modelos que ficaram no fundo do ranking geral. Aquele número não
media nada, e não deve ser citado.

**Janela de contexto truncada.** Em 571 dos 26.036 comentários do corpus (2,19%)
a expressão-gatilho não aparece no texto extraído: a janela de ±3 linhas é
cortada em 2.000 caracteres após a concatenação, e linha longa (arquivo
minificado) estoura o orçamento antes da linha do match. Decisão registrada:
tratar como negativo, sem recoleta. **A precisão medida é do pipeline (léxico +
janela), não do léxico isolado.**

**Quantização e provedor.** Cada juiz roda num endpoint fixado sem fallback, e o
provedor efetivo é gravado por item. Dois modelos tiveram de trocar de provedor
no meio da rodada — o endpoint original devolvia corpo vazio em ~90% das
chamadas —, o que mudou a quantização de bf16 para fp8. O `llama-3.3-70b` da
rodada anterior rodou em bf16, então a comparação entre rodadas carrega essa
variável.

**Não-determinismo residual.** Temperatura zero em todas as chamadas. Resta
variação de kernel e de versão de runtime dentro do provedor, que temperatura
não elimina.

**Tradução dos exemplos.** O rótulo e o raciocínio dos 8 exemplos são dos
anotadores; a versão em inglês que entra no prompt é tradução do autor. As duas
ficam registradas lado a lado em `validation/panel/cc/exemplar_pool.json`.

## 7. Reprodução

```bash
python3 scripts/17_build_cc_eval_set.py          # pool de exemplos + eval_371
python3 scripts/run_panel_cc.sh baratos          # 4 modelos, k=2 e k=8
python3 scripts/run_panel_cc.sh resto            # 7 modelos, k=8
python3 scripts/08_panel_analysis.py report --set eval_371
```

Artefatos: `validation/panel/cc/` (conjunto e pool),
`validation/panel/runs/eval_371/` (votos e justificativas por item),
`validation/panel/analysis/eval_371__*.csv` (métricas).

Todo run grava a justificativa do modelo por item, então a análise de erro não
exige chamada nova de API.

## Referências citadas

- Sheikhaei, Tian, Wang & Xu (2024). *EMSE* 29:159. arXiv 2405.06806.
- Li, Yin, Yang et al. (2026). IMPACT. *TOSEM* 35(4), art. 102.
- Ahmed, Devanbu, Treude & Pradel (2025). MSR 2025.
- Feinstein & Cicchetti (1990). *J Clin Epidemiol* 43(6) — paradoxo do κ.
