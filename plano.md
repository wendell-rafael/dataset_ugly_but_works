# Plano de Experimento: *Ugly But It Works* (UBW)
**Construção do Dataset de Resignação Funcional em Repositórios Open-Source**

Wendell — PPGCC/UFCG · Orientador: Prof. João Arthur Brunet Monteiro

---

> **Escopo:** Este documento descreve o experimento de coleta e construção do dataset UBW anotado, incluindo scripts de coleta reproduzíveis e protocolo de anotação. As análises de sobrevivência (RQ2) e o survey (RQ3) dependem do dataset aqui produzido e são tratados como trabalho futuro.

---

## 1. Questões de Pesquisa

Apenas RQ1 é endereçada diretamente pelos entregáveis deste plano. RQ2 e RQ3 dependem do dataset produzido aqui e serão investigadas em etapa subsequente.

**RQ1 — Caracterização do fenômeno** *(endereçada neste plano)*
Com que frequência expressões UBW ocorrem em repositórios open-source e como se distribuem entre as categorias semânticas (A, B, C) e os tipos de artefato (comentários de código, commits, issues, PRs)?

**RQ2 — Dinâmica temporal** *(trabalho futuro)*
Comentários UBW têm tempo de vida maior do que SATD genérico equivalente? A taxa de remoção difere entre as categorias?

**RQ3 — Motivações** *(trabalho futuro)*
Quais fatores técnicos, organizacionais e cognitivos levam desenvolvedores a introduzir código UBW? As motivações diferem entre as categorias?

---

## 2. Corpus de Repositórios

### 2.1 Fonte de dados

A seleção usa o **SEART-GHS** (Dabic et al., 2021), que indexa mais de 735 mil repositórios GitHub com atributos pré-calculados (estrelas, forks, commits, linguagem etc.), dispensando varredura direta da API do GitHub na fase de triagem. A curadoria segue os critérios de Munaiah et al. (2017) para distinguir projetos reais de repositórios pessoais ou experimentais.

### 2.2 Critérios de inclusão

| Critério | Valor | Justificativa |
|---|---|---|
| Estrelas | ≥ 100 | Proxy de popularidade e relevância (Dabic et al., 2021) |
| Commits totais | ≥ 100 | Maturidade mínima para análise futura de sobrevivência |
| Contribuidores | ≥ 3 | Distingue projetos de equipe de projetos pessoais (Munaiah et al., 2017) |
| Último commit | ≤ 2 anos | Repositórios inativos distorcem taxas de remoção |
| Issues e PRs | Habilitados | Necessário para coleta multi-artefato |
| Fork | Não | Evita duplicidade de comentários no corpus |
| Linguagem | Sem restrição | Entra como covariável futura; não é critério de exclusão |

### 2.3 Flexibilização de critérios

Se o corpus resultar com menos de 60 eventos de remoção por categoria UBW, os thresholds de estrelas e contribuidores serão reduzidos progressivamente, com registro de cada ajuste. A decisão é tomada após o piloto (Seção 3.1), não antes.

### 2.4 Threshold de inclusão no corpus final

Um repositório entra no corpus final apenas se tiver **≥ 5 ocorrências UBW** em pelo menos um tipo de artefato coletado. O valor equilibra dois riscos: abaixo dele, as estimativas de sobrevivência por repositório têm variância muito alta; acima de um limite excessivo (≥ 20), o corpus fica enviesado para projetos com volume anormal de SATD, que Bavota & Russo (2016) identificaram como outliers com comportamento de remoção atípico.

Este threshold é aplicado apenas ao subconjunto destinado à análise de sobrevivência (RQ2). A RQ1 é calculada sobre todos os repositórios do corpus, inclusive os com zero ocorrências, que entram como denominador.

Se o piloto mostrar que o threshold de 5 exclui mais de 40% dos repositórios com ocorrências UBW, o valor será reduzido para 3, com análise de sensibilidade comparando os resultados.

---

## 3. Léxico UBW e Estratégia de Coleta

### 3.1 Piloto exploratório

Antes da coleta em larga escala, o léxico será testado em **20 repositórios aleatórios** fora do corpus final, com os objetivos de: estimar a precisão preliminar de cada expressão (verdadeiros positivos / total de candidatos); identificar expressões com precisão abaixo de 50% para revisão ou remoção; estimar o volume total esperado no corpus completo; e verificar a viabilidade do threshold de 5 ocorrências.

Para as expressões de maior risco (Categoria C e as marcadas com ⚠), o piloto continua até acumular pelo menos 20 candidatos por expressão, garantindo base estatística mínima para a decisão de manter ou remover.

**Marco crítico:** ao fim do Mês 2, o léxico está fechado e aprovado pelo orientador. Nenhuma alteração é feita depois disso sem registro explícito de justificativa.

### 3.2 Léxico (pós-piloto)

O léxico é organizado em três categorias semânticas. Essa organização é uma contribuição deste estudo: Potdar & Shihab (2014) tratam expressões similares como lista plana sem distinção semântica, e Maldonado & Shihab (2015) estratificam por tipo de dívida técnica (design, teste, documentação), não pela intenção do desenvolvedor.

As categorias têm perfis de ambiguidade diferentes. A Categoria A tem menor risco de falso positivo, pois expressões como `ugly but it works` raramente aparecem fora de contexto de resignação técnica. A Categoria B tem risco intermediário. A Categoria C tem o maior risco, pois suas expressões são mais genéricas. As estimativas do piloto serão analisadas por categoria, com critério de corte mais rigoroso aplicado à Categoria C.

**Categoria A — Julgamento estético e hacks explícitos**

Código fora dos padrões mantido exclusivamente pela funcionalidade. Expressões como `dirty hack` constam nas top-10 feature words de design debt em Maldonado et al. (2017), e `ugly` é sinal de alta relevância em Ren et al. (2019).

`ugly but it works`, `ugly but works`, `dirty hack`, `this is a hack`, `hacky but works`, `horrible but works`, `terrible but works`, `messy but works`

**Categoria B — Workarounds e urgência**

Soluções temporárias que tendem a se tornar permanentes. `band-aid fix` e `duct tape fix` evocam reparos emergenciais que sobrevivem indefinidamente, o que Maipradit et al. (2020) chamam de *On-Hold SATD*. `quick and dirty` consta no léxico de Potdar & Shihab (2014) e `workaround` é uma das feature words mais discriminativas de requirement debt em Maldonado et al. (2017).

`ugly workaround`, `dirty workaround`, `quick and dirty`, `crude but it works`, `not pretty but it works`, `band-aid fix`, `duct tape fix`

**Categoria C — Resignação funcional e incerteza**

Aceitação de uma solução subótima associada à falta de entendimento do sistema ou ao medo de introduzir regressões ao refatorar. As expressões desta categoria são as mais próximas do conceito de *Aging Debt* de Sridharan et al. (2025), dívida que envelhece sem resolução.

`not ideal but it works`, `not elegant but works`, `ugly solution but`, `ugly code but`, `magic number` ⚠, `hope everything will work`, `don't touch` ⚠

*(⚠ = alto risco de falso positivo; reavaliação obrigatória após o piloto)*

### 3.3 Estratégia de coleta por tipo de artefato

A coleta usa a GitHub REST API com autenticação via PAT. Para todos os artefatos, as queries incluem o qualificador `repo:owner/name`, iterando sobre a lista de repositórios selecionados. Isso garante que os dados coletados correspondem exatamente ao corpus curado na Seção 2.

As queries abaixo usam `"ugly but it works"` como expressão ilustrativa. O mesmo padrão se aplica a todas as expressões do léxico.

#### Seleção de repositórios (SEART-GHS)

```
GET https://seart-ghs.si.usi.ch/api/r/search
    ?gt:stars=100
    &gt:commits=100
    &gt:contributors=3
    &is:fork=false
    &gt:lastCommit=730d
    &has:issues=true
```

#### Comentários de código (git grep)

A extração é feita via clone local, evitando o teto de 1.000 resultados da Search API e garantindo acesso ao histórico completo. Os resultados são filtrados por tokens de comentário (`//`, `#`, `/* */`, `"""` etc.) para excluir ocorrências em string literals, dados embutidos e fixtures de teste.

```bash
git grep --ignore-case --line-number --context=3 \
    "ugly but it works" \
    -- "*.py" "*.java" "*.js" "*.ts" "*.c" "*.cpp" "*.go" "*.rb"
```

Rastreamento temporal via `git log` pickaxe:

```bash
git log --all --follow -S "ugly but it works" \
    --pretty=format:"%H %ai" -- caminho/do/arquivo.py
```

O primeiro commit em ordem cronológica corresponde à introdução. O commit subsequente que remove a string corresponde à remoção. Se a string ainda existe no HEAD, o registro é censurado (`is_censored = 1`).

#### Issues

```
GET /search/issues
    ?q="ugly but it works" in:body type:issue repo:owner/name
    &sort=created&order=asc&per_page=100
```

`closed_at` é usado como timestamp de resolução. Issues abertas são censuradas.

#### Pull Requests

```
GET /search/issues
    ?q="ugly but it works" in:body type:pr repo:owner/name
    &sort=created&order=asc&per_page=100
```

PRs com `merged_at` preenchido ou `state=closed` são considerados resolvidos.

#### Commit messages

```
GET /search/commits
    ?q="ugly but it works" repo:owner/name
    &sort=committer-date&order=asc&per_page=100
```

Como commits são imutáveis, todos os registros deste artefato recebem `is_censored = 1` e contribuem apenas para RQ1.

#### Limites de rate limit

| Endpoint | Limite (PAT autenticado) | Observação |
|---|---|---|
| `/search/*` | 30 req/min | Requer intervalo mínimo de 2s entre chamadas |
| REST geral | 5.000 req/h | Usado para enriquecimento de metadados |

### 3.4 Reprodutibilidade

Os resultados da Search API mudam ao longo do tempo. O replication package incluirá a data de corte exata da coleta, as respostas brutas arquivadas em JSON e os SHAs de commit para ancorar o estado de cada repositório.

### 3.5 Schema de coleta

| Campo | Tipo | Justificativa |
|---|---|---|
| `repo_full_name` | string | Chave de join; rastreabilidade ao repositório de origem |
| `artifact_type` | enum | `code_comment`, `commit_message`, `issue_body`, `pr_body` — Li et al. (2023) |
| `artifact_id` | string | SHA (commits), número (issues/PRs), `filepath:line` (comentários) |
| `matched_expression` | string | Expressão que disparou a coleta; usada para estimar precisão por expressão |
| `category_ubw` | enum | `A`, `B`, `C` — derivada de `matched_expression` |
| `body_text` | string | Janela de ±3 linhas para `code_comment`; corpo completo para os demais |
| `created_at` | datetime ISO 8601 | Timestamp de introdução; para `code_comment`, via `git log` pickaxe |
| `removed_at` | datetime / NULL | Timestamp de remoção; NULL se ainda presente (Rantala et al., 2020) |
| `is_censored` | boolean | 1 = ainda presente na data de corte; 0 = evento observado |
| `time_to_event_days` | integer | Dias entre `created_at` e `removed_at` (ou data de corte) |
| `time_to_event_commits` | integer | Commits entre introdução e remoção (Rantala et al., 2020) |
| `repo_stars` | integer | Proxy de popularidade (Dabic et al., 2021) |
| `repo_age_days` | integer | Dias desde o primeiro commit; variável de confusão |
| `repo_commits` | integer | Volume de atividade do repositório |
| `primary_language` | string | Covariável futura no modelo Cox |
| `url` | string | Link direto ao artefato; rastreabilidade para replicação |

---

## 4. Operacionalização do Evento de Remoção

A definição de "remoção" é a decisão metodológica de maior impacto na variável dependente da análise de sobrevivência futura, e varia por tipo de artefato:

| Artefato | Definição de remoção | Justificativa |
|---|---|---|
| Comentários de código | Desaparecimento textual no diff entre commits consecutivos | Operacionalização conservadora; mudança de arquivo sem alterar o comentário não conta |
| Commit messages | Não se aplica — commits são imutáveis | |
| Issue bodies | Fechamento da issue (`closed` via API) | Análogo funcional à resolução em sistemas de issue tracking |
| PR bodies | Merge ou fechamento do PR | Idem |

Quando o arquivo inteiro é deletado ou o repositório é arquivado, o evento é tratado como censura, não como remoção intencional, alinhando com Zampetti et al. (2018), que encontraram que 20–50% das remoções de SATD são acidentais. Qualquer instância ainda presente na data de corte recebe `is_censored = 1`.

---

## 5. Validação Manual e Anotação

### 5.1 Objetivos

A validação manual tem dois objetivos: estimar a **precisão do léxico** (quantos candidatos coletados são genuinamente instâncias de UBW) e validar a **atribuição de categoria** (se a classificação A/B/C derivada automaticamente coincide com a categoria que anotadores atribuem ao ler o contexto completo).

Para estimar a precisão bruta do léxico, uma amostra é extraída dos candidatos **antes** da pré-triagem por LLM. Isso separa a precisão do filtro léxico da precisão do pipeline completo, e as duas métricas são reportadas de forma independente.

### 5.2 Tamanho da amostra

O tamanho segue o critério padrão da área: 95% de confiança com margem de erro de 5%, que converge para aproximadamente 385 itens para populações acima de 5.000. Esse critério foi usado por Bavota & Russo (2016) e por Pham et al. (2025). A amostra é estratificada por categoria (A, B, C) e por tipo de artefato.

### 5.3 Time de anotação

Mínimo de dois anotadores independentes, com possibilidade de um terceiro para desempate.

### 5.4 Protocolo

O protocolo segue as etapas de Awon (2024), que alcançou kappa de 0,926 com calibração prévia:

1. **Guideline de anotação:** definições operacionais de cada categoria, exemplos positivos e negativos por tipo de artefato e regras de desempate para casos limítrofes
2. **Calibração:** 50 itens por tipo de artefato anotados de forma independente, seguidos de sessão de discussão. Maldonado & Shihab (2015) mostram que isso reduz divergências residuais em até 30%
3. **Anotação plena** da amostra estratificada, de forma independente por cada anotador, seguida de cálculo de concordância e resolução de divergências por consenso

Cada item recebe três rótulos: `is_ubw` booleano, `category_confirmed` (A, B, C ou "não classificável") e `confidence` em três níveis (certo, provável, incerto).

### 5.5 Métricas de concordância

O **Cohen's kappa** é a métrica padrão da área (Maldonado & Shihab, 2015; Bavota & Russo, 2016). O mínimo aceitável é κ ≥ 0,61 (Landis & Koch, 1977); κ ≥ 0,80 é considerado excelente. O **Gwet's AC1** é reportado em paralelo por ser mais robusto ao paradoxo do kappa em classes desbalanceadas (Gwet, 2008), conforme recomendado por Wongpakaran et al. (2013). As métricas são calculadas separadamente para a tarefa binária `is_ubw` e para a classificação de categoria, restrita aos verdadeiros positivos.

A concordância na atribuição de categoria é o principal indicador da viabilidade da taxonomia A/B/C proposta. Se esse kappa vier baixo, a contribuição central do estudo fica fragilizada.

### 5.6 LLM como pré-triagem

O classificador LLM reduz o volume que chega à anotação humana, mas não substitui os anotadores. O fluxo é: o filtro léxico gera N candidatos; o LLM classifica cada um como `UBW-verdadeiro`, `não-UBW` ou `incerto`; itens `incerto` vão obrigatoriamente para anotação humana; uma amostra aleatória de 15% dos demais também é revisada por humanos. Se o kappa entre LLM e anotadores ficar abaixo de 0,61, a triagem automática é descartada e a anotação é feita integralmente por humanos.

---

## 6. Trabalho Futuro

**Análise de sobrevivência (RQ2):** pipeline KM por categoria → log-rank test com correção de Bonferroni → modelo Cox com covariáveis (`category_ubw`, `artifact_type`, `repo_age_days`, `repo_stars`, `primary_language`), com verificação via resíduos de Schoenfeld. O modelo requer ≥ 10 eventos por covariável (Peduzzi et al., 1996), o que implica ≥ 110–165 instâncias por categoria considerando taxas de remoção observadas na literatura de SATD (Li et al., 2021).

**Survey de motivações (RQ3):** instrumento em três blocos (perfil do respondente, escala Likert com 12 itens, campo aberto), recrutamento via e-mail para contribuidores dos repositórios do corpus, comparação ao baseline de Xavier et al. (2020).

---

## 7. Entregáveis

**Primários (escopo deste plano)**

1. Dataset UBW anotado com schema completo (Seção 3.5), incluindo label manual, categoria e metadados do repositório
2. Scripts de coleta em Python reproduzíveis via SEART-GHS e GitHub API
3. Guideline de anotação com definições operacionais, exemplos e regras de desempate
4. Relatório de concordância inter-anotadores: kappa e Gwet's AC1 por tipo de artefato e categoria
5. Estimativas de precisão do léxico por expressão e categoria com IC binomial, calculadas antes da triagem LLM

**Futuros (dependem do dataset)**

1. Curvas Kaplan-Meier com IC 95% e medianas de sobrevivência por categoria
2. Tabela de coeficientes Cox com hazard ratios, IC e p-valores
3. Resultados do survey de motivações (RQ3)

---

## 8. Decisões Metodológicas

| Decisão | Escolha | Referência | O que ancora |
|---|---|---|---|
| Seleção de repositórios | SEART-GHS + critérios de inclusão | Dabic et al. (2021); Munaiah et al. (2017) | Indexa 735 mil repositórios com 25 atributos pré-calculados, dispensando varredura direta da API. Critérios de ≥ 3 contribuidores e distinção projeto real vs. pessoal derivam do Reaper. |
| Sem restrição de linguagem de programação | Linguagem como covariável futura | Sutoyo et al. (2024) | Dataset multi-linguagem mostra que SATD transcende linguagens; restrição a Java reduziria cobertura sem ganho metodológico. |
| Multi-artefato (4 tipos) | Issues, PRs, commits, code comments | Li et al. (2023) | SATD distribui-se de forma relativamente uniforme entre as quatro fontes; restringir a comentários de código subamostria o fenômeno. |
| Queries restritas ao corpus | Qualificador `repo:` por repositório | — | Consistência entre seleção e coleta; evita candidatos de fora do corpus curado. |
| Filtro por tokens de comentário | Excluir string literals e dados embutidos | — | Validade de construto; ocorrências em strings não representam SATD de desenvolvedores. |
| Threshold ≥ 5 aplicado só à RQ2 | RQ1 usa corpus completo como denominador | Bavota & Russo (2016) | Repositórios com volume anormal de SATD são outliers com comportamento de remoção atípico; threshold protege a análise de sobrevivência sem distorcer a contagem de prevalência. |
| Piloto dimensionado por candidatos | ≥ 20 candidatos por expressão de alto risco | — | Base estatística mínima por expressão para decisão de manter ou remover do léxico. |
| Remoção = desaparecimento textual (code) | Conservador, evita falsos positivos | Rantala et al. (2020) | Operacionalização do tempo de sobrevivência em commits, alinhada com literatura de KL-SATD. |
| Remoção acidental → censura | Evita contaminação da taxa de remoção | Zampetti et al. (2018) | 20–50% das remoções de SATD são acidentais (deleção de arquivo inteiro); tratá-las como evento distorceria hazard ratios. |
| Precisão bruta medida antes do LLM | Separa precisão léxica da precisão do pipeline | — | Permite avaliar contribuição independente do filtro léxico e da triagem automática. |
| Kappa + Gwet's AC1 | Robusto a desbalanceamento de classes | Gwet (2008); Wongpakaran et al. (2013) | Corpora SATD têm maioria de instâncias não-SATD; kappa paradox pode subestimar concordância real. |
| ~385 itens estratificados | Confiança de 95%, margem de 5% | Bavota & Russo (2016); Pham et al. (2025) | Tamanho padrão de amostra para validação manual na área. |
| LLM como pré-triagem apenas | Não substitui anotadores humanos | — | Presença de incertezas semânticas nas categorias B e C exige julgamento humano contextual. |
| Pipeline KM → log-rank → Cox (futuro) | Análise de sobrevivência em três camadas | Li et al. (2021) | Pipeline validado empiricamente para SATD; distingue diferenças entre grupos antes de modelar covariáveis. |
| ≥ 10 eventos por covariável no Cox | EPV rule | Peduzzi et al. (1996) | Estudo de simulação Monte Carlo; abaixo desse limiar os coeficientes são instáveis e viiesados. |
| Python (`lifelines`) | Reprodutibilidade; padrão em MSR | — | Biblioteca madura e bem documentada para análise de sobrevivência em Python. |

---

## 9. Limitações

**Precisão do léxico:** matching lexical gera falsos positivos (ex: `"not ideal but it works"` em contexto não-SATD). Mitigado pela validação manual e pela gradação de risco entre categorias.

**Viés de seleção:** repositórios com ≥ 100 estrelas não representam todo o universo open-source. Os resultados não generalizam para projetos de baixa visibilidade.

**Léxico em inglês:** o léxico captura expressões em inglês, que é a língua franca do OSS. Comentários em outros idiomas ficam fora do escopo, o que é uma limitação à validade externa.

**Definição de remoção para issues e PRs:** fechamento de issue não implica que o código UBW foi corrigido. O evento é tratado como resolução do artefato, não remoção do código. Isso deve ser considerado ao interpretar comparações de sobrevivência entre tipos de artefato.

---

## 10. Referências

**Awon, M. (2024)** — *Self-Admitted Technical Debt in Scientific Software*. Dissertação de mestrado. Protocolo de calibração com 50 itens por tipo de artefato antes da anotação plena; kappa geral de 0,926 (κ = 0,843–0,960 por artefato).

**Bavota, G. & Russo, B. (2016)** — "A Large-Scale Empirical Study on Self-Admitted Technical Debt". *Proceedings of the 13th IEEE/ACM Working Conference on Mining Software Repositories (MSR 2016)*, pp. 315–326. DOI: 10.1145/2901739.2901742

**Dabic, O., Aghajani, E. & Bavota, G. (2021)** — "Sampling Projects in GitHub for MSR Studies". *MSR 2021*, pp. 560–564. DOI: 10.1109/MSR52588.2021.00074 · arXiv: 2103.04682

**Gwet, K.L. (2008)** — "Computing inter-rater reliability and its variance in the presence of high agreement". *British Journal of Mathematical and Statistical Psychology*, 61(1), 29–48. DOI: 10.1348/000711006X126600

**Landis, J.R. & Koch, G.G. (1977)** — "The Measurement of Observer Agreement for Categorical Data". *Biometrics*, 33(1), 159–174. DOI: 10.2307/2529310

**Li, Y. et al. (2021)** — "An Exploratory Study on the Introduction and Removal of Different Types of Technical Debt". arXiv: 2101.03730. *(Pipeline KM → log-rank → Cox para análise de sobrevivência de SATD.)*

**Li, Y., Soliman, M. & Avgeriou, P. (2023)** — "Automatic identification of self-admitted technical debt from four different sources". *Empirical Software Engineering*, 28(3), art. 65. DOI: 10.1007/s10664-023-10297-9

**Maipradit, R., Treude, C., Hata, H. & Matsumoto, K. (2020)** — "Wait for it: identifying 'On-Hold' self-admitted technical debt". *Empirical Software Engineering*, 25, 3770–3798. DOI: 10.1007/s10664-020-09854-3

**Maldonado, E.S. & Shihab, E. (2015)** — "Detecting and Quantifying Different Types of Self-Admitted Technical Debt". *7th IEEE International Workshop on Managing Technical Debt (MTD 2015)*, pp. 9–15. DOI: 10.1109/MTD.2015.7332619

**Maldonado, E.S., Shihab, E. & Tsantalis, N. (2017)** — "Using Natural Language Processing to Automatically Detect Self-Admitted Technical Debt". *IEEE Transactions on Software Engineering*, 43(11), 1044–1062. DOI: 10.1109/TSE.2017.2654244

**Munaiah, N., Kroh, S., Cabrey, C. & Nagappan, M. (2017)** — "Curating GitHub for Engineered Software Projects". *Empirical Software Engineering*, 22(6), 3219–3253. DOI: 10.1007/s10664-017-9512-6

**Peduzzi, P., Concato, J., Kemper, E., Holford, T.R. & Feinstein, A.R. (1996)** — "A simulation study of the number of events per variable in logistic regression analysis". *Journal of Clinical Epidemiology*, 49(12), 1373–1379. DOI: 10.1016/S0895-4356(96)00236-3

**Pham, P., Sridharan, M., Esposito, M. & Lenarduzzi, V. (2025)** — "Descriptor: C++ Self-Admitted Technical Debt Dataset (CppSATD)". *IEEE Data Descriptions* (to appear). arXiv: 2505.01136

**Potdar, A. & Shihab, E. (2014)** — "An Exploratory Study on Self-Admitted Technical Debt". *Proceedings of the 2014 IEEE International Conference on Software Maintenance and Evolution (ICSME 2014)*, pp. 91–100. DOI: 10.1109/ICSME.2014.31

**Rantala, L., Mäntylä, M. & Lenarduzzi, V. (2020)** — "Prevalence, Contents and Automatic Detection of KL-SATD". *IEEE 20th International Working Conference on Source Code Analysis and Manipulation (SCAM 2020)*. arXiv: 2008.05159

**Ren, X., Xing, Z., Xia, X., Lo, D., Wang, X. & Grundy, J. (2019)** — "Neural network-based detection of self-admitted technical debt: From performance to explainability". *ACM Transactions on Software Engineering and Methodology*, 28(3). DOI: 10.1145/3340544

**Sridharan, M., Mäntylä, M. & Rantala, L. (2025)** — "Detection, Classification and Prevalence of Self-Admitted Aging Debt". arXiv: 2504.17428 *(preprint)*

**Sutoyo, E., Avgeriou, P. & Capiluppi, A. (2024)** — "Deep Learning and Data Augmentation for Detecting Self-Admitted Technical Debt". arXiv: 2410.15804

**Wongpakaran, N., Wongpakaran, T., Wedding, D. & Gwet, K.L. (2013)** — "A comparison of Cohen's Kappa and Gwet's AC1 when calculating inter-rater reliability coefficients: a study conducted with personality disorder samples". *Psychiatry Research*, 209(3), 241–245. DOI: 10.1016/j.psychres.2013.07.002

**Xavier, L., Ferreira, F., Brito, R. & Valente, M.T. (2020)** — "Beyond the Code: Mining Self-Admitted Technical Debt in Issue Tracker Systems". *Proceedings of the 17th International Conference on Mining Software Repositories (MSR 2020)*, pp. 137–146. DOI: 10.1145/3379597.3387459 · arXiv: 2003.09418

**Zampetti, F., Serebrenik, A. & Di Penta, M. (2018)** — "Was Self-Admitted Technical Debt Removal a Real Removal? An In-Depth Perspective". *15th IEEE/ACM International Conference on Mining Software Repositories (MSR 2018)*, pp. 526–536. DOI: 10.1145/3196398.3196423