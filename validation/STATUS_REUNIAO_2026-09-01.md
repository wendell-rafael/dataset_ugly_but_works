# Status para reunião com orientador — Trilho B (painel de juízes LLM)

Preparado em 2026-09-01. Cobre a semana desde o fechamento do plano de
experimento (`PLANO_EXPERIMENTO_LLM.md`): o que foi implementado, o que foi
medido nos 200 itens de desenvolvimento, e o que ainda falta antes de tocar no
conjunto de teste (385) ou no corpus completo (91.458).

## 1. O que o experimento faz, em uma frase

Complementa a anotação humana (Trilho A, 92,7% de precisão, κ 0,844–0,925 entre
3 anotadores) com uma camada automática: um painel de LLMs lê cada item
capturado pelo léxico e sinaliza os que provavelmente são falso positivo —
casos em que a expressão apareceu mas não há UBW de verdade (string de teste,
citação, negação, sentido não-técnico). O produto final são duas colunas novas
no dataset: `n_judges_flagged_fp` e `panel_id`.

## 2. O que foi testado nos 200 itens de desenvolvimento

**10 modelos, todos de peso aberto**, escolhidos por família + custo, com
endpoint fixo na OpenRouter (ver Seção 5):

| Família | Modelo | Raciocina? |
|---|---|---|
| OpenAI | gpt-oss-120b | sim |
| Mistral | mistral-small-3.2-24b | não |
| Qwen | qwen3-32b | sim |
| Qwen | qwen3-coder | não |
| Google | gemma-3-27b | não |
| DeepSeek | deepseek-v3.2-exp | não |
| DeepSeek | deepseek-chat (V3) | não |
| Meta | llama-3.3-70b | não |
| Z.ai | glm-5.2 | sim |
| Moonshot | kimi-k2.5 | sim |

**4 estratégias de prompt**, todas construídas sobre o mesmo texto-base
(`03_metrics_llm_triage.py`, prompt "v1"), variando só a presença de definição
e de exemplos:

1. **zero-shot sem definição** — só os nomes dos 3 rótulos possíveis, sem
   explicar o que é UBW. Mede quanto o modelo resolve sem ajuda.
2. **zero-shot com definição** — acrescenta o parágrafo que define UBW
   (resignação funcional) e o critério de cada rótulo. É a linha de base.
3. **few-shot fixo** — definição + 6 exemplos rotulados por humanos (3
   positivos, 3 negativos), sempre os mesmos, sorteados uma vez do
   desenvolvimento.
4. **few-shot recuperado** — definição + os *k* exemplos mais parecidos com o
   item a julgar, por similaridade de texto (TF-IDF). Testado com **k=3** na
   rodada principal; k=2 e k=5 estão rodando agora (ver Seção 8).

Isso dá **40 combinações** (10 modelos × 4 estratégias) + 2 execuções antigas
de um prompt reprovado (`checklist_v2`, ver Seção 4) = **42 configurações
medidas**.

### Exemplo real de cada estratégia

Mesmo item nos 4 prompts, para mostrar exatamente o que muda. O trecho:

```
Repositório: Autodesk/synthesis | code_comment | expressão: "dirty hack"
"assert(pthread_create(&t, NULL, func, NULL) == 0); /* A dirty hack, but we
cannot rely on pthread_join in this primitive test. */ Sleep(2000);"
```
Gabarito humano: **UBW-verdadeiro**.

**1) zero-shot sem definição** — 149 caracteres de instrução de sistema, sem
explicar o que é UBW:
> "Você é um assistente de pesquisa em engenharia de software empírica. Sua
> tarefa é classificar trechos de texto extraídos de repositórios de
> software." + os 3 nomes de rótulo, sem critério.

**2) zero-shot com definição** — mesmo item, mas o prompt de sistema (635
caracteres) explica: *"admite, de forma explícita, ter aceitado uma solução
tecnicamente subótima [...] porque ela funciona"*, e o texto do usuário lista
o critério de cada um dos 3 rótulos antes de mostrar o trecho.

**3) few-shot fixo** — igual ao anterior, mas antes do item entram **6
exemplos fixos**, sempre os mesmos em toda a rodada: 3 rotulados
UBW-verdadeiro, 3 não-UBW, cada um com a justificativa que o anotador humano
escreveu quando disponível. Ex.: *"[EXEMPLO 4 — rótulo humano: não-UBW] ...
'package fix (tmp, dirty hack)' ... justificativa: resolvido em calibração
(convergiu com Wendell)"*.

**4) few-shot recuperado (k=3)** — igual à definição, mas os 3 exemplos mudam
por item: são os 3 mais parecidos com o texto que está sendo julgado, achados
por similaridade. Para este item (expressão "dirty hack"), os 3 recuperados
também usam "dirty hack", incluindo um positivo quase idêntico em estrutura
("Bit of a dirty hack but tl;dr...") e um negativo ("package fix (tmp, dirty
hack)").

## 3. Como medimos "o LLM concorda com o humano"

Kappa de Cohen — a mesma métrica que reportamos entre os 3 anotadores humanos
(κ 0,844–0,925 no conjunto de teste oficial). Nos 200 de desenvolvimento, essa
mesma métrica entre os humanos deu:

| Par de anotadores | κ |
|---|---|
| Wendell × Bruno | 0,805 |
| Wendell × Miguel | 0,817 |
| Bruno × Miguel | 0,852 |

É a régua de comparação: **quanto o melhor LLM chega perto disso.**

### Duas correções de método que mudaram o resultado, e por quê

**Correção 1 — comparar contra cada anotador, não contra a maioria.** A
primeira leitura comparava o LLM contra o voto majoritário dos 3 humanos. Isso
é uma régua mais fácil: a maioria já filtra o ruído de um anotador individual.
Para comparar com os 0,805–0,852 acima — que são par a par — o LLM também
precisa ser comparado par a par contra cada um dos 3, e depois tirar a média.

**Correção 2 — abstenção conta como erro, não desaparece da conta.** O LLM pode
responder "incerto". O cálculo de kappa original excluía esses itens do
cálculo — e isso premiava quem abstinha nos casos difíceis, porque o item
difícil simplesmente saía do denominador. Corrigido: "incerto" agora conta como
se o juiz tivesse dito "não é falso positivo" (é a leitura operacional real —
um juiz que não decide não gera alerta, exatamente como um juiz que decide
"UBW-verdadeiro").

**O efeito das duas correções foi inverter o ranking:**

| Juiz | Abstenções | κ ingênuo (vs. maioria) | κ correto (vs. anotador, penalizado) |
|---|---|---|---|
| deepseek-chat, few-shot fixo | 48 / 200 (24%) | 0,622 (1º lugar) | 0,446 |
| kimi-k2.5, few-shot fixo | 23 / 200 | 0,588 (2º lugar) | 0,479 |
| qwen3-coder, zero-shot | 54 / 200 (27%) | 0,611 | 0,338 |
| **llama-3.3-70b, few-shot fixo** | **1 / 200** | 0,558 | **0,537 (1º lugar)** |

Os dois primeiros colocados na leitura ingênua eram os que mais se recusavam a
decidir. Corrigido, o líder é `llama-3.3-70b` em few-shot fixo, que decide quase
tudo (1 abstenção em 200).

## 4. Resultado principal

**Nenhuma configuração testada chega perto do acordo humano-humano.** O melhor
resultado — `llama-3.3-70b`, few-shot fixo — tem κ = **0,537** contra a régua
correta. O pior par de humanos (Wendell×Bruno) tem κ = 0,805. É uma diferença
de 0,27, não pequena.

**Métricas completas do juiz líder** (200 itens, 173 positivos / 27 negativos):

| Métrica | Valor |
|---|---|
| Kappa (vs. cada anotador, penalizado) | 0,537 |
| Precisão do alerta | 68,2% (IC 95%: 50,0%–86,4%) |
| Cobertura (dos 27 negativos reais, quantos o juiz achou) | 55,6% (15 de 27) |
| Alertas emitidos | 22 de 200 |
| Falsos positivos do próprio juiz (disse "não-UBW" errado) | 7 |
| Abstenções | 1 |

O intervalo de confiança da precisão do alerta é largo (50–86%) porque só há
22 alertas — número pequeno. Isso só fecha com mais confiança nos 385 do
conjunto de teste.

**O painel de múltiplos juízes não ajuda.** Medimos quantos "votos
independentes" o conjunto de juízes realmente entrega (correlação de erro
entre eles) — deu **1,44 de 3**, isto é, os juízes erram nos mesmos itens.
Juntar 3 opiniões correlacionadas não é melhor que uma opinião só. A regra de
agregação que o próprio protocolo escolheu automaticamente foi **"melhor juiz
sozinho"**, não maioria nem votação ponderada.

**O prompt reprovado, para contexto.** Uma variante anterior (`checklist_v2`,
que transformava a definição de UBW em checklist rígido de 5 condições) tinha
sido testada em agosto e reprovada: κ ≈ 0 — o modelo passou a rejeitar quase
tudo, inclusive itens que os humanos aceitam sem discussão (88% dos "temporary
fix" foram aceitos por humanos, o checklist rejeitava quase todos). O achado
foi que **o critério escrito no guideline de anotação é mais estrito do que o
que os anotadores de fato praticam** — é um achado sobre o próprio instrumento
de anotação, não um bug de prompt. Está descartado; o prompt atual (o "v1"
usado nas 4 estratégias acima) é o validado.

## 5. O que corrigimos no código nesta semana

Rodar a matriz completa (8.400 chamadas de API) expôs 6 defeitos reais, todos
corrigidos:

1. **Gabarito com contagem errada.** A coluna `unanime` usava `isin()` com uma
   lista contendo uma Series — Python descarta isso em silêncio. Contava 21
   itens unânimes quando o real são 188. Corrigido antes de qualquer medição
   valer.
2. **Falha de API virava rótulo permanente.** A lógica de retomada (que evita
   reprocessar itens já feitos) tratava qualquer item já gravado como
   "concluído" — inclusive os que falharam por rate limit ou erro de rede.
   Numa execução de horas contra rate limit, isso teria produzido itens
   `incerto` fabricados por falha técnica, permanentes.
3. **Modelos de raciocínio truncavam.** `kimi-k2.5` gera em média 757 tokens de
   saída (raciocínio incluído) antes do JSON final; o teto inicial de 300, depois
   1.000, cortava a resposta no meio em quase todos os itens. Subiu para 2.500.
4. **Corrida de threads no índice de busca.** Rodando com múltiplos workers em
   paralelo, duas threads podiam competir para construir o índice de
   similaridade (usado no few-shot recuperado) e uma terceira lia uma versão
   incompleta, quebrando a execução. Corrigido com lock.
5. **Exemplos recuperados só ensinavam "sim".** Medido: em 70% dos itens, os 3
   exemplos que a busca por similaridade trazia eram todos positivos — porque
   a busca encontra a própria expressão-gatilho repetida, não o critério de
   julgamento. Corrigido com cota mínima de 1 exemplo negativo + preferência
   por exemplos que tenham justificativa humana escrita. Caiu para 0%.
6. **Um "modelo" era, na prática, dez provedores diferentes.** A OpenRouter
   roteava a mesma chamada ao `gpt-oss-120b` para até 10 provedores distintos,
   alguns rodando o peso em precisão diferente (bf16 vs. fp4) pelo mesmo preço.
   Sem fixar isso, "o juiz gpt-oss-120b" não era um classificador único.
   Corrigido: cada juiz agora usa um endpoint fixo, escolhido pela maior
   precisão disponível, sem fallback automático.

## 6. Perguntas prováveis do orientador, com resposta pronta

**"Por que nenhum modelo chega perto do humano?"** Regime de prevalência
difícil (86,5% de positivos no dev) combinado com poucos negativos (27) — o
sinal que distingue os LLMs bons dos ruins está todo concentrado numa fatia
pequena dos dados. Modelos generalistas, sem calibração específica para esse
critério, erram justamente nessa fatia. É consistente com o que a literatura
mais recente relata sobre painéis de LLM como juízes (Kohli, 2026 — painéis
de LLM entregam poucos "votos independentes" mesmo quando parecem diversos).

**"Isso invalida a coluna automática do dataset?"** Não necessariamente. O
plano já previa essa possibilidade: a Seção 6 (Critérios de decisão) diz que
precisão do alerta entre 60–80% publica só o subconjunto de maior confiança, e
abaixo de 60% não publica nada — a métrica real (precisão do alerta = 68,2% no
dev) ainda não decide nada, porque a decisão oficial só vale sobre o conjunto
de teste (385), usado uma única vez.

**"Por que não testar todos os 10 modelos direto nos 385?"** Porque o
conjunto de teste é recurso de uso único — testar tudo nele destruiria sua
validade como avaliação independente. Por isso existe a etapa de
desenvolvimento: filtrar e escolher a configuração aqui, congelar, e só então
gastar o teste uma vez.

**"Quanto isso custou?"** US$ 2,80 na matriz completa dos 200 itens (8.400
chamadas). A varredura adicional de k e de esforço de raciocínio (Seção 8)
custa mais ~US$ 2,50-3,00. Rodar o juiz escolhido nos 385 custa menos de
US$ 0,30. O corpus completo (91.458 itens), só com o juiz vencedor, fica na
faixa de US$ 10-15.

**"O painel usa vários modelos votando, como um comitê?"** Era a intenção
original do plano, mas os dados mostraram que não compensa: os juízes erram
nos mesmos itens (1,44 votos independentes de 3), então agregar não melhora
sobre usar o melhor juiz sozinho. O próprio protocolo (pré-registrado antes de
rodar, para não decidir isso *depois* de ver o resultado) escolheu essa regra
automaticamente.

## 7. Decisões a debater na reunião

Três, em ordem de impacto. Nenhuma tomada sozinho porque todas mudam o número
que vai ao artigo.

**Decisão 1 — qual versão do prompt congelar (Seção 12).** O recorte por prefixo
dá κ 0,559; o recorte centrado na expressão dá 0,442. O segundo é
metodologicamente correto (o juiz vê o que deveria julgar), e a diferença existe
porque o primeiro **acertava por acidente** em itens onde o modelo rejeitava por
não encontrar a expressão. Minha leitura: a correção deve ficar, e o número
reportado passa a ser o menor. Reportar 0,559 sabendo de onde ele vem seria
inflar o resultado.

**Decisão 2 — como tratar a abstenção no ranking.** Já implementei o κ
penalizado (abstenção conta como não-alerta, item não sai do denominador) e ele
está sendo usado como critério de seleção. Vale confirmar que o orientador
concorda com essa convenção, porque ela inverteu o ranking: os dois primeiros
colocados na leitura ingênua eram os que mais se recusavam a decidir.

**Decisão 3 — congelar agora ou esperar.** A varredura de k e de
`reasoning-effort` (Seção 8) termina de madrugada. Custa pouco e pode mudar o
líder. Como o conjunto de teste é de uso único, vale congelar com os dados
completos em vez de com os parciais.

**Não decidido de propósito:** rodar o conjunto de teste (385). É recurso de uso
único e não havia necessidade para esta reunião.

## 8. Em andamento (não fazia parte da rodada original, iniciado hoje)

Dois testes que o plano promete mas a rodada principal não cobriu, disparados
em paralelo à escrita deste documento:

- **Varredura de k no few-shot recuperado** (k=2 e k=5, além do k=3 já
  medido) — testa se o número de exemplos recuperados por similaridade muda o
  resultado. 10 modelos × 2 valores de k = 20 execuções extras.
- **`reasoning-effort=low`** nos 4 modelos que raciocinam (gpt-oss-120b,
  qwen3-32b, kimi-k2.5, glm-5.2) — medido antes que gastar menos tokens de
  raciocínio não piora a concordância com o humano e reduz custo em até 32%
  no corpus completo.

## 8. Em andamento (não fazia parte da rodada original, iniciado hoje)

Dois testes que o plano promete mas a rodada principal não cobriu, disparados
em paralelo à escrita deste documento:

- **Varredura de k no few-shot recuperado** (k=2 e k=5, além do k=3 já
  medido) — testa se o número de exemplos recuperados por similaridade muda o
  resultado. 10 modelos × 2 valores de k = 20 execuções extras.
- **`reasoning-effort=low`** nos 4 modelos que raciocinam (gpt-oss-120b,
  qwen3-32b, kimi-k2.5, glm-5.2) — medido antes que gastar menos tokens de
  raciocínio não piora a concordância com o humano e reduz custo em até 32%
  no corpus completo.

## 9. Baselines clássicos — FEITO (Seção 4.2.2 do plano)

Implementados em `scripts/09_classical_baselines.py` e executados. TF-IDF +
regressão logística e TF-IDF + XGBoost, avaliados por validação cruzada
estratificada repetida (5 folds × 5 repetições) **dentro dos 200** — não no
conjunto de teste, que fica reservado.

| Modelo | κ médio | desvio | MCC | Alertas | Precisão do alerta | Cobertura |
|---|---|---|---|---|---|---|
| TF-IDF + regressão logística | 0,108 | 0,043 | 0,121 | 13 | 38,5% | 18,5% |
| TF-IDF + XGBoost | 0,199 | 0,056 | 0,200 | 31 | 25,8% | 29,6% |
| *(referência: melhor LLM)* | *0,537* | — | *0,562* | *22* | *68,2%* | *55,6%* |

**Resultado útil para o argumento do artigo:** um classificador de texto
treinado do zero, sem nenhum conhecimento de mundo, fica em κ 0,11–0,20 — muito
abaixo do melhor LLM (0,537). Isso mostra que o ganho dos LLMs não é artefato da
métrica nem da prevalência: eles realmente trazem informação que o texto sozinho
não dá. É a comparação que justifica usar LLM em vez de um modelo simples.

Limitação declarada no próprio script: com 27 negativos em 200, cada fold de
validação tem 5–6 negativos, então as estimativas na classe de interesse são
instáveis. Os números existem para comparação na mesma escala, não para
sustentar afirmação isolada sobre os baselines.

## 10. Ablação de `category_ubw` — FEITA, e o viés não é detectável

O prompt informava ao juiz a categoria léxica que o próprio pipeline já tinha
atribuído (`- Categoria léxica atribuída automaticamente: A`). Isso é pista a
favor do positivo — o modelo lê "o sistema já achou que é UBW" num conjunto que
já tem 86,5% de positivos. Era ameaça à validade declarada em aberto no plano.

Implementado como flag `--drop-category`: o prompt sai idêntico, menos essa
linha. Resultado nas duas configurações já concluídas:

| Configuração | κ com categoria | κ sem categoria | Delta | Δ taxa de positivos |
|---|---|---|---|---|
| llama-3.3-70b, few-shot fixo | 0,559 | 0,543 | **−0,015** | −0,005 |
| llama-3.3-70b, zero-shot | 0,469 | 0,507 | **+0,038** | −0,005 |

**Os deltas são pequenos e apontam em direções opostas.** Ambos ficam bem abaixo
do limiar de ~0,10 que a medição do truncamento (Seção 12) estabeleceu como
diferença real neste tamanho de amostra. A taxa de positivos — que é o que mais
deveria se mover se houvesse viés pró-positivo — muda meio ponto percentual nos
dois casos.

Leitura honesta, aplicando a própria régua: **o efeito não é detectável com
n = 200**, o que não é a mesma coisa que "não existe". Mas é suficiente para
rebaixar essa ameaça de "não medida" para "medida, sem efeito aparente" no texto
do artigo.

O terceiro par (`kimi-k2.5` few-shot fixo) confirma: κ 0,493 com categoria,
0,493 sem — delta **exatamente zero**.

### Um defeito de análise encontrado ao fechar esta seção

Ao consolidar os seis pares descobri que as execuções `nocat` do `deepseek-chat`
tinham **200 de 200 chamadas falhadas** (rate limit), e o fail-safe grava essas
falhas como label `incerto`. Meu primeiro cálculo tratou isso como abstenção
legítima e produziu κ = 0,000 — número que parecia resultado e não era.

Isso expôs um defeito no próprio script de análise: `08_panel_analysis.py`
carregava registros com `ok: False` e os contava como abstenção do modelo,
atribuindo à prudência do juiz o que era falha de rede. **Corrigido:** esses
registros agora viram ausência de voto, e uma execução majoritariamente falha é
descartada pelo filtro de cobertura.

Impacto sobre o que já foi reportado: **nenhum**. O total de falhas é 5,6% dos
registros, concentrado nas execuções novas (`nocat`, `k2`, `k5`) que ainda
estavam rodando. O juiz líder e as 42 configurações da eliminatória principal
têm zero ou quase zero falhas, e o ranking do topo não mudou após a correção.
As execuções contaminadas estão sendo reprocessadas.

## 11. Análise de erro — FEITA (Etapa 5 do plano)

Implementada em `scripts/10_error_analysis.py`. Não custa API: a justificativa do
modelo já é gravada por item, então a etapa é filtragem e leitura.

O juiz líder erra em **19 de 200 itens (9,5%)** — 12 deixando passar falso
positivo, 7 alertando indevidamente. Onde o erro se concentra:

**Por tipo de artefato.** `code_comment`: **zero erros em 57 itens**.
`commit_message`: 14,7%. `pr_body`: 10,4%. Comentário de código é o artefato em
que o critério é mais nítido — o texto está colado no código que ele descreve.

**Por comprimento.** Mediana de 309 caracteres nos itens que acerta, **137 nos
que erra**. Texto curto dá menos contexto e o juiz erra mais.

**Sobreposição com a discordância humana — o achado mais importante:**

| Itens | Total | Erros do juiz | Taxa |
|---|---|---|---|
| Humanos **unânimes** | 188 | 14 | **7,4%** |
| Humanos **divergiram** | 12 | 5 | **41,7%** |

O juiz erra **5,6× mais** justamente onde os três anotadores também não
concordaram entre si. Isso muda a leitura do erro: boa parte não é o modelo
sendo burro, é a zona de ambiguidade genuína do critério de UBW. Onde os humanos
têm certeza, o juiz acerta 92,6% das vezes.

### O padrão vale para o painel inteiro, não só para o líder

Testei em todos os 50 juízes com execução completa, para descartar que fosse
ruído de um caso:

| | Taxa de erro média |
|---|---|
| Itens em que os humanos foram unânimes (188) | **13,3%** |
| Itens em que os humanos divergiram (12) | **41,7%** |
| Razão média | **4,0×** |

**47 dos 50 juízes** erram mais nos itens não-unânimes. Só 3 não seguem o
padrão. Isso deixa de ser observação anedótica e vira resultado: **a dificuldade
que os LLMs têm acompanha a dificuldade que os humanos tiveram**. Os modelos não
estão errando aleatoriamente — estão errando onde o critério é objetivamente
ambíguo.

É um argumento forte para o artigo: parte do teto de κ ≈ 0,54 observado não é
limitação dos modelos, é limitação do próprio critério de anotação naquela faixa
de casos. E sugere um uso concreto para a camada automática que não é o
originalmente planejado — **discordância entre juízes como detector de itens que
merecem revisão humana**, em vez de como rótulo final.

## 12. Defeito de prompt encontrado pela análise de erro

Lendo as justificativas do modelo apareceu uma resposta suspeita: *"A expressão
'stopgap' não está presente no trecho fornecido"*. Investiguei, e o modelo
estava certo.

O prompt corta o corpo do artefato nos **primeiros 2.000 caracteres**. Em textos
longos, a expressão que disparou a coleta às vezes fica **depois** do corte — o
juiz é instruído a avaliar se "a expressão X indica UBW" recebendo um texto que
não contém X.

Quantificado:

| Situação | Dev (200) | Teste (385) |
|---|---|---|
| Expressão ausente do `body_text` inteiro (problema da coleta) | 13 | 29 |
| Expressão perdida pelo corte de 2.000 caracteres (problema do prompt) | 6 | 3 |
| **Total em que o juiz não vê a expressão** | **19 (9,5%)** | **32 (8,3%)** |

E o efeito no desempenho é grande:

| | Itens | Erros | Taxa |
|---|---|---|---|
| Juiz **vê** a expressão | 181 | 13 | **7,2%** |
| Juiz **não vê** a expressão | 19 | 6 | **31,6%** |

**32% de todos os erros do melhor juiz vêm de 9,5% dos itens** — aqueles em que
ele não tinha como acertar.

**Correção implementada:** flag `--center-window`, que recorta os 2.000
caracteres **em torno da expressão** em vez de pegar o prefixo. Recupera
exatamente os 6 itens perdidos por truncamento no dev. Ficou como opção e não
como padrão de propósito: mudar o padrão tornaria as 42 execuções já feitas
não-comparáveis em silêncio.

### O resultado da correção foi o oposto do esperado — e é o achado mais fino da noite

Rodei o juiz líder com a janela centrada. **O κ caiu de 0,559 para 0,442.**

O diagnóstico, item a item, nos 6 recuperados:

| Item | Gabarito | Com prefixo | Com janela |
|---|---|---|---|
| 1 | UBW | não-UBW ✗ | UBW ✓ |
| 2 | não-UBW | não-UBW ✓ | UBW ✗ |
| 3 | não-UBW | não-UBW ✓ | não-UBW ✓ |
| 4 | UBW | não-UBW ✗ | não-UBW ✗ |
| 5 | não-UBW | não-UBW ✓ | UBW ✗ |
| 6 | não-UBW | não-UBW ✓ | UBW ✗ |

Sem ver a expressão, o juiz respondia **"não-UBW" nos seis** — rejeitava por não
encontrar o que deveria avaliar. E quatro deles **eram** negativos de verdade:
**o juiz acertava pelo motivo errado**. Com a janela, ele passa a ver a
expressão, julga de fato, e erra em quatro.

Duas conclusões, ambas relevantes para o artigo:

1. **O κ de 0,559 estava parcialmente inflado por acerto acidental.** O 0,442 é
   a medida mais honesta da capacidade real do modelo. Isso não significa que a
   janela centrada seja pior — significa que a métrica anterior estava sendo
   ajudada por um defeito.
2. **Apenas 5 rótulos mudaram em 200, e isso derrubou o κ em 0,12.** É a
   demonstração empírica mais direta da fragilidade que já vínhamos declarando:
   com 27 negativos, meia dúzia de decisões muda o resultado inteiro. Qualquer
   diferença de κ menor que ~0,10 entre dois juízes deste ranking não deve ser
   lida como diferença real.

**Decisão a tomar com o orientador:** qual das duas versões congelar. A janela
centrada é metodologicamente mais correta (o juiz vê o que deveria julgar), mas
tem κ menor. Minha leitura é que a correção deve ficar, justamente porque o
número maior vinha de um artefato — mas é decisão que muda o resultado
reportado, então não tomei sozinho.

Os outros 13 itens (expressão ausente do texto guardado) são problema da coleta,
não do prompt — vale investigar se o `body_text` está sendo truncado na
mineração ou se o match ocorreu em outro campo.

## 13. QP3 (detector externo) — BLOQUEADA, com motivo concreto

Tentativas desta madrugada, todas registradas para não parecer pendência
escondida:

**MT-MoE-BERT (IMPACT, Li et al. TOSEM 2026).** Repositório clonado
(`github.com/yepYoung/SATD-IMPACT`) — o código está lá, mas **os pesos não**.
O README aponta para um file-box da Universidade de Nanjing
(`box.nju.edu.cn`), e o link redireciona para `/accounts/login/`: exige conta
institucional. Sem os pesos, não há como executar o modelo.

**Modelos do mesmo grupo no HuggingFace.** Existem três
(`chaos1203/satd-glm4-9b-chat-sft` e variantes), mas são GLM4-9B fine-tunados —
LLMs generativos de 9 bilhões de parâmetros. Rodar em CPU sem GPU é inviável
pela mesma análise de hardware já feita (latência de minutos por item).

**Alternativas BERT no HuggingFace.** `aavvvv/mt-bert-satd` e
`aavvvv/satd-identify` parecem promissores pelo nome, mas o `config.json` dos
dois mostra `architectures: ["BertForMaskedLM"]` — são modelos de linguagem
mascarada, **sem cabeça de classificação**. Usá-los exigiria treinar o
classificador nós mesmos, o que descaracteriza o braço: deixaria de ser
"detector externo independente" e viraria "modelo que nós treinamos".

**DebtHunter (Sala et al., EASE 2021).** O repositório original
(`RiccardoRubei/DebtHunter`) foi removido do GitHub. Achei um fork
(`suu-y/SATDBailiff-DebtHunter`) que **contém os modelos pré-treinados**
(`DHbinaryClassifier.model`, Weka serializado) e o jar executável com Weka
embutido — e há Java 25 na máquina. Tecnicamente viável. Porém a execução do
jar foi **bloqueada pela política de segurança do ambiente** em que trabalhei,
e não tentei contornar. É o caminho mais promissor para destravar QP3, e
precisa ser rodado manualmente ou com permissão explícita.

**Recomendação para a reunião:** QP3 depende de acesso que não temos hoje. Ou
se pede os pesos aos autores do IMPACT por e-mail, ou se roda o DebtHunter
localmente (caminho mais curto — os artefatos já estão baixados em
`scratchpad/dh/lib/DebtHunter-Tool/`). Não é falta de implementação, é falta de
acesso, e vale decidir qual das duas portas bater.
