# Complemento ao Agente A — Por que a triagem final tem que ser manual

Pesquisa feita fora do Cowork, a pedido direto do Wendell (2026-07-27), pra
fundamentar com a literatura a decisão de que a validação de precisão do
dataset UBW (TP/FP) precisa ser feita por anotação humana em pares, não por
LLM, mesmo com a triagem LLM já implementada em `03_metrics_llm_triage.py`.
Isso já é a postura do protocolo atual (guideline Seção 2: "LLM nunca é
definitiva por si só"); este documento é a munição bibliográfica para
apresentar essa escolha ao orientador.

**Metodologia desta busca:** WebSearch, verificação de título/arXiv ID de cada
referência antes de listar. Não encontrei um caso público de "paper rejeitado
por usar só LLM como anotador" — pareceres de revisão não costumam ser
públicos — então não fabriquei esse tipo de exemplo. O que existe, e é mais
forte para citar, são (1) papers que testam e quantificam a não-confiabilidade
do LLM como anotador, e (2) os padrões/checklists que a comunidade usa como
critério de aceitação, que exigem exatamente o que o UBW já faz.

---

## 1. Papers que testam e quantificam a não-confiabilidade do LLM como anotador

- **Reiss, M. V. (2023).** *Testing the Reliability of ChatGPT for Text
  Annotation and Classification: A Cautionary Remark.* arXiv:2304.11085.
  Achado central: o ChatGPT é **não-determinístico** — o mesmo input, ou uma
  reformulação mínima do prompt, produz classificações diferentes em rodadas
  distintas. Recomendação explícita do autor: **validação contra dados
  anotados por humanos é necessária**; uso não supervisionado de LLM para
  anotação/classificação **não é recomendado**. Esta é a citação mais direta
  para justificar "por que não aceitar o rótulo do LLM como definitivo",
  porque ataca exatamente a premissa (consistência) que tornaria o LLM
  aceitável como *ground truth*.

- **Zheng, L. et al. (2023).** *Judging LLM-as-a-Judge with MT-Bench and
  Chatbot Arena.* NeurIPS 2023 (Datasets and Benchmarks Track). arXiv:2306.05685.
  Não é sobre SATD, mas é a referência canônica sobre **vieses sistemáticos**
  de LLM atuando como avaliador/juiz: viés de posição (ordem dos itens
  comparados), viés de verbosidade (prefere respostas mais longas
  independente de qualidade) e viés de auto-favorecimento (favorece saídas
  do próprio modelo). Relevante para o UBW porque a tarefa de classificar
  `is_ubw`/categoria tem exatamente o tipo de ambiguidade textual sutil onde
  esses vieses aparecem (ver os near-misses do guideline, Seção 6).

- **Ziems, C. et al. (2024).** *Can Large Language Models Transform
  Computational Social Science?* Computational Linguistics 50(1):237–291
  (também arXiv:2305.03514). O mais equilibrado dos três: não descarta o LLM,
  mas define **duas condições** para usá-lo de forma responsável —
  (a) tratar o LLM como só mais um anotador dentre humanos e IA, com rótulo
  final decidido por voto majoritário; ou (b) usar o LLM só para
  pseudo-rótulos combinados com uma **amostra pequena de gold labels
  humanos** via estimadores não enviesados (ex.: *Design-based
  Semi-supervised Learning*, DSL). **Isso é, na prática, uma descrição quase
  literal do que o UBW já faz**: LLM pré-tria, incerto e uma auditoria de 15%
  vão para humano, e a amostra de ~385 itens é o gold set que ancora a
  precisão real. Cite este paper para mostrar que a arquitetura do pipeline
  UBW já segue o desenho que a literatura recomenda como uso responsável de
  LLM em anotação — não é evitar LLM por precaução ingênua, é uma escolha de
  desenho alinhada ao estado da arte.

---

## 2. Padrões que funcionam como critério de aceitação (o que os revisores checam)

Não existe um "índice de papers rejeitados", mas existem os documentos que a
comunidade usa para decidir o que é um dataset/anotação aceitável — e checar
o dataset UBW contra eles é o substituto defensável de "o que diferencia
aprovado de rejeitado":

- **Bender, E. M. & Friedman, B. (2018).** *Data Statements for Natural
  Language Processing: Toward Mitigating System Bias and Enabling Better
  Science.* TACL. Um dos dois documentos fundadores de documentação de
  dataset citados por praticamente toda revisão de ética/dados em NLP desde
  então.

- **Gebru, T. et al. (2018/2021).** *Datasheets for Datasets.* arXiv:1803.09010
  (publicado em Communications of the ACM, 2021). O outro documento fundador;
  pergunta explicitamente como as anotações foram coletadas, validadas e por
  quem.

- **Rogers, A., Baldwin, T. & Leins, K. (2021).** *"Just What do You Think
  You're Doing, Dave?" A Checklist for Responsible Data Use in NLP.* EMNLP
  Findings 2021. Base direta do **ACL Responsible NLP Research Checklist**
  (usado hoje por ACL/EMNLP/NAACL/ARR como parte formal da revisão — todo
  autor preenche esse checklist ao submeter). Uma das perguntas do checklist
  cobre explicitamente características e controle de qualidade da população
  de anotadores. É o item mais próximo de um "critério objetivo de revisor"
  que existe hoje em NLP, e serve de analogia direta para o padrão que MSR/
  ICSE/TSE esperam implicitamente em papers de mineração com anotação manual.

- **Artstein, R. & Poesio, M. (2008).** *Inter-Coder Agreement for
  Computational Linguistics.* Computational Linguistics 34(4):555–596.
  A referência clássica sobre por que reportar concordância inter-anotador
  (κ e afins) é considerado requisito metodológico básico, não opcional —
  serve de base teórica para por que o UBW reporta κ **e** AC1 em paralelo.

- **Who Annotates in NLP? A Large-scale Assessment of Human Annotation
  Reporting between 2018 and 2025.** arXiv:2606.02255 (2026). **Achado mais
  relevante pra sua pergunta específica** sobre o que mudou pré/pós boom de
  LLM: é uma auditoria em larga escala (1.603 papers, 2.667 tarefas de
  anotação, veículos ACL, 2018–2025) de **quem** anotou e **o que** foi
  reportado sobre o processo. Cobre exatamente a janela do boom de LLM
  (2018–2025) e audita a prática real de relato de anotação humana ao longo
  dela. Os números exatos de tendência (se relato de anotação humana caiu,
  subiu, ou como LLM entrou nesse espaço) não vieram completos na busca —
  **a confirmar**: recomendo ler o paper completo antes de citar números
  específicos dele na dissertação, mas o próprio recorte temporal e o desenho
  do estudo já servem como evidência de que a comunidade de NLP considera
  essa uma pergunta metodológica séria o suficiente para uma auditoria em
  larga escala.

---

## 3. Como isso se traduz em argumento pro orientador

O argumento não precisa ser "LLM é ruim" — é mais preciso e mais defensável
dizer:

1. A literatura (Reiss 2023, Zheng et al. 2023) mostra que LLM sozinho **não
   é confiável o suficiente pra ser *ground truth*** em tarefas de
   classificação textual ambígua — exatamente o tipo de ambiguidade que o
   guideline do UBW documenta nos near-misses (Seção 6).
2. A literatura que **não** descarta o LLM (Ziems et al. 2024) só o endossa
   sob desenhos específicos — voto majoritário entre anotadores humanos e IA,
   ou LLM como pseudo-rótulo ancorado por uma amostra gold humana — e o UBW
   já implementa a segunda opção.
3. Os padrões que a comunidade usa pra avaliar rigor de dataset (Datasheets,
   Data Statements, o checklist do ACL Rolling Review, Artstein & Poesio para
   concordância) pedem, todos, documentação e validação humana do processo de
   anotação — nenhum aceita "o LLM rotulou" como suficiente.
4. Portanto, a decisão de tratar a triagem LLM como pré-filtro e reservar a
   anotação em pares humana como fonte da métrica de precisão reportada não é
   conservadorismo — é o desenho que a própria literatura recente sobre uso de
   LLM em anotação recomenda como responsável.

---

## Referências (formato solto, verificar formatação final antes de ir para a dissertação)

- Reiss, M. V. (2023). Testing the Reliability of ChatGPT for Text Annotation and Classification: A Cautionary Remark. arXiv:2304.11085.
- Zheng, L., Chiang, W.-L., Sheng, Y. et al. (2023). Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. NeurIPS 2023 (Datasets and Benchmarks). arXiv:2306.05685.
- Ziems, C., Held, W., Shaikh, O., Chen, J., Zhang, Z. & Yang, D. (2024). Can Large Language Models Transform Computational Social Science? Computational Linguistics, 50(1), 237–291. arXiv:2305.03514.
- Bender, E. M. & Friedman, B. (2018). Data Statements for Natural Language Processing: Toward Mitigating System Bias and Enabling Better Science. TACL, 6, 587–604.
- Gebru, T., Morgenstern, J., Vecchione, B. et al. (2018/2021). Datasheets for Datasets. arXiv:1803.09010 / Communications of the ACM, 64(12), 86–92.
- Rogers, A., Baldwin, T. & Leins, K. (2021). "Just What do You Think You're Doing, Dave?" A Checklist for Responsible Data Use in NLP. Findings of EMNLP 2021.
- Artstein, R. & Poesio, M. (2008). Inter-Coder Agreement for Computational Linguistics. Computational Linguistics, 34(4), 555–596.
- Who Annotates in NLP? A Large-scale Assessment of Human Annotation Reporting between 2018 and 2025 (2026). arXiv:2606.02255. *(ler o paper completo antes de citar números — busca não confirmou os achados quantitativos exatos.)*
