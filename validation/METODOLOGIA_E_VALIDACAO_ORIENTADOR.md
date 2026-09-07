# Preparação e validação do dataset UBW — material para reunião de orientação

> Rascunho de conteúdo (não o layout final — vai pro Claude Design depois).
> Gráficos referenciados estão em `figures/overview_v2/`. Seções marcadas
> `[PLACEHOLDER]` dependem da anotação dos 385 pelos 3 avaliadores, ainda em
> andamento.

## 1. O que é o dataset

UBW ("ugly but works") é um subtipo estreito de SATD (Self-Admitted Technical
Debt): trechos onde o(a) autor(a) do código admite, sobre uma decisão sua
própria e com referência concreta ao código, um trade-off explícito entre
qualidade da solução ("feio", "hack", "workaround", "provisório") e o fato de
ela funcionar / resolver o problema / não ser mexida. Não é uma reflexão
genérica sobre boas práticas, é uma resignação funcional pontual.

Nenhum trabalho da literatura estuda esse subtipo isoladamente com léxico
fechado + multi-artefato + análise de sobrevivência da remoção — é o gap que
o projeto ocupa.

## 2. Pipeline de construção do corpus

1. **Léxico fechado.** 25 expressões literais curadas manualmente (ex.:
   "temporary fix", "quick and dirty", "stopgap", "ugly hack", "dirty
   workaround"), sem correspondência lexical ambígua com jargão técnico
   comum.
2. **Mineração multi-artefato.** `git log -S` (mensagens de commit) +
   varredura de comentário de código + API do GitHub (corpo de PR). Rodada
   paralelizada por repositório, sem rate limit de rede na varredura de
   commit. **Rotação de múltiplos tokens de API** — o limite de 30 req/min
   da Search API do GitHub é por token, não por IP; o coletor aceita uma
   lista de tokens e faz round-robin entre eles a cada chamada, cada um com
   seu próprio estado de rate limit, multiplicando o throughput efetivo por
   `len(tokens)` sem violar o limite individual de nenhum. Essas duas
   frentes (paralelização por repositório + rotação de tokens) são o que
   viabilizou minerar 91 mil ocorrências em escala de tempo de projeto de
   mestrado — sem elas, o gargalo de rede tornaria a coleta impraticável.
3. **Canonicalização.** Deduplicação, remoção de contaminação por arquivo
   gerado/build (achado registrado em rodada anterior, corrigido antes da
   consolidação), filtro de bot.
4. **Amostragem sobre o corpus consolidado (N=91.458, sem `issue_body`).**
   Ver Seção 3 pra mecânica de cada pool.

## 3. Como a amostra foi colhida

Quadro (frame) de amostragem: os 91.458 registros consolidados (fatia A +
fatia B), já sem `issue_body`. Seed fixa = 42, script único
(`03b_final_sampling.py build-v2`), com guarda-corpo deliberado: o comando
recusa gerar amostra com `--label oficial` a menos que o operador digite
literalmente a confirmação de que A+B já foi consolidado — evita gerar
"amostra oficial" por engano em cima de corpus ainda provisório.

Quatro pools, sorteadas do mesmo frame, **mutuamente exclusivas**
(cada item sorteado é removido do pool remanescente antes do próximo sorteio
— não há sobreposição entre pools):

- **`main` (385 itens) — amostra de precisão oficial.** Amostragem
  aleatória simples, sem estratificação por categoria (a categoria A/B/C já
  não é dimensão analítica). Tamanho fixado pela fórmula de Cochran (Seção
  7). É o único pool cujo resultado vira número de precisão do paper.
- **`calibration` (200 itens).** Amostrada à parte do `main`, mesmo
  processo aleatório simples. Serve só pra treinar/alinhar critério entre os
  3 anotadores antes da medição real — nunca entra em métrica.
- **`watch` (106 itens) — sobre-amostragem por raridade de expressão, não
  lista fixa.** Qualquer expressão do léxico com menos de 50 ocorrências no
  corpus inteiro (`--watch-rarity-threshold`) recebe piso mínimo de
  amostragem, pra garantir que expressões raras apareçam na validação em vez
  de sumirem por sorte na amostragem aleatória do `main`. Hoje isso pegou 6
  expressões: "crude but it works", "hope everything will work", "horrible
  but works", "messy but works", "not elegant but works", "terrible but
  works". Diagnóstico — mede cobertura do léxico, não precisão.
- **`near_miss` (100 itens) — near-miss adversarial.** Extraído por
  heurísticas mecânicas a partir dos exemplos NEGATIVOS listados no
  `ANNOTATION_GUIDELINE.md` (string de teste/fixture, citação de terceiro,
  negação, remoção/undo, diretiva de tooling/arquivo gerado, uso
  não-técnico da expressão). Testa se o léxico erra pro lado do falso
  positivo em casos que *parecem* UBW mas não são — mede especificidade, não
  entra na precisão oficial.

**Reponderação.** Como `watch` e `near_miss` são sobre-amostrados de
propósito (não são representativos da proporção real no corpus), pesos por
estrato ficam salvos à parte (`sampling_weights_oficial.csv`) pra que a
precisão global reportada não fique enviesada por essa sobre-amostragem —
só o pool `main` entra no cálculo de precisão sem peso nenhum, os outros são
puramente diagnósticos.

**Correção de população finita.** Aplicada automaticamente se o frame
tivesse menos de 5.000 itens (não é o caso aqui — 91.458 já está na faixa
onde o N necessário estabiliza, ver Seção 7).

### 3.1 A amostra reproduz as proporções do corpus? (sim — verificado)

Pergunta levantada na orientação: a planilha de calibração tem PR, commit,
comentário de código e expressões variadas — essas proporções batem com as do
corpus inteiro, ou o subconjunto ficou enviesado?

**Tipo de artefato: bate por desenho.** A amostragem é estratificada por
`(category_ubw, artifact_type)` com alocação proporcional ao tamanho de cada
estrato (`stratified_sample`, `scripts/03_metrics_llm_triage.py`). Não é
sorte — é imposto pelo procedimento:

| Tipo de artefato | Corpus (91.458) | Calibração (200) | Amostra main (385) |
|---|---|---|---|
| Mensagem de commit | 47,4% | 47,5% (95) | 47,3% (182) |
| Comentário de código | 28,5% | 28,5% (57) | 28,6% (110) |
| Corpo de PR | 24,1% | 24,0% (48) | 24,2% (93) |

**Expressão do léxico: não é estratificada, mas aderiu.** A expressão não
entra como variável de estratificação — as proporções vêm por consequência do
sorteio dentro de cada estrato. Ainda assim, o teste de aderência
(qui-quadrado de bondade de ajuste contra as proporções do corpus, estratos
com frequência esperada ≥ 5) não rejeita a hipótese de mesma distribuição:

| Amostra | Variável | χ² | gl | p | Conclusão |
|---|---|---|---|---|---|
| Calibração (200) | tipo de artefato | 0,00 | 2 | 0,999 | aderente |
| Main (385) | tipo de artefato | 0,00 | 2 | 0,999 | aderente |
| Calibração (200) | expressão | 5,50 | 6 | 0,481 | aderente |
| Main (385) | expressão | 11,58 | 8 | 0,171 | aderente |

Os desvios visíveis item a item (ex.: "this is a hack" com 10,0% no corpus,
7,0% na calibração e 13,0% na main) estão dentro da variação amostral
esperada para esses tamanhos — nenhum é estatisticamente significativo.

Ou seja: a amostra é representativa do corpus tanto em artefato (por
construção) quanto em expressão (verificado a posteriori).

## 4. Caracterização do corpus (N = 91.458)

Recorte usado nestes gráficos: **exclui `issue_body`** (24.734 registros,
21,3% do bruto de 116.192) — issue fica mais distante do código em si que
comentário/commit/PR, fora do escopo de proximidade que o projeto quer medir.
Categorias A/B/C do léxico também não aparecem mais aqui — deixaram de ser
dimensão analítica (decisão de reunião, 2026-07-29); todo o corpus é tratado
como uma coisa só, `is_ubw` binário.

- **Figura 1** (`01_artefato.png`) — distribuição por tipo de artefato:
  mensagem de commit 47,4% (43.351), comentário de código 28,5% (26.036),
  corpo de PR 24,1% (22.071).
- **Figura 2** (`02_linguagem.png`) — top 15 de 44 linguagens principais dos
  repositórios. C++ (18,7%) e Python (17,9%) lideram, seguidos de TypeScript
  (12,0%).
- **Figura 3** (`03_expressoes.png`) — ranking completo das 25 expressões do
  léxico por número de ocorrências. "temporary fix" domina (28,1% do
  corpus sozinha); expressões da categoria de resignação explícita ("ugly
  but it works", "hacky but works") são as mais raras.
- **Figura 4** (`04_artefato_x_linguagem.png`) — composição de artefato por
  linguagem (top 10). Rust e C# se destacam por terem quase nenhum
  comentário de código capturado (7-9%) e predominância de PR/commit —
  hipótese: convenção de comunidade nesses ecossistemas usa menos comentário
  inline pra esse tipo de admissão.
- **Figura 5** (`05_top_repos.png`) — repositórios com mais ocorrências
  (top 15 de 21.553 com pelo menos 1 ocorrência).

## 5. Protocolo de validação humana

Três anotadores (Wendell, Bruno, Miguel), três fases:

1. **Calibração (200 itens, iguais pros 3).** Anotação independente, depois
   discussão em grupo pra alinhar critério. Nunca entra na métrica oficial.
   κ pós-discussão: Wendell×Bruno 0,80, Wendell×Miguel 0,82, Bruno×Miguel
   0,85 (Cohen's Kappa; concordância bruta 87-89% já era alta antes da
   discussão — divergência inicial de κ é o paradoxo de prevalência
   clássico, AC1 de Gwet nos mesmos dados já dava 0,84-0,85).
2. **Medição + paralelização, redundância total (385 itens, os MESMOS pros
   3, sem fatiar).** Decisão de 2026-08-11: abandonado o desenho anterior de
   "1 anotador por item na paralelização" — agora os 3 anotam os 385
   inteiros, de forma independente, sem discussão. Composição por artefato:
   182 commit / 110 code_comment / 93 PR.
3. **Diagnóstico (fora da métrica oficial).** `watch` (106) e `near_miss`
   (100) — medem especificidade do léxico contra casos parecidos mas não
   confirmados, não entram no cálculo de precisão nem de κ.

**Ferramenta.** Viewer HTML standalone por anotador, com atalho de teclado
(Q/W = sim/não, 1/2/3 = certain/likely/uncertain), destaque do trecho
casado no texto, progresso salvo automaticamente, export CSV com fallback
garantido.

## 6. Fundamentação das escolhas de validação na literatura

Levantamento feito em 2026-08-11 pra ancorar duas decisões que o orientador
pode questionar: (a) usar κ de Cohen como métrica principal, (b) reportar AC1
de Gwet junto por causa do desbalanceamento.

### 6.1 O que os trabalhos de SATD fazem — κ de Cohen é o padrão do campo

| Trabalho | Tipo | Anotadores | Amostra anotada | Métrica | Valor |
|---|---|---|---|---|---|
| Pham, Sridharan, Esposito & Lenarduzzi (2025) — **CppSATD** | *Dataset descriptor* (IEEE Data) | 2 | **385** SATD + 385 não-SATD | κ de Cohen | 0,86 / 1,0 |
| Melin, Eisty, Watson & Malviya-Thakur (2025) — SATD multi-artefato em software científico | Empírico multi-artefato | 2 | 200 (50 por artefato) | κ de Cohen | 0,926 geral |
| Unterbusch, Sadeghi, Fischbach, Obaidi & Vogelsang (2023) — necessidades de explicação em reviews | Empírico (RE/SE) | 4 | 485 duplo-codificados | κ + **AC1** | κ=0,495 · AC1=0,945 |

Três leituras diretas pro nosso caso:

1. **N=385 tem precedente literal em paper de dataset SATD.** O CppSATD —
   que é exatamente o tipo de publicação que miramos (descritor de dataset,
   trilha Data/Tool) — validou com **385 itens**, o mesmo número que
   chegamos independentemente por Cochran. Argumento pronto pra dúvida do
   orientador sobre o tamanho da amostra.
2. **Nosso protocolo está acima do padrão do campo em número de
   anotadores.** Os dois trabalhos de SATD acima usaram **2** anotadores; nós
   usamos **3**, com fase de calibração e discussão registrada. Nenhum dos
   dois faz redundância total sobre a amostra inteira como passamos a fazer.
3. **κ por tipo de artefato é prática estabelecida, e PR é de fato o artefato
   mais difícil.** Melin et al. reportam κ separado por fonte, e o menor
   valor deles é justamente o de pull request (0,843, contra 0,95+ em
   comentário/commit/issue). Reforça a decisão de quebrar nossos resultados
   por artefato — e antecipa que o κ de PR deve vir mais baixo, sem que isso
   signifique falha de protocolo.

Faixa de referência do campo (κ em estudos recentes de SATD): 0,73–0,96.
Nossos valores pós-calibração (0,80 / 0,82 / 0,85) caem confortavelmente
dentro dela.

### 6.2 Por que reportar AC1 junto — e a ressalva que precisa entrar no texto

O caso de Unterbusch et al. (2023) é o precedente mais próximo do que
vivemos: **95,05% de concordância bruta, mas κ = 0,495** — porque a classe
positiva era rara (~5% dos itens). Os autores reportam AC1 = 0,945 e
justificam com o *paradoxo do kappa*: com prevalência muito desbalanceada, κ
sai baixo mesmo com concordância altíssima, e deixa de ser informativo.
É a mesma forma numérica do nosso caso (87–89% bruta, κ inicial 0,47–0,60,
AC1 0,84–0,85) — ou seja, não é anomalia nossa, é comportamento conhecido e
já publicado em SE.

**Ressalva importante (Vach & Gerke, 2023, *MethodsX* 10:102212).** Há
crítica formal ao uso de AC1 como substituto do κ. Os autores mostram que os
dois medem coisas estruturalmente diferentes (κ usa concordância esperada,
AC1 usa discordância esperada; AC1 sobe conforme a prevalência se afasta de
0,5, κ desce; AC1 pode dar valor diferente de zero mesmo sem associação
nenhuma entre anotadores). A conclusão prática que nos afeta diretamente:

> **a escala verbal de Landis & Koch não deve ser aplicada a valores de
> AC1.**

Consequência concreta pro nosso material: podemos reportar AC1 = 0,84, mas
**não** devemos chamá-lo de "excelente" ou "quase perfeito" — esses rótulos
só valem pra κ. Já verificamos o código: `03_metrics_llm_triage.py` aplica
`interpret_kappa()` somente ao κ e reporta AC1 como número puro, então a
implementação está correta; o ajuste é só de redação nos textos que
descrevem os resultados.

**Forma de reportar que fica defensável** (segue Wongpakaran et al. 2013 e
acomoda a crítica de Vach & Gerke): sempre a tétrade **concordância bruta
(%) + prevalência das classes + κ (com rótulo Landis-Koch) + AC1 (número,
sem rótulo)**, nunca κ sozinho nem AC1 sozinho. Regra de interpretação já
registrada no projeto: κ baixo + AC1 alto + bruta alta ⇒ paradoxo de
prevalência, anotação aceitável com justificativa explícita; κ e AC1 ambos
baixos ⇒ problema real de guideline/construto.

### 6.3 Referências metodológicas de base

- **Landis & Koch (1977)** — origem da escala verbal de κ (0,61–0,80
  substancial; > 0,80 quase perfeita). Aplicável só a κ.
- **Gwet (2008)** — formulação do AC1.
- **Wongpakaran, Wongpakaran, Wedding & Gwet (2013)**, *BMC Med Res
  Methodol* — comparação empírica κ × AC1; mostra que AC1 permanece próximo
  da concordância bruta quando a prevalência varia, enquanto κ oscila.
- **Vach & Gerke (2023)**, *MethodsX* 10:102212 — a crítica; base da
  ressalva da Seção 6.2.

## 7. Por que N=385 é estatisticamente válido [já fechado com o orientador]

Fórmula de Cochran + correção de população finita: a partir de ~50 mil de
população, o N necessário estabiliza em 383-384 até 100 milhões — o tamanho
da população deixa de ser a variável relevante. O que move N é a margem de
erro aceita: ±5% → 383, ±3% → 1.055, ±2% → 2.340 (95% de confiança).
Precedentes: Bavota & Russo 2016 (pop=7.584, n=366), Pham et al. 2025
(pop=13-16k, n=374-376) — mesmo platô com população bem menor que a nossa.

## 8. Resultados de precisão

Rótulo final por item = maioria dos 3 votos (nunca empata com N ímpar).

### 8.1 Concordância entre anotadores

| Par | κ de Cohen | Interpretação |
|---|---|---|
| Wendell × Bruno | 0,925 | excelente |
| Wendell × Miguel | 0,872 | excelente |
| Bruno × Miguel | 0,844 | excelente |

### 8.2 Precisão

| Recorte | N | TP (is_ubw=True) | Precisão | IC 95% | Margem |
|---|---|---|---|---|---|
| Amostra oficial (385, todos os artefatos) | 385 | 357 | **92,7%** | 90,1%–95,3% | ±2,6pp |
| Comentário de código | 110 | 104 | 94,5% | 90,3%–98,8% | ±4,2pp |
| Mensagem de commit | 182 | 169 | 92,9% | 89,1%–96,6% | ±3,7pp |
| Corpo de PR | 93 | 84 | 90,3% | 84,3%–96,3% | ±6,0pp |

**Nota pro orientador:** a margem ±2,6pp geral já é melhor que os ±5%
dimensionados por Cochran — a prevalência alta (92% True) reduz a variância.
Quebras por artefato têm n menor (93 a 182), então margem maior — reportadas
já com o IC próprio de cada fatia, não com o do agregado.

**Nota conceitual:** como UBW é subtipo definicional de SATD (Seção 1), todo
item confirmado `is_ubw=True` também é, por construção, uma instância de
SATD — mas a precisão medida aqui é a do *minerador de UBW*, não de um
detector de SATD genérico (o léxico não cobre requirement/test/doc debt sem
a moldura "feio mas funciona").

### 8.3 Onde isso posiciona o resultado na literatura

Levantamento de concordância inter-anotador reportada em papers de dataset
de SATD, para contextualizar nosso κ (2026-08-19):

| Paper | N manual | Anotadores | κ |
|---|---|---|---|
| Potdar & Shihab (2014) — seminal do campo | 101.762 | 1 | — (nenhuma) |
| Maldonado & Shihab (2015) | 33.093 | 1 | — (nenhuma) |
| Maipradit et al. (2019/2021) — On-Hold SATD | 335 | 2 (de 3) | 0,541–0,821 |
| PENTACET (Sridharan et al. 2023) | 388 | 2 | 0,75 |
| SATDAUG (Sutoyo & Capiluppi 2024) | — | 3 | 0,74 |
| Aging Debt (Sridharan et al. 2025) | 2.562 | 2 | 0,695 |
| CppSATD (Pham et al. 2025) | 385+385 | 2 | 0,86 / 1,0 |
| Melin et al. (2025) | 200 | 2 | 0,926 geral (0,843 pior fonte) |
| **UBW (este trabalho)** | **385** | **3** | **0,844–0,925** |

Nota: os dois papers fundacionais do campo (Potdar & Shihab 2014, Maldonado
& Shihab 2015) não reportam concordância inter-anotador — a classificação
foi feita por um único pesquisador em ambos.

Dois outros trabalhos (Rantala et al. 2024 e PENTACET) também chegam a
N=385, mas por coincidência de fórmula — mesma conta padrão de amostragem
(p=0,5, IC 95%, margem 5%) que qualquer calculadora de tamanho amostral
devolve, não convergência metodológica real com este desenho.

## 9. Trilho B — a ideia (exploratória)

Além da validação humana, existe uma segunda camada em desenvolvimento:
passar um **ensemble de LLMs** por todo o corpus (91.458 itens), não só pela
amostra, para produzir uma leitura descritiva em escala.

**A ideia em uma frase:** dois ou mais modelos classificam cada ocorrência de
forma independente; onde concordam, o rótulo é aceito como sinal
exploratório; onde divergem ou hesitam, o item fica marcado como
indeterminado. O custo de rodar o corpus inteiro é da ordem de **$36 a $48**.

<details><summary>De onde vem esse custo</summary>

Não é estimativa de catálogo — os tamanhos foram medidos no próprio corpus e
na saída real do piloto:

- **Entrada:** 2.314 caracteres por chamada em média (média de 3.000 itens
  sorteados, com o prompt já montado). Desses, **1.818 são o template fixo do
  prompt — 79% da entrada.** O texto do artefato em si é só 452 caracteres em
  média (truncado em 2.000).
- **Saída:** 298 caracteres em média, medidos nas 400 respostas reais do
  piloto (200 itens × 2 modelos), não estimados.
- **Preços por 1M tokens (OpenRouter):** DeepSeek V3.2 $0,21 entrada /
  $0,32 saída; Qwen3 Coder $0,30 / $1,00.

| Conversão caractere→token | DeepSeek | Qwen3 Coder | Ensemble |
|---|---|---|---|
| 4,0 chars/token (medido) | $13,29 | $22,69 | **$35,98** |
| 3,5 chars/token (conservador) | $15,19 | $25,93 | **$41,12** |
| 3,0 chars/token (pessimista) | $17,72 | $30,25 | **$47,97** |

A única incerteza real é a razão caractere/token, que varia com o tokenizador
de cada modelo — daí a faixa em vez de um número único. Conferência contra o
piloto: para 200 itens o modelo prevê $0,079 e o gasto observado ficou em
~$0,05, ou seja, a estimativa erra para cima.

**Otimização óbvia, ainda não aplicada:** como 79% da entrada é template fixo
repetido 183 mil vezes (91.458 × 2 modelos = 83M tokens só de boilerplate),
cache de prompt reduziria a conta de forma relevante. Vale verificar suporte
no OpenRouter antes de rodar em escala.

</details>

**O que isso é e o que não é.** O Trilho B é uma camada **descritiva** —
serve para olhar padrões que a amostra de 385 não alcança (por linguagem, por
expressão rara, por repositório). O número de precisão do artigo continua
vindo do Trilho A, da anotação humana. O LLM não gera rótulo de dataset e não
substitui anotador.

**Estado atual: implementado, paralelizado e já medido contra gabarito
humano.** O piloto rodou os 200 itens de calibração — que têm rótulo dos 3
anotadores — com DeepSeek V3.2 e Qwen3 Coder, `temperature=0`:

| | Concordância com humano (κ) | Acurácia | Acha os positivos | Acha os negativos |
|---|---|---|---|---|
| Qwen3 Coder | 0,611 | 94,5% | 100% | 46,7% |
| DeepSeek V3.2 | 0,408 | 89,4% | 94,8% | 43,8% |
| Só onde os dois concordam (126 de 200) | 0,529 | **96,0%** | 100% | 37,5% |

Leitura: nos ~63% dos itens em que os dois modelos concordam, eles acertam
96% das vezes. O acerto vem quase todo dos positivos — a camada automática
**encontra bem o que é UBW e é fraca em identificar o que não é** (acha menos
da metade dos negativos). Serve para descrever o corpus em escala; não serve
como juiz de precisão, que é exatamente o papel reservado ao Trilho A.

A literatura de SATD apoia esse uso: LLM sem *fine-tuning* tem desempenho
competitivo em identificação binária — a nossa tarefa — e falha em
classificação multi-categoria, que abandonamos. Fundamentação, plano de
execução, experimentos de prompt e riscos metodológicos em
`validation/ANEXO_TRILHO_B_LLM.md`.

## 10. Pendências

**Precisa de decisão nesta reunião**

- **"temporary fix" seco conta como UBW?** 61,9% do corpus (56.623 itens) é
  disparado por marcador puramente temporal (`temporary fix`, `temp fix`,
  `stopgap`, `workaround for now`, `band-aid fix`), sem nenhum juízo sobre a
  qualidade da solução. Na calibração os 3 anotadores trataram esses casos
  como equivalentes aos com juízo estético (86% vs 87% True). Três saídas:
  aceitar (e ajustar o texto do guideline), rejeitar (e podar o léxico), ou
  **reportar as duas fatias separadamente** — que é a recomendação, sai de
  graça do léxico e vira uma dimensão de análise. Detalhe no anexo do
  Trilho B. **A decisão precisa sair antes de a anotação dos 385 começar**,
  senão o trabalho dos três é refeito.

**Em execução**

- Anotação dos 385 pelos 3 avaliadores — ferramenta pronta e publicada,
  ainda não iniciada.
- Preencher a Seção 8 (precisão + κ/AC1) quando a anotação fechar.
- Recalcular a margem de erro das quebras por artefato (n = 93 a 182), que é
  maior que os ±5% do agregado.

**Ajuste de redação**

- Revisar os textos do projeto que chamam AC1 de "excelente"/"quase
  perfeito" — o rótulo de Landis-Koch não se aplica a AC1 (Vach & Gerke,
  2023; Seção 6.2). Reportar AC1 como número puro. O código já está correto.
