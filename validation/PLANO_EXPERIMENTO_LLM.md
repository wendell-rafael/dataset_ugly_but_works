# Plano de experimento — triagem automática do corpus UBW

> **Revisão de escopo, 02/09/2026.** O dataset passou a ser restrito a
> **comentários de código**. Em consequência, a análise de precisão por
> expressão do léxico (antiga QP2, e a QPG que a englobava) saiu do desenho,
> junto com a correção de Rogan-Gladen que existia para sustentá-la. As seções
> abaixo já refletem o escopo novo; o histórico da versão multi-artefato está
> nos resultados de `validation/panel/analysis/`, que continuam válidos como
> medida do que foi rodado.

## 1. Objetivo e escopo

O experimento produz e calibra uma camada de validação automática sobre os
**26.036 comentários de código** do corpus, sinalizando quais itens capturados
pelo léxico são de fato Self-Admitted Technical Debt do subtipo *ugly but
works*. A camada é complemento da anotação humana, nunca substituta: a precisão
reportada no artigo vem exclusivamente do Trilho A.

O gabarito é o conjunto de validação de **379 comentários** (110 herdados da
amostra multi-artefato mais 269 sorteados em 02/09/2026), dimensionado por
Cochran a 95% de confiança e margem de 5%, com p = 0,50 e correção de população
finita. Somam-se a ele os **57 comentários** do conjunto de calibração, que
seguem reservados ao desenvolvimento — foram usados para escolher prompt,
modelo e regra de agregação, e por isso não entram na validação.

A saída do experimento é dupla: duas colunas novas no dataset publicado e um
pacote de replicação com os prompts e os passos executados.

**O que o experimento não mede.** Cobertura. Não estimamos quanto UBW existe
fora do alcance do léxico — isso exigiria varrer o texto bruto dos projetos e
anotar um denominador que não temos. A precisão aqui é sempre **condicionada ao
léxico**: que fração dos itens capturados é UBW real. A redação inversa
("recuperação") seria erro de construto.

**Nota sobre o léxico neste escopo.** Das 25 expressões, **24 ocorrem em
comentários de código**; `terrible but works` aparece somente em issues,
commits e PRs. A amostra de validação é aleatória simples e, por isso,
autoponderada — cada item representa a mesma fração do corpus, e a precisão
global é a proporção direta de positivos, sem reponderação. Como consequência
do sorteio simples, 13 das 24 expressões estão representadas na amostra; as
demais têm poucas ocorrências no corpus e não sustentariam estimativa própria
mesmo sob censo (`duct tape fix` tem 3 ocorrências, `horrible but works` tem 4).

## 2. Questões de pesquisa

**QP1.** Quão bem as LLMs reproduzem o consenso dos três anotadores no conjunto
de validação, e o que a estrutura do erro revela sobre onde o critério de UBW é
ambíguo?

**QP2.** Qual abordagem de prompt alcança concordância mais próxima da
observada entre os anotadores humanos?

**QP3.** Como um detector de SATD treinado por outro grupo (IMPACT) classifica
os itens do nosso corpus, e o que a discordância dele com o nosso rótulo diz
sobre a fronteira entre SATD geral e o subtipo UBW?

## 3. Variáveis e métricas

Variáveis independentes: modelo e abordagem de prompt. Variável dependente:
rótulo binário por item. O tipo de artefato deixou de ser variável — o escopo
tem um só. A expressão do léxico permanece como dimensão descritiva do erro, não
como variável de análise (Seção 1).

### 3.1 Por que a acurácia não serve

A prevalência de positivos é alta: 86,5% no conjunto de calibração
multi-artefato, e 94,5% nos comentários de código do conjunto de validação. Um
classificador que respondesse "sim, é UBW" para tudo, sem ler o texto,
acertaria 94,5% e teria κ igual a zero. Nenhuma métrica que some acertos sem
separar as classes distingue uma configuração boa de uma inútil neste regime.
Daí o conjunto abaixo, que sempre reporta a célula pequena separada.

O escopo restrito **agrava** esse problema em vez de aliviá-lo: comentário de
código é o artefato em que o léxico erra menos, então há menos negativos para
detectar e a classe de interesse fica ainda mais escassa.

### 3.2 QP1 e QP2 — concordância com o gabarito humano

- Matriz de confusão 2×2.
- Concordância nas duas direções, com IC de Wilson em cada proporção: dos itens
  que os humanos aceitaram, que fração o painel aceita; dos que rejeitaram, que
  fração o painel rejeita. Wilson e não Wald porque o denominador da segunda é
  de dezenas e a proporção fica perto da borda.
- **Precisão do alerta**, métrica principal para a decisão de publicação: dos
  itens que o painel marcou como prováveis falsos positivos, que fração o
  rótulo humano confirma. É a pergunta que o usuário do dataset faz ao ler a
  coluna. A cobertura é reportada ao lado, porque as duas se opõem — alertar
  mais encontra mais e acerta menos.
- MCC entre o rótulo do modelo e o humano.
- κ de Cohen contra **cada anotador individualmente**, não só contra o voto
  majoritário. A maioria absorve o ruído de um anotador isolado e produz régua
  mais frouxa do que a usada para reportar o acordo entre os humanos, que é par
  a par. As duas versões são reportadas, e a comparação com o acordo humano usa
  a individual.
- κ **penalizando abstenção**: o rótulo `incerto` conta como ausência de alerta
  e o item permanece no denominador. Sem isso, um juiz que se recusa a decidir
  nos casos difíceis aparece como mais concordante do que é — na rodada
  multi-artefato essa correção inverteu o ranking.
- Concordância bruta, prevalência, e AC1 de Gwet apenas como valor numérico, já
  que a escala verbal de Landis e Koch não se aplica a ele (Vach e Gerke, 2023).
- Taxa de positivos de cada juiz, como controle: um modelo que rejeita muito
  destoa da prevalência observada e entrega coluna ruidosa mesmo com κ aceitável.
- Correlação de erro entre juízes (φ par a par) e número de votos efetivamente
  independentes que o painel entrega.
- Caracterização dos itens em que o painel discorda do consenso humano:
  comprimento do corpo, expressão, e sobreposição com os itens não unânimes
  entre os anotadores. Na rodada multi-artefato esse cruzamento foi o achado
  mais forte — o erro dos modelos concentra onde os humanos também divergiram.

### 3.3 QP3 — detector externo

As mesmas métricas da Seção 3.2 aplicadas ao MT-MoE-BERT do IMPACT — com a
ressalva de leitura da Seção 4.2.3, que muda o sentido dos falsos positivos
dele.

## 4. Dados e materiais

### 4.1 Conjuntos

| Papel | Conjunto | Composição | Uso |
|---|---|---|---|
| Desenvolvimento | 57 comentários da calibração, 3 anotadores | 56 positivos / 1 negativo | escolha de prompt, seleção de juízes, regra de agregação |
| Validação | 379 comentários: 110 herdados + 269 novos, 3 anotadores | herdados: 104 / 6, κ 0,847–0,918 | avaliação final, usada uma única vez |
| Aplicação | Comentários de código do corpus | 26.036 registros, 9.584 repositórios, 42 linguagens | recebe a marcação final |

O corpus de aplicação é `data/full_run/ubw_collected_consolidated.csv` restrito
a `artifact_type == "code_comment"`, cobrindo 24 das 25 expressões do léxico
(Seção 1).

A amostra de 269 itens novos foi sorteada em 02/09/2026 por
`scripts/11_sample_code_comment.py --aleatoria-simples`, semente 42, e está em
`validation/sample_code_comment/`. Os 57 comentários da calibração foram
**excluídos do sorteio sem contar para o alvo**: eles já influenciaram a escolha
de prompt e modelo, então incluí-los na validação faria a estimativa herdar
itens que ela deveria avaliar de forma independente.

**O conjunto de desenvolvimento é o ponto fraco deste desenho.** São 57 itens
com **um único negativo**. Isso não sustenta calibração de nada que dependa de
distinguir a classe negativa — inclusive a seleção de juízes por κ, cuja
variância nesse regime é dominada por um item. Duas saídas possíveis, a decidir:
reaproveitar as decisões de método já tomadas na rodada multi-artefato (onde
havia 27 negativos em 200), declarando a transferência; ou ampliar o
desenvolvimento com uma amostra nova de comentários. A primeira é mais barata e
defensável desde que o critério de UBW não tenha mudado com o escopo.

Cada decisão dos anotadores pode vir acompanhada de justificativa curta no campo
de observação. Na rodada multi-artefato, **52 dos 200** itens de calibração
tinham justificativa escrita e apenas **9 dos 385** de validação. Esse é o banco
real de exemplos disponível para a estratégia few-shot; o desenho trabalha
dentro dele, e não sobre a hipótese de que todos estejam justificados.

### 4.2 Juízes candidatos

#### 4.2.1 LLMs

Modelos de famílias distintas, todos com peso aberto, consultados via
OpenRouter com temperatura zero. Preços conferidos em 31/08/2026 pelo
subcomando `verify-judges`, que também confirma a existência de cada slug. O
custo por corpus abaixo projeta 53,0 milhões de tokens de entrada e 6,9 milhões
de saída, medidos com os prompts e as respostas do piloto.

| Família | Slug | Licença | US$/corpus |
|---|---|---|---|
| OpenAI | `openai/gpt-oss-120b` | Apache 2 | 3,13 |
| Mistral | `mistralai/mistral-small-3.2-24b-instruct` | Apache 2 | 5,36 |
| Qwen | `qwen/qwen3-32b` | Apache 2 | 6,17 |
| Google | `google/gemma-3-27b-it` | Gemma | 7,35 |
| DeepSeek | `deepseek/deepseek-v3.2-exp` | MIT | 17,14 |
| DeepSeek | `deepseek/deepseek-chat` (V3) | MIT | 20,72 |
| Qwen | `qwen/qwen3-coder` | Apache 2 | 22,80 |
| Moonshot | `moonshotai/kimi-k2.5` | aberta | 39,38 |
| Meta | `meta-llama/llama-3.3-70b-instruct` | Llama | 42,53 |
| Z.ai | `z-ai/glm-5.2` | MIT | 88,88 |

#### 4.2.1.1 Endpoint fixo por juiz

A OpenRouter roteia cada requisição para o endpoint que julgar melhor no
momento. Num teste de 40 chamadas ao `gpt-oss-120b` saíram **dez provedores
distintos** (AkashML, Groq, DeepInfra, Google, Amazon Bedrock, SiliconFlow,
Together, Parasail, DigitalOcean, CoreWeave), e os vinte endpoints desse modelo
incluem pesos em **bf16, fp4 e quantização não declarada, ao mesmo preço**. Sem
fixar, "o juiz gpt-oss-120b" não é um classificador: é uma mistura de vários,
com pesos numericamente diferentes. Temperatura zero não corrige isso, porque a
variação está no peso e não na amostragem.

Cada juiz passa então a ter um endpoint fixo, escolhido pelo subcomando
`pick-providers` com política declarada — **maior precisão numérica disponível,
desempate por preço** — e chamado com `allow_fallbacks: false`, para que a
fixação não seja silenciosamente desfeita sob carga. A escolha fica versionada
em `validation/panel/providers.csv` e o provedor efetivo é gravado por item no
JSONL, de modo que a violação da premissa seria detectável na auditoria.

O custo dessa decisão é disponibilidade: sem fallback, um provedor ocupado
devolve HTTP 429 e a chamada falha em vez de migrar. Isso já foi observado com o
AkashML. O prejuízo é tempo, não dado, porque a retomada reprocessa registros
com `ok: False`.

Efeito colateral favorável: o preço de tabela do catálogo `/models` é o pior
caso, não o efetivo. Fixar o melhor endpoint derrubou a projeção do Llama 3.3
70B no corpus de US$ 47,79 para **US$ 10,90** e a do GLM-5.2 de US$ 148,56 para
**US$ 52,29**.

#### 4.2.1.2 Esforço de raciocínio

Seis dos dez candidatos emitem tokens de raciocínio, e eles dominam o custo: no
`gpt-oss-120b`, 216 dos 264 tokens de saída (82%) foram raciocínio, e a saída
custa cerca de 4,6 vezes a entrada por token. Medido sobre 12 itens do
desenvolvimento, com endpoint fixo:

| `reasoning.effort` | saída/item | raciocínio | concordância com o humano | abstenções |
|---|---|---|---|---|
| `high` | 488 | 489 | 88% | 1 |
| `medium` (default) | 218 | 177 | 92% | 1 |
| `low` | 114 | 56 | 92% | 0 |

O `high` é dominado: custa quatro vezes mais que o `low` e concorda menos. Ele
sai da varredura. O `low` reduz a saída em 48% contra o default sem perda de
concordância na amostra medida, o que corta de 17% a 32% do custo de corpus dos
modelos que raciocinam.

O esforço é **parâmetro de configuração do juiz**, medido na eliminatória e
congelado no `panel_id` junto com o prompt — não otimização aplicada em
silêncio. A amostra de 12 itens justifica varrê-lo, não decidi-lo: a decisão sai
dos 200.

Duas notas de catálogo. O `mistralai/ministral-8b` não existe na OpenRouter (só
a variante datada `ministral-8b-2512`) e o Ministral 8B é distribuído sob
licença de pesquisa, não Apache; o slot da Mistral com peso aberto de uso livre
é o Small 3.2 24B. E o Llama 3.3 70B subiu de US$ 8 para US$ 42 por corpus
entre 19 e 31 de agosto de 2026, o que o tira da faixa competitiva sem que nada
tenha mudado no modelo — evidência de que o preço precisa ser reconferido na
data da execução, e não copiado deste documento.

A eliminatória custa cerca de **US$ 4,60** com tokens medidos: US$ 2,90 na fase
base (10 slugs × 4 estratégias × 200 itens, no esforço default do provedor) e
US$ 1,70 na varredura de esforço (os 6 modelos que raciocinam × 4 estratégias,
em `low`). Nesse patamar não faz sentido restringir a lista antes de medir. O
teto de custo só passa a valer como critério de desempate na Etapa 5, entre
juízes de desempenho equivalente.

Sobre o tamanho da saída: o piloto assumia 75 tokens por item, número válido
para modelos que não raciocinam. Os que raciocinam gastam de 114 a 488 conforme
o esforço, e é isso que domina o custo de corpus. Duas alavancas foram testadas
e descartadas: truncar o corpo do artefato (a mediana é de 275 caracteres, e
cortar de 2.000 para 500 economizaria 51 tokens ao custo de mutilar 24% dos
itens) e a variante `:batch` (existe só para o `gpt-oss-120b`, e é mais cara que
o endpoint normal). O cache de prefixo tem desconto relevante apenas nos modelos
caros — `qwen3-coder` −89%, `kimi` −84%, `glm-5.2` −81% — e favorece o few-shot
fixo, cujo bloco de ~1.430 tokens se repete item a item, contra o recuperado,
que troca os exemplos e nunca reaproveita cache.

#### 4.2.2 Baselines clássicos

TF-IDF com regressão logística e TF-IDF com XGBoost, treinados no conjunto de
desenvolvimento e avaliados no de teste. Entram como referência de comparação,
não como candidatos ao painel, e o reporte declara a limitação: 27 exemplos
negativos para treino é pouco, a validação é cruzada estratificada e repetida
dentro dos 200, e o IC das métricas resultantes é largo por construção.

#### 4.2.3 Detector externo (IMPACT)

MT-MoE-BERT do IMPACT (Li et al., TOSEM 2026), aplicado sem ajuste, na
configuração publicada. Por ser modelo de codificação e não de geração, roda em
CPU sem custo de API. O DebtHunter (Sala et al., EASE 2021) fica como segundo
detector externo opcional, pelo mesmo raciocínio.

**A leitura do voto dele é assimétrica, e isso não é detalhe.** O IMPACT detecta
SATD em geral; UBW é um subtipo de SATD. Quando ele diz "não é SATD", falha uma
condição necessária de UBW e isso é evidência forte de falso positivo do
léxico. Quando ele diz "é SATD", a evidência a favor de UBW é fraca, porque
todo SATD que não seja UBW cai nessa resposta. Consequência prática: a matriz
de confusão dele contra o gabarito UBW tem falsos positivos que são artefato da
diferença de definição, não erro de classificação, e reportá-la como se fosse
comparável cabeça a cabeça com os LLMs seria enganoso. Ele entra como flag
própria na saída e como variável do agregador, nunca como voto contado na
maioria.

Vale como a principal proteção contra o risco de os LLMs errarem juntos por
viés de treino comum, por ter sido treinado por outro grupo, com outros dados e
outra arquitetura.

### 4.3 Abordagens de prompt

Quatro variantes. As três últimas são construídas sobre o mesmo prompt v1 já
validado em `03_metrics_llm_triage.py`, importado e não copiado, de modo que
qualquer ajuste no texto canônico vale para todas. Os exemplos são injetados
numa âncora textual imediatamente antes do candidato, o que garante a ordem
instrução → exemplos → item.

1. **zero-shot sem definição** (202 tokens/item) — os nomes dos três rótulos, os
   campos do candidato e o formato de saída. Nenhuma definição de UBW, nem no
   system prompt nem anexada aos rótulos. Mede quanto o modelo resolve com o
   conhecimento que já traz.
2. **zero-shot com definição** (644 tokens/item) — o prompt v1 atual, linha de
   base do projeto. O contraste com a variante 1 isola o valor da definição
   ancorada na literatura.
3. **few-shot com exemplos fixos** (1.631 tokens/item, k = 6) — a definição mais
   um conjunto fixo de exemplos, sorteado uma única vez do desenvolvimento com
   3 positivos e 3 negativos, todos com justificativa humana.
4. **few-shot com exemplos recuperados** (878 a 1.240 tokens/item, k = 2, 3 ou
   5) — a definição mais os k exemplos mais parecidos com o item a classificar,
   por similaridade de cosseno sobre TF-IDF. Mesmo desenho da etapa de
   classificação do IMPACT.

A variante 1 mantém o campo `category_ubw` de propósito, apesar de ele ser
sinal a favor do positivo (Seção 4.3.2). Removê-lo aqui mudaria duas coisas ao
mesmo tempo e impediria atribuir ao texto da definição qualquer diferença de
desempenho contra a variante 2.

As justificativas humanas entram nas variantes 3 e 4 como conteúdo de exemplo,
extraídas do pool de 52 descrito na Seção 4.1. Elas **nunca** entram como
variável de entrada do item classificado: os itens não rotulados do corpus não
as possuem, e um classificador que dependesse delas funcionaria no
desenvolvimento e falharia na aplicação.

Quando o item avaliado pertence ao próprio pool de exemplos, ele é removido dos
candidatos antes da seleção (leave-one-out). Sem isso a medida de few-shot no
desenvolvimento seria otimista por construção.

#### 4.3.1 Correção da recuperação por similaridade

A recuperação por similaridade pura degenera neste corpus, e a medição sobre os
200 itens de desenvolvimento com k = 3 mostrou o tamanho do problema: em 33% dos
casos os três exemplos eram da **mesma expressão** do item a julgar, em 70% eram
**todos positivos**, e em 50% **nenhum** trazia justificativa humana. Um item com
"temp fix" recuperava três mensagens de commit "temp fix", todas positivas e
todas sem justificativa. Isso ensina "esta expressão é sempre sim" em vez do
critério, e reforça o desbalanceamento de classe que o resto do desenho tenta
neutralizar.

Duas correções, ambas internas ao desenho de recuperação por similaridade:

- **Cota de classe.** Pelo menos um positivo e um negativo entre os k, quando
  k ≥ 2. As vagas restantes vão para os mais parecidos, sem restrição.
- **Bônus por justificativa.** A similaridade de um exemplar que tenha
  justificativa humana escrita é multiplicada por 1,25. É bônus e não filtro:
  apenas 24% do pool tem justificativa, e priorizá-las estritamente descartaria
  a similaridade, que é o ponto da estratégia.

Efeito medido, com k = 3: exemplos todos positivos cai de 70% para **0%**,
itens sem nenhuma justificativa entre os exemplos cai de 50% para **10%**, e a
fração de exemplos com justificativa sobe de 24% para **51%**. A concentração na
mesma expressão cai de 33% para 28% — ainda alta, mas já não é sinônimo de
"todos da mesma classe".

#### 4.3.2 Duas limitações conhecidas do prompt canônico

**O v1 vaza sinal a favor do positivo.** O template injeta o campo `Categoria
léxica atribuída automaticamente`, que é produto da própria categorização
lexical que estamos auditando, e funciona como pista de que "o sistema já achou
que é UBW". Um braço de ablação sem esse campo é a forma de medir o tamanho do
viés; enquanto não for medido, ele é declarado como ameaça de construto.

**Os exemplos few-shot nunca mostram o rótulo `incerto`.** O pool humano é
binário, então as variantes 3 e 4 suprimem a abstenção por construção. A taxa de
abstenção, portanto, **não é comparável** entre as variantes zero-shot e as
few-shot, e o reporte precisa dizer isso em vez de tabelar os quatro valores
lado a lado.

#### 4.3.3 O prompt v2 e o que ele revelou

Uma quinta variante foi testada em 11/08/2026 e reprovada: o v2, que transforma
as cinco condições da definição operacional do `ANNOTATION_GUIDELINE.md` em
checklist explícito com exemplos negativos. Medido nos 200 itens contra o mesmo
gabarito, obteve κ de **0,004** (DeepSeek V3.2) e **0,027** (Qwen3 Coder),
rejeitando cerca de 85% do que os anotadores humanos aceitam.

O diagnóstico importa mais que o descarte. As justificativas geradas pelo v2 são
internamente corretas — os modelos aplicam a condição 2 ("não basta admitir que
é ruim, precisa haver resignação em manter") ao pé da letra e rejeitam
"temporary fix for X" seco. Só que 88% dos itens com "temporary fix" na
calibração foram aceitos pelos humanos. **O critério escrito no guideline é mais
estrito do que o critério que os anotadores de fato praticam.** É um achado de
validade de construto sobre o nosso instrumento de anotação, não um defeito de
prompt, e entra no artigo como tal.

Consequência para este experimento: o v1 permanece o canônico, e sua fraqueza
conhecida é o recall na classe negativa (captura cerca de 44% dos negativos),
não a concordância geral.

### 4.4 Infraestrutura

A máquina local (12 núcleos, 31 GB de RAM, sem GPU) executa os juízes baseados
em encoder e todas as análises. Rodar LLMs generativos nela foi testado com o
qwen3:4b via ollama e descartado: sem GPU a latência é de minutos por item, o
que projeta meses para o corpus. Há acesso ao IBM Power9 como alternativa. As
chamadas de API usam o pipeline existente, incremental, retomável e
paralelizado.

## 5. Procedimento

### Etapa 1 — Eliminatória no desenvolvimento

Rodar a matriz de modelos × estratégias e medir, por juiz, as métricas da Seção
3.2. Responde a QP2.

**Executada em 01/09/2026 sobre os 200 itens multi-artefato**, antes da revisão
de escopo: 10 modelos × 4 estratégias, 40 combinações completas. Resultados em
`validation/panel/analysis/`. Com o escopo restrito a comentários, o
desenvolvimento disponível cai para 57 itens com 1 negativo (Seção 4.1), o que
não permite repetir a eliminatória no novo escopo. A decisão pendente é entre
transferir as escolhas de método já feitas ou ampliar o desenvolvimento.

**Corte de entrada no painel: κ ≥ 0,75 contra o gabarito humano.** A barra é
deliberadamente alta, na faixa dos κ observados entre os anotadores humanos.

**Fallback, pré-registrado aqui e não depois de ver os resultados.** Se nenhum
juiz atingir 0,75, o painel é formado pelos três melhores acima de κ = 0,40
(limiar de "concordância moderada" de Landis e Koch, abaixo do qual o voto
adiciona mais ruído que sinal), e todo o reporte declara explicitamente que o
painel opera **abaixo da barra pretendida**, com a interpretação das colunas
publicadas ajustada de acordo. Se nem três juízes atingirem 0,40, o experimento
é reportado como resultado negativo e nenhuma coluna é publicada.

O fallback existe porque κ é dominado pela célula pequena neste regime: com 27
negativos em 200, três ou quatro discordâncias concentradas nos negativos
derrubam κ de 0,8 para 0,5 sem que o desempenho geral mude muito. É plausível
que nenhum LLM sem calibração alcance o que anotadores humanos treinados
alcançaram após uma rodada de discussão.

Não é conjectura: os dois únicos juízes já medidos contra este gabarito, ambos
com o prompt v1 em zero-shot, ficaram em κ = **0,408** (DeepSeek V3.2) e
**0,611** (Qwen3 Coder). Nenhum dos dois passa de 0,75. A barra continua onde
está — a comparação com os anotadores humanos é o ponto —, mas o cenário de
acionamento do fallback deve ser tratado como o mais provável, e não como
exceção.

### Etapa 2 — Diagnóstico de correlação e regra de agregação

Medir a concordância juiz-juiz e, a partir dos erros cometidos em conjunto,
quantos votos efetivamente independentes o painel entrega. O passo existe
porque juízes LLM tendem a errar nos mesmos itens: Kohli (2026) mostrou um
painel de nove juízes de sete famílias entregando o equivalente a 2,2 votos
independentes, sem que nenhum esquema de ponderação, Dawid-Skene incluído,
recuperasse a independência perdida.

Teto de cinco juízes no painel final: Kohli mostra que cinco capturam cerca de
90% da independência alcançável, e que juízes adicionais acrescentam pouco.
Entre juízes de desempenho equivalente, a preferência é por diversidade de
família; entre juízes de desempenho e família equivalentes, por menor custo.

Escolha da regra, condicionada ao diagnóstico:

| Cenário observado | Regra adotada |
|---|---|
| Confiabilidade parecida, erros pouco correlacionados | maioria simples |
| Confiabilidade desigual | agregador XGBoost sobre os votos, mas só se superar o melhor juiz sozinho na precisão do alerta; caso contrário, melhor juiz sozinho |
| Menos de 2 votos efetivos | melhor juiz sozinho, com o painel reportado como redundante |

A maioria para confiabilidade parecida e a agregação ponderada para
confiabilidade desigual seguem o OLAF (Mia e Zaman, 2025), que também recomenda
reportar concordância humano-modelo separada da concordância modelo-modelo.

O agregador, quando houver, recebe os votos de cada juiz mais metadados
disponíveis em todo o corpus (tipo de artefato, expressão, comprimento do
texto) e a flag do detector externo — cerca de dez variáveis para 200
observações, com validação cruzada interna.

### Etapa 3 — Congelamento

Congelar juízes, versões de modelo, prompt, valor de k, temperatura, regra de
agregação e limiar. O estado congelado vira manifest versionado. A partir daqui
nada é ajustado à luz de resultado novo.

### Etapa 4 — Validação (n = 379, uma única vez)

Rodar o painel congelado mais o MT-MoE-BERT sobre os 385. Responde a QP1,
parcialmente a QP3. Depende da conclusão da anotação dos 269 itens novos
(Seção 4.1).

### Etapa 5 — Análise de erro

Segunda passada sobre os itens em que o painel discorda do consenso humano,
caracterizando-os pelas dimensões da Seção 3.2 e confrontando a justificativa
do modelo com a do anotador. **Não requer chamada nova de API**: todo run já
grava a justificativa do modelo por item, então esta etapa é filtragem e
leitura, não execução.

### Etapa 6 — Aplicação ao corpus (n = 26.036)

Rodar a configuração congelada, mais o MT-MoE-BERT, sobre o corpus completo com
temperatura zero. Produz as colunas publicadas. Custo estimado entre US$ 25 e US$ 45 conforme a composição do
painel, e acima de US$ 150 se `kimi-k2.5` ou `glm-5.2` entrarem nele.

Sobre determinismo: o endpoint de cada juiz é fixo e sem fallback (Seção
4.2.1.1), o que remove a maior fonte de variação — pesos em quantizações
diferentes sob o mesmo nome de modelo. Resta a variação de kernel e de versão de
runtime dentro do próprio provedor, que temperatura zero não elimina. O provedor
efetivo é gravado por item, então a premissa é auditável, e a variação residual é
tratada como ameaça de conclusão.

### Etapa 7 — Auditoria da saída

Amostrar a saída da aplicação e revisar com humanos, para verificar se o
comportamento do painel no corpus corresponde ao observado no teste. A pergunta
é de deriva de distribuição, distinta da que o IMPACT respondia com sua
auditoria de 500 itens (lá, validar rótulos de dado sintético), e por isso o
tamanho não foi copiado: a amostra é dimensionada por Cochran (95% de
confiança, margem de 5%), que estabiliza em 385 para populações deste porte.

### Etapa 8 — Publicação

Duas colunas novas no dataset:

- `n_judges_flagged_fp` — inteiro de 0 a k, quantos juízes do painel rejeitaram
  o item, para que cada usuário escolha o próprio corte.
- `panel_id` — string que identifica a configuração que produziu a contagem:
  versões dos modelos, versão do prompt, k, temperatura, regra de agregação e
  data da execução.

Mais `llm_rationale` (justificativa, para auditoria) e a flag do detector
externo em coluna própria. O descritor declara que a marcação é automática,
parcial e não validada item a item por humanos.

## 6. Critérios de decisão

| Resultado no teste | Decisão |
|---|---|
| Precisão do alerta ≥ 80% | publica a marcação completa, com a cobertura declarada |
| Entre 60% e 80% | publica apenas o subconjunto de maior confiança (ao menos 2 juízes) |
| Abaixo de 60% | não publica; o experimento é reportado como limitação |
| Concordância alta entre juízes com concordância baixa contra o humano | não publica: é indício de viés compartilhado, não de acerto |

## 7. Ameaças à validade

**Conclusão.** O resultado ser fruto do acaso. Mitigado por IC de Wilson em toda
proporção reportada e bootstrap nas quantidades derivadas. O não-determinismo
residual dos LLMs sob temperatura zero, discutido na Etapa 6, entra aqui.

**Construto.** Duas ameaças distintas. A primeira: usamos o rótulo humano como
referência de verdade para medir LLMs, quando o rótulo humano é ele próprio uma
medida com erro — mitigado pelo κ alto entre os três anotadores e pela entrada
de um detector externo ao projeto. A segunda: o IMPACT mede SATD e nós medimos
UBW, então a discordância dele é parcialmente definicional e não pode ser lida
como erro (Seção 4.2.3).

**Interna.** Viés na construção do experimento. Mitigado pelo congelamento de
prompt, modelo, parâmetros e regra de agregação após o desenvolvimento, antes
de qualquer contato com o conjunto de teste ou o corpus; e pelo pré-registro do
fallback de κ na Etapa 1, para que a barra não seja renegociada depois de ver o
resultado. A escassez de negativos (27 no desenvolvimento, 28 no teste)
limita tanto o agregador quanto os baselines clássicos, e é declarada em cada
reporte que dependa deles.

**Externa.** O corpus cobre 21.553 repositórios sem restrição de linguagem, em
três tipos de artefato, o que sustenta generalização dentro do universo de
projetos de código aberto do GitHub. Não se estende a código proprietário nem a
plataformas fora do GitHub. A premissa de sensibilidade e especificidade
constantes entre expressões (Seção 3.3) é a limitação mais forte da
extrapolação por expressão.

## 8. Implementação

O `07_judge_panel.py` monta os conjuntos a partir das anotações (`build-gold`),
confere slugs e preços na OpenRouter (`verify-judges`) e roda um juiz sobre um
conjunto (`run`). Cada combinação de modelo e estratégia grava um arquivo
próprio em `validation/panel/runs/`, uma linha por item, e a execução é
retomável. As estratégias de prompt ficam em `panel_prompts.py`.

O `08_panel_analysis.py` executa o protocolo das Etapas 1 e 2 na ordem em que
foi fixado e escreve o relatório com métricas por juiz, matriz de concordância
juiz-juiz, diagnóstico de correlação de erro, comparação entre regras de
agregação e a regra escolhida com justificativa. O subcomando `apply` aplica uma
regra congelada, que é o que roda no teste e depois no corpus.

As rodadas de julho e agosto de 2026 sobre os 200 itens foram importadas para o
formato do painel (`import-legacy`), então DeepSeek V3.2 e Qwen3 Coder em
zero-shot já entram na Etapa 1 sem repetir chamada paga.

### 8.1 Pendências de implementação

Já feito em 31/08/2026: a estratégia `zero_shot_nodef` (variante 1 da Seção
4.3), a correção da recuperação por similaridade (Seção 4.3.1), a fixação de
endpoint por juiz (subcomando `pick-providers` e `--provider`), o parâmetro
`--reasoning-effort`, e a reescrita de `run_panel_fase1.sh` em duas fases —
base e varredura de esforço, com a lista de modelos que raciocinam derivada dos
`reasoning_tokens` observados na fase base em vez de assumida.

Três defeitos de execução corrigidos no mesmo dia, todos encontrados pelo teste
de fumaça e nenhum visível sem ele:

- `_load_done` contava item com `ok: False` como concluído, o que transformava
  falha de rede, rate limit ou 402 em rótulo `incerto` permanente que a retomada
  nunca revisitaria.
- `max_tokens` era 300 e é orçamento total: nos modelos que raciocinam o corte
  caía antes de o JSON começar ou no meio dele, e as duas falhas viravam
  abstenção fabricada. Passou para 1.000.
- Condição de corrida na construção do índice TF-IDF com `--workers > 1`,
  resolvida com lock e publicação atômica do par vetorizador/matriz.

Em aberto:

- Métricas da Seção 3.2 ausentes de `08_panel_analysis.py`: MCC, IC de Wilson
  nas duas direções, φ par a par, desagregação por artefato e por expressão.
- Braço de ablação sem `category_ubw`, para medir o vazamento descrito na Seção
  4.3.2.
- Baselines clássicos da Seção 4.2.2 e integração do MT-MoE-BERT não têm
  implementação.
- O corte de κ em `08_panel_analysis.py` está em 0,40 e precisa passar para
  0,75 com o fallback da Etapa 1.

## Referências

Brown, L. D.; Cai, T. T.; DasGupta, A. Interval estimation for a binomial
proportion. Statistical Science 16(2), 2001. — sustenta a escolha de Wilson
sobre Wald.

Chicco, D.; Jurman, G. The advantages of the Matthews correlation coefficient
(MCC) over F1 score and accuracy in binary classification evaluation. BMC
Genomics 21(6), 2020.

Cochran, W. G. Sampling Techniques. 3ª ed. Wiley, 1977. — dimensionamento da
amostra de validação.

Landis, J. R.; Koch, G. G. The measurement of observer agreement for
categorical data. Biometrics 33(1), 1977. — escala de interpretação do kappa.

Matthews, B. W. Comparison of the predicted and observed secondary structure of
T4 phage lysozyme. Biochimica et Biophysica Acta 405(2), 1975.

Mia, M. I.; Zaman, T. S. OLAF: Towards Robust LLM-Based Annotation Framework in
Empirical Software Engineering. arXiv:2512.15979, 2025.

Kohli, G. Nine Judges, Two Effective Votes: Correlated Errors Undermine LLM
Evaluation Panels. arXiv:2605.29800, 2026.

Li, Q. et al. IMPACT: Identifying and Classifying Multiple Sourced and
Categorized Self-Admitted Technical Debts. ACM TOSEM 35(4), 2026.

Sala, I.; Tommasel, A.; Arcelli Fontana, F. DebtHunter: A Machine
Learning-based Approach for Detecting Self-Admitted Technical Debt. EASE 2021.

Vach, W.; Gerke, O. Gwet's AC1 is not a substitute for Cohen's kappa. MethodsX
10, 2023.

Wilson, E. B. Probable inference, the law of succession, and statistical
inference. Journal of the American Statistical Association 22(158), 1927.
