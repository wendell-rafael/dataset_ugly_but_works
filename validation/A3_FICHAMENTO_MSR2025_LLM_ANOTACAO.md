# Fichamento — Can LLMs Replace Manual Annotation of Software Engineering Artifacts?

Complementa `A2_CRITICA_LLM_ANOTADOR.md`, no mesmo formato de fichamento usado
na planilha de revisão da literatura do projeto.

## Metadados

**Título:** Can LLMs Replace Manual Annotation of Software Engineering Artifacts?
**Autores:** Toufique Ahmed, Premkumar Devanbu, Christoph Treude, Michael Pradel
**Instituições:** University of California, Davis; IBM Research, Yorktown Heights; Singapore Management University; University of Stuttgart
**Publicado em:** IEEE/ACM 22nd International Conference on Mining Software Repositories (MSR), 2025. Venceu o ACM SIGSOFT Distinguished Paper Award
**DOI:** 10.1109/MSR66628.2025.00086

## Qual o problema?

Estudos com sujeitos humanos em engenharia de software são caros e difíceis
de escalar. Os autores citam Haque et al., que pagaram US$60/hora via Upwork
a desenvolvedores experientes para avaliar 420 resumos de código, com
múltiplas notas por amostra para conseguir concordância inter-avaliador
estável. Ao mesmo tempo, LLMs recentes passaram a rivalizar com desempenho
humano em várias tarefas. A pergunta do artigo é direta: quando e como é
seguro substituir uma resposta humana por uma resposta de LLM, num cenário
misto humano-LLM, sem perder confiabilidade da avaliação?

Não é uma pergunta de resposta binária. Os próprios autores mostram, logo na
introdução, dois exemplos de resumos de código. Num, os três avaliadores
humanos e o GPT-4 concordam "concordo plenamente". No outro, os três humanos
discordam entre si (concordo, discordo totalmente, discordo) e o GPT-4 bate
com apenas um deles. Mesmo entre humanos a tarefa já é inconsistente em
alguns casos, o que complica qualquer comparação simples de modelo contra
humano.

## Qual a solução?

Aplicaram 6 LLMs (GPT-4, GPT-3.5, Claude-3.5-Sonnet, Gemini-1.5-Pro,
Llama3-70B, Mixtral-8x22B, todos via few-shot prompting com 3-4 exemplos) a
10 tarefas de anotação vindas de 5 datasets já existentes na literatura, não
coletados pelos autores. Compararam a concordância entre humanos, entre
humano e modelo, e entre modelos entre si.

A métrica escolhida foi Krippendorff's alpha, não Cohen's kappa, de
propósito. Alpha generaliza para qualquer número de anotadores, dados
incompletos (nem todo anotador avalia toda amostra) e qualquer tipo de
escala (nominal, ordinal, intervalar), o que os 5 datasets exigiam
simultaneamente. Kappa só serve para pares de anotadores; foi calculado à
parte, só como checagem suplementar, e o padrão relativo entre concordância
humano-humano e humano-modelo se manteve.

O núcleo metodológico são quatro perguntas de pesquisa, cada uma respondendo
uma decisão prática diferente. RQ1 mede o nível de concordância
humano-humano, humano-modelo e modelo-modelo em cada tarefa. RQ2 pergunta
como decidir, sem gastar esforço humano, se uma tarefa é candidata a ser
automatizada; a resposta é a concordância modelo-modelo, calculável sem
nenhum humano, que correlaciona fortemente com a concordância humano-modelo
(Spearman = 0,65, p < 0,05). RQ3 pergunta, dado que a tarefa é viável, quais
amostras específicas são seguras para delegar; a resposta é a confiança do
modelo, a probabilidade de saída do próprio LLM, já que amostras de alta
confiança têm mais chance de bater com o humano. RQ4 mede quanto esforço
humano dá para economizar sem perder concordância estatisticamente.

## Como foi avaliado?

Cinco datasets, dez tarefas.

| Dataset | Tarefas | Anotadores humanos | Amostras |
|---|---|---|---|
| Sumarização de código (Haque et al.) | Acurácia, adequação, concisão, similaridade | 6 | 210 funções, 420 resumos |
| Inconsistência nome-valor (Patra & Pradel) | 1 (Likert 1-5) | 11 | 40, avaliadas por todos os 11 |
| Causalidade (Fischbach et al.) | 1 (binário) | 6 | 1.000 (de 10.000+, ≥2 avaliadores) |
| Similaridade semântica (Kamp et al.) | Objetivos, operações, efeitos | 3 por amostra, pool de 8 | 786 pares |
| Aviso de análise estática (Kang et al.) | 1 (aberto/fechado/desconhecido) | apenas 2 | 200 (de 1.306, por custo/limite de taxa) |

Para cada tarefa, calcularam alpha nas três configurações (humano-humano,
humano-modelo, modelo-modelo) e depois simularam a substituição gradual:
trocar 10%, 20%, até 100% das notas humanas por notas do GPT-4, escolhidas
por confiança ou aleatoriamente, e observar em que ponto a concordância sai
da faixa de confiança do estudo só-humano.

## Quais são os resultados?

A concordância varia muito por tarefa (médias de alpha):

| Tarefa | Humano-Humano | Humano-Modelo | Modelo-Modelo |
|---|---|---|---|
| Similaridade semântica (objetivos/operações/efeitos) | 0,71–0,86 | 0,64–0,77 | 0,69–0,83 |
| Similaridade (sumarização) | 0,64 | 0,66 | 0,68 |
| Inconsistência nome-valor | 0,52 | 0,49 | 0,66 |
| Acurácia (sumarização) | 0,38 | 0,44 | 0,48 |
| Causalidade | 0,44 | 0,22 | 0,39 |
| Aviso de análise estática | 0,80 | 0,15 | 0,12 |

O caso do aviso de análise estática é o achado mais forte do artigo:
concordância humano-humano alta (0,80), mas humano-modelo e modelo-modelo
muito baixos (0,15 e 0,12). Os próprios autores concluem, sem meio-termo,
que essas descobertas sugerem que LLMs não podem substituir com segurança
as notas humanas nessa tarefa. É a tarefa que exige ler o diff e julgar se
um aviso foi corrigido de propósito ou só desapareceu incidentalmente,
contexto profundo, não julgamento superficial de texto.

No total, para 7 das 10 tarefas dá para substituir com segurança pelo menos
uma nota humana por uma de LLM, com economia de esforço entre 9% (nome-valor,
que tem 11 avaliadores) e 33% (a maioria das tarefas de 3 avaliadores).
Nenhuma tarefa permite substituir todos os humanos com segurança. Os autores
testaram e não encontraram nenhum ponto de corte de confiança em que o
modelo bata consistentemente com a maioria dos humanos em 100% das amostras.

## Resenha Crítica

Este é o precedente mais direto encontrado para o uso de LLM no UBW. Vem da
mesma conferência de onde já citamos Maldonado, Bavota e Xavier, ganhou o
prêmio de melhor artigo do MSR 2025 e foi publicado há poucos meses. O
achado mais importante para o projeto não é que LLM funciona bem, é a
distinção entre tarefa de baixo contexto e tarefa de alto contexto. O
exemplo de alto contexto que os autores dão, o aviso de análise estática,
exige ler o diff e julgar intenção, o que se aproxima do que se pede ao
anotador do UBW muito mais do que se aproxima da comparação superficial de
texto que caracteriza uma tarefa de baixo contexto. Julgar `is_ubw` exige
aplicar as 5 condições do guideline: autor falando de si mesmo, trade-off
explícito, referência a código real, ausência de negação, ausência de ruído
de string. Isso é julgamento contextual.

Se o padrão do artigo se sustenta, a tarefa do UBW está mais perto do 0,12
do aviso de análise estática do que do 0,83 de similaridade semântica.
Reforça, com evidência empírica e não só o argumento teórico de Reiss e
Ziems já usado antes, a decisão de manter LLM só como pré-filtro.

Valem dois pontos técnicos. A escolha de Krippendorff's alpha em vez de
Cohen's kappa segue a mesma razão que está em aberto na reunião com o
especialista em quantitativa, e serve como precedente de um MSR premiado
optando por alpha justamente pela heterogeneidade de escalas e de número de
anotadores entre tarefas. E o próprio artigo tem um limite que o UBW não
tem: avalia a distribuição natural dos datasets originais, sem nenhum pool
adversarial deliberado. O pool de near-miss do UBW, os 100 itens escolhidos
por parecerem falsos positivos, é um teste mais rigoroso do que qualquer
coisa que este artigo faz.

O que o artigo não resolve, e que é relevante para o UBW: eles nunca tentam
substituir todos os humanos, só uma fração, com um humano sempre como
âncora. Isso é consistente com o desenho do UBW, mas eles não têm uma
segunda camada de verificação equivalente ao desempate por terceiro
anotador. Para eles, substituir uma nota já é o ponto final da cadeia de
decisão.

## O que isso tem a ver com o UBW?

Serve como evidência empírica, não só teórica, de que a tarefa de anotação
do UBW, por ser de alto contexto, provavelmente cairia no grupo onde LLM não
substitui humano com segurança. Isso reforça a decisão já tomada de LLM como
pré-filtro apenas. A ideia de concordância modelo-modelo como preditor
barato, da RQ2 do artigo, é uma extensão que vale considerar para o próprio
pipeline: rodar 2-3 LLMs na triagem em vez de 1, e usar a concordância entre
eles como sinal adicional de quão arriscado é um item antes mesmo de chegar
no humano. E a escolha de Krippendorff's alpha entra como precedente
concreto para a discussão com o especialista em quantitativa sobre reportá-lo
ao lado de κ e AC1.

## Replicação

Os autores disponibilizam prompts detalhados e exemplos few-shot em material
suplementar, e há um pacote de replicação publicado no Zenodo. O código de
análise (cálculo de alpha, correlação de Spearman, simulação de substituição
gradual) é reproduzível a partir da descrição do artigo. Os datasets
originais (Haque et al., Patra & Pradel, Fischbach et al., Kamp et al., Kang
et al.) são de terceiros, com disponibilidade variável. Os próprios autores
citam, na seção de ameaças à validade, que é difícil achar datasets públicos
com as notas de cada anotador preservadas, já que a maioria só publica o
rótulo final de consenso.
