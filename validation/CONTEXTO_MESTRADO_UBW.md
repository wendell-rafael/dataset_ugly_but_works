# Contexto do mestrado UBW

Documento de contexto para iniciar uma conversa nova. Reúne o que o projeto é,
onde ele está e quais números são oficiais. Estado em 19/08/2026.

## 1. Pesquisa

Mestrado no PPGCC/UFCG, orientação do Prof. João Arthur Brunet Monteiro. O
objeto é um subtipo de dívida técnica autoadmitida (SATD) que chamamos de UBW,
de "Ugly But It Works": a pessoa desenvolvedora admite que a solução é feia, um
hack ou um workaround, e a mantém assim mesmo porque funciona. Não é qualquer
SATD, é especificamente a resignação funcional, o trade-off explícito entre
qualidade reconhecida e funcionamento.

O produto principal é um dataset minerado do GitHub, com alvo de submissão na
trilha Data & Tool do MSR 2027 (prazo estimado em novembro de 2026, CFP oficial
ainda não publicado). O repositório de código chama `gh-satd-miner` e o software
de mineração foi registrado à parte.

Gap de literatura confirmado: existe muito trabalho sobre detecção binária de
SATD e sobre taxonomias de SATD (Potdar e Shihab 2014, Maldonado e Shihab 2015,
Maldonado et al. 2017, DebtHunter 2021, IMPACT 2026), mas nenhum trabalho isola
esse subtipo, e quase todos ficam restritos a comentários de código.

## 2. O que é coletado

Quatro tipos de artefato do GitHub: comentário de código, mensagem de commit,
corpo de issue e corpo de pull request. A busca é por léxico fechado de 25
expressões, dividido em três categorias:

- Categoria A, julgamento estético e hacks explícitos, menor risco de falso
  positivo: `ugly but it works`, `ugly but works`, `dirty hack`, `this is a
  hack`, `hacky but works`, `horrible but works`, `terrible but works`, `messy
  but works`, `ugly hack`.
- Categoria B, workarounds e urgência: `ugly workaround`, `dirty workaround`,
  `quick and dirty`, `crude but it works`, `not pretty but it works`, `band-aid
  fix`, `duct tape fix`, `temporary fix`, `temp fix`, `stopgap`, `workaround for
  now`.
- Categoria C, resignação funcional e incerteza, maior risco de falso positivo:
  `not ideal but it works`, `not elegant but works`, `ugly solution but`, `ugly
  code but`, `hope everything will work`.

O léxico é fechado e versionado em `LEXICO.md` e `ubw/lexicon.py`. Sete
expressões foram promovidas por mineração de padrões em 03/07/2026, e `magic
number` foi removida por dar 0 de 10 verdadeiros positivos em amostra manual.
A categoria C é sistematicamente rara nos dados, de 1 a 3 registros por rodada
mesmo em centenas de repositórios, e isso é tratado como característica real do
fenômeno.

Cada registro guarda repositório, tipo de artefato, identificador do artefato,
expressão que casou, categoria, texto do corpo, data de criação, data de
remoção quando detectada, indicador de censura e tempo até o evento em dias e em
commits (para análise de sobrevivência), estrelas, idade e número de commits do
repositório, linguagem principal, URL, e os identificadores disponíveis do autor
mais um hash SHA-256, para permitir uma survey futura sem expor dado bruto na
publicação.

## 3. Tamanho do corpus

Números atuais, conferidos em 19/08/2026 sobre
`data/full_run/ubw_collected_consolidated.csv`:

- 116.192 registros em 26.667 repositórios, corpus bruto consolidado.
- 91.458 registros em 21.553 repositórios no frame de amostragem, que é o corpus
  sem `issue_body`. Esse é o número que aparece em todo o material oficial.
- Distribuição por artefato no frame: 43.351 mensagens de commit, 26.036
  comentários de código, 22.071 corpos de pull request.
- Expressões mais frequentes: `temporary fix` (33.660), `temp fix` (11.631),
  `this is a hack` (9.111), `ugly hack` (8.443), `quick and dirty` (8.273),
  `stopgap` (8.064).

A triagem partiu de 74.807 repositórios canônicos vindos do SEART-GHS. Números
de rodadas anteriores que ainda aparecem em documentos antigos (108 registros
do piloto de julho, 780 do round_800, 3.217 do round_3000) são históricos e não
devem ser citados como o corpus.

## 4. Infraestrutura de coleta

Minerar dezenas de milhares de repositórios em quatro canais esbarra em rate
limit, timeout e serviço de terceiro instável. O que foi implementado para isso,
e que é parte do que se reporta na trilha de ferramenta:

- Rotação de múltiplos tokens do GitHub em round-robin, cada token com estado
  próprio de rate limit.
- Agrupamento de repositórios por query da Search API, aproveitando que
  múltiplos qualificadores `repo:` funcionam como OR. Reduziu a fase de busca de
  cerca de 5,8 horas para cerca de 48 minutos num corpus de 784 repositórios.
  Quando uma expressão comum estoura o teto de 1000 resultados dentro de um
  lote, a coleta detecta e refaz por repositório para não perder recall.
- Checkpoint incremental em todas as etapas longas, com o próprio arquivo de
  saída servindo de checkpoint. O projeto já perdeu execuções inteiras por
  gravar só no final.
- Circuit breaker no cliente HTTP para outage sustentado, e Dead Letter Queue
  para repositórios que falham repetidamente no canal de comentário de código.
- Correção de TLS para o SEART-GHS, que não envia o certificado intermediário e
  cujo certificado venceu em julho de 2026. A cadeia é completada via AIA, com
  fixação de impressão digital SHA-256, sem desabilitar verificação TLS.
- Canonicalização de nomes de repositório antes da coleta, porque repositório
  renomeado quebra o qualificador `repo:` e duplica entrada.
- Filtros de precisão vindos de falso positivo real: código vendorizado por
  caminho e por nome de arquivo, autores bot, frase colando através de quebra de
  linha, e correspondência literal normalizada, porque a Search API faz stemming
  e devolve falso positivo.

Um achado de contaminação vale registro: 31,2% dos comentários de código de uma
rodada eram duplicata exata do mesmo texto dentro do mesmo repositório, vindos
de `dist/`, `build/`, arquivos minificados e principalmente `search_index.js`
gerado pelo Documenter.jl, uma cópia por versão de documentação commitada.
Corrigido por filtro de caminho mais deduplicação de texto idêntico por
repositório.

## 5. Validação humana, encerrada

Esse é o resultado central do dataset e está fechado.

Amostra de 385 itens, dimensionada por Cochran com correção de população finita
(95% de confiança, margem de 5%), estratificada proporcionalmente por tipo de
artefato, com semente 42. A categoria A/B/C deixou de ser dimensão de
estratificação na reamostragem de 29/07/2026, porque a fronteira entre as três
famílias não se mostrou discriminável de forma confiável nem entre os próprios
pesquisadores. Três anotadores (Wendell, Bruno e Miguel) anotaram os mesmos 385
itens, redundância total, cada um sem ver o rótulo dos outros.

- Kappa de Cohen final: Wendell×Bruno 0,925, Wendell×Miguel 0,872, Bruno×Miguel
  0,844, todos "excelente" na escala de Landis e Koch.
- Unanimidade em 375 de 385 itens (97,4%). Os 10 restantes foram resolvidos por
  maioria 2-1, mecanismo já previsto no guia de anotação.
- **Precisão do corpus: 92,7%, IC 95% de 90,1% a 95,3%.** Esse é o número
  oficial do artigo.
- Por tipo de artefato: comentário de código 94,5%, commit 92,9%, pull request
  90,3%.

O reporte segue sempre a tétrade concordância bruta, prevalência, kappa e AC1 de
Gwet, com leitura verbal de Landis e Koch aplicada só ao kappa, porque a escala
não vale para o AC1 (Vach e Gerke, 2023). O contexto disso é o paradoxo de
prevalência: 86,5% dos itens são positivos, então concordância bruta alta convive
com kappa moderado, e acurácia não distingue classificador bom de inútil.

Existem outros três conjuntos anotados ou reservados:

- Calibração, 200 itens, também anotados pelos três. Gabarito por maioria: 173
  positivos e 27 negativos, com 188 dos 200 unânimes. Votos individuais: Wendell
  176 positivos, Bruno 171, Miguel 172 mais um item nunca respondido.
- `watch`, 106 itens, e `near_miss`, 100 itens, pools de diagnóstico que ficaram
  fora dos batches de anotação. Decisão tomada: `near_miss` não será anotada.

Sobre a procedência da calibração, que importa para o que se pode afirmar com
ela: os 200 foram sorteados do frame inteiro de 91.458 por amostragem aleatória
estratificada por tipo de artefato, semente 42, antes de qualquer outra pool, e
as proporções batem com o frame em 0,1 ponto percentual. Os 385 vieram do
restante, disjunto da calibração. Ou seja, a calibração é uma amostra
probabilística legítima do frame, e não um pool de conveniência. O motivo de ela
não entrar em nenhuma estimativa reportada não é o sorteio, é o reuso: ela foi
usada para ajuste de prompt, seleção de juiz e treino de agregador, e um número
estimado sobre o mesmo conjunto que orientou essas escolhas fica enviesado para
cima. Isso precisa estar escrito em qualquer texto que cite os dois conjuntos.

Uma consequência menor do desenho, que também deve ser declarada: os 385 foram
sorteados do frame já sem a calibração, sem a `watch` e sem a `near_miss`, um
total de 406 itens removidos, 0,4% do frame. O efeito sobre a estimativa é
desprezível, mas a `near_miss` é adversarial por construção, então a remoção não
é aleatória e o correto é declarar em vez de omitir.

O texto que cada anotador leu foi exatamente o campo `body_text` do registro,
sem corte: verificado item a item entre os visualizadores HTML e os CSVs, com
diferença máxima de zero caractere, incluindo uma mensagem de commit de 12.834
caracteres.

## 6. Achado de validade de construto

Um experimento de prompt em agosto revelou uma tensão real que não é sobre LLM.
O guia de anotação exige, na condição 2, que o trecho expresse resignação em
manter a solução. Aplicada ao pé da letra, essa condição rejeita "temporary fix
for X" seco, porque anunciar um conserto não é o mesmo que aceitar conviver com
ele. Só que os anotadores humanos aceitam esses casos: 88% dos itens com
"temporary fix" na calibração vieram positivos.

Ou seja, o critério escrito era mais estrito que o praticado. A decisão tomada
em 19/08/2026 foi alinhar o texto à prática: marcador puramente temporal já
satisfaz a condição 2, e isso está registrado no `ANNOTATION_GUIDELINE.md`.

## 7. Onde o trabalho está agora

O que falta é uma camada automática de controle de qualidade sobre o corpus
inteiro, e é exatamente isso que precisa ser replanejado.

A ideia: a validação humana estabeleceu 92,7% de precisão numa amostra de 385;
um comitê de classificadores automáticos passaria pelos 91.458 registros
marcando os prováveis falsos positivos como coluna adicional do dataset. O
número de precisão do artigo continua vindo só da anotação humana. O escopo é
precisão do que foi capturado, não cobertura: o experimento não mede quanto UBW
existe fora do alcance das 25 expressões.

O que já foi medido de verdade, sobre os 200 de calibração, com dois modelos via
OpenRouter e temperatura zero:

| Configuração | Precisão do alerta | Cobertura dos negativos | Kappa contra humano |
|---|---|---|---|
| Qwen3 Coder, prompt zero-shot | 1,000 (7 de 7) | 25,9% | 0,611 |
| DeepSeek V3.2, prompt zero-shot | 0,500 (7 de 14) | 25,9% | 0,408 |
| Qwen3 Coder, prompt checklist | 0,129 | 66,7% | 0,027 |
| DeepSeek V3.2, prompt checklist | 0,132 | 81,5% | 0,004 |

O prompt em checklist, que transformava as cinco condições do guia em
verificação explícita, foi reprovado: rejeita cerca de 85% do que os humanos
aceitam. Foi ele que revelou o achado da Seção 6.

Diagnóstico de correlação nos dois juízes que sobrevivem ao corte: correlação
média de erro de 0,649, o que dá 1,21 votos efetivamente independentes de 2. Ou
seja, com esses dois o painel é redundante e agregar não muda nada.

Métrica de decisão: precisão do alerta, isto é, dos itens que o comitê marcou
como provável falso positivo, que fração o rótulo humano confirma. Acurácia não
serve, porque responder "é UBW" para tudo já acerta 86,5% com kappa zero.

Separação de conjuntos que precisa ser respeitada: os 200 de calibração são o
desenvolvimento, os 385 são o teste e devem ser tocados uma única vez.

## 8. Infraestrutura já implementada para essa etapa

- `scripts/07_judge_panel.py`: monta os conjuntos a partir das anotações,
  confere slug e preço dos modelos no catálogo da OpenRouter, roda um juiz sobre
  um conjunto gravando JSONL retomável, e importa as rodadas antigas.
- `scripts/panel_prompts.py`: três estratégias de prompt, zero-shot, few-shot
  fixo e few-shot recuperado por similaridade TF-IDF, com exclusão do próprio
  item na seleção de exemplos.
- `scripts/08_panel_analysis.py`: métricas por juiz, matriz de concordância
  juiz-juiz separada da concordância juiz-humano, correlação de erro, votos
  efetivos, comparação entre regras de agregação incluindo XGBoost com validação
  cruzada, e escolha da regra.

Restrições práticas: a máquina local tem 12 núcleos e 31 GB de RAM, sem GPU.
Inferência generativa local foi testada com qwen3:4b via ollama e descartada,
porque deu mais de 90 segundos por item. Há acesso a um IBM Power9. A conta da
OpenRouter está sem saldo no momento, e o nível gratuito estrangula a poucas
requisições por minuto. Rodar a matriz completa nos 200 custa centavos.

Dois detectores de SATD treinados por outros grupos estão previstos como juízes
locais gratuitos, ainda não integrados: o DebtHunter (Sala, Tommasel e Arcelli
Fontana, EASE 2021) e o MT-MoE-BERT do IMPACT (Li et al., TOSEM 2026). Como UBW
é subtipo de SATD, o voto deles é assimétrico: "não é SATD" é evidência forte de
falso positivo, "é SATD" é evidência fraca.

## 9. Referências que já entraram no desenho

- OLAF (Mia e Zaman, arXiv:2512.15979, 2025), framework de anotação por LLM em
  engenharia de software empírica, recomenda maioria quando a confiabilidade é
  parecida, agregação ponderada quando é desigual, e reportar concordância
  humano-modelo separada da modelo-modelo.
- Kohli (arXiv:2605.29800, 2026), sobre erros correlacionados: um painel de nove
  juízes de sete famílias entregou o equivalente a 2,2 votos independentes, e
  cinco juízes já capturam cerca de 90% da independência alcançável.
- IMPACT (Li et al., TOSEM 35(4), 2026), de onde vem o desenho de few-shot por
  recuperação de exemplos similares.
- Vach e Gerke (MethodsX 10, 2023), sobre não aplicar a escala verbal de
  Landis-Koch ao AC1.

## 10. Preferências de trabalho

- Nunca fabricar, simular ou ajustar dado de anotação. Alterar CSV de anotador
  só com decisão real reportada, e nunca o do Wendell, que é a referência.
- Reportar resultado como ele é, incluindo o que deu errado. Um pedido anterior
  de omitir a etapa de resolução de divergências foi recusado.
- Texto sem cara de IA: sem travessões em aposto, sem parágrafo abrindo com
  termo em negrito seguido de frase, sem lista onde prosa resolve, sem jargão de
  chatbot.
- Documentos do projeto são escritos em português.
