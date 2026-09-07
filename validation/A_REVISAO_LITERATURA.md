# Agente A — Revisão de Literatura: benchmark de validação e anotação

**Mandato:** Seção 3 do `PLANO_VALIDACAO_COWORK.md` (Agente A). **Data:** 2026-07-27.
**Escopo:** benchmark para calibrar o esforço humano de validação do dataset UBW — **não** é
revisão sistemática. Reaproveita a literatura já citada em `plano.md`, `ANNOTATION_GUIDELINE.md`
e `RESULTADOS_*`; verificações externas via busca web estão marcadas. Números não confirmados
estão explicitamente marcados como **a confirmar** — nenhum número foi inventado.

---

## 1. Trilha 1 — Como os trabalhos de SATD validam coleta e anotam

| Estudo | Anotadores | Amostra / desenho | Métrica de concordância | Calibração / protocolo |
|---|---|---|---|---|
| Potdar & Shihab (2014, ICSME) | 1 (primeiro autor) na leitura principal | Leitura manual de comentários de 4 projetos para derivar os 62 padrões lexicais | Nenhuma métrica formal reportada (**a confirmar** no original) | Nenhum protocolo formal; é o baseline histórico que o campo depois corrigiu |
| Maldonado & Shihab (2015, MTD) | 1 anotador principal + 2º anotador em subamostra | 33.093 comentários lidos; subamostra estatisticamente significativa para confiabilidade (tamanho exato **a confirmar**; ~95%/5%) | Cohen's κ ≈ **+0,81** (valor consolidado em Maldonado et al., 2017, TSE; **a confirmar** se o MTD'15 reporta o mesmo número) | Leitura integral por 1 pessoa; 2º anotador só valida — desenho mais fraco que o do UBW |
| Bavota & Russo (2016, MSR) | 2 autores | Amostra de validação manual no padrão 95% confiança / ±5% (o plano cita ~385; com correção de população finita o número cai para ~366 — valor exato **a confirmar**) | Cohen's κ (valor exato **a confirmar**) | Resolução de divergências por discussão; é a âncora do tamanho de amostra do plano UBW |
| Zampetti, Serebrenik & Di Penta (2018, MSR) | Anotação manual pelos autores (nº exato **a confirmar**) | 5 projetos Java; análise em profundidade de remoções de SATD | — (estudo qualitativo de diffs) | **Confirmado via web:** 20–50% das remoções de SATD são acidentais (o comentário some porque a classe/método/arquivo inteiro foi removido); só ~8% das remoções são reconhecidas na mensagem de commit. Distinguem remoção real de acidental **inspecionando o diff**: mudança dirigida ao código anotado vs. deleção em bloco. É exatamente a regra que o UBW já implementa (deleção de arquivo/arquivamento → censura, não evento) |
| Li, Soliman & Avgeriou (2023, EMSE 28(3)) | 2 anotadores (primeiros autores) nas partes anotadas manualmente | 4 fontes (código, commit, issue, PR); combina datasets existentes + anotação própria de commits/PRs; em subanálise com amostragem estratificada de pares reportam κ = +0,81 ("almost perfect") — **a confirmar** se esse κ se aplica também ao dataset principal | Cohen's κ | Anotação independente + resolução de conflitos; F1 médio de detecção 0,611 — mostra que mesmo o estado da arte automático erra bastante, reforçando o humano como ground truth |
| SATDAUG — Sutoyo, Avgeriou & Capiluppi (MSR'24, arXiv 2403.07690) | **Nenhum anotador novo** | Dataset balanceado por *data augmentation* sobre o multi-fonte de Li et al. | Herda os rótulos originais | Relevância para o UBW: evidencia que o desbalanceamento de classes é o problema central dos corpora SATD — mesma motivação do AC1 em paralelo e da sobre-amostragem da Categoria C |
| Awon (2024, University of Victoria) | 2+ anotadores com calibração | 28.680 comentários de código em 9 repositórios de software científico; tese sobre *Self-Admitted Scientific Debt* | Cohen's κ geral **0,926** (0,843–0,960 por artefato, conforme já citado no plano; confirmado via web como "almost perfect" nos conjuntos de calibração) | **Calibração de 50 itens por tipo de artefato** antes da anotação plena — protocolo que o guideline UBW já adota. Nota de citação: a fonte web indica **tese de doutorado (UVic)**, não dissertação de mestrado como está em `plano.md` — corrigir a citação (a confirmar no documento original) |
| Multi-artifact scientific software (arXiv 2601.10850, 2026) | 2 anotadores (autores) | 50 amostras não rotuladas **por tipo de artefato** (4 tipos) rotuladas independentemente na calibração | Cohen's κ, "almost perfect" em todos os conjuntos de calibração | Confirma que o desenho "50 itens/artefato + κ por artefato" é o padrão emergente em SATD multi-artefato — idêntico ao da Seção 3 do guideline UBW |
| SLR — Sutoyo & Capiluppi (arXiv 2312.15020) | — | Revisão de uma década (2014–2024) de abordagens de detecção de SATD, 6 bases | — | **Confirma a lacuna:** a revisão organiza o campo por tipos de dívida (design, requirement, test, documentation...) e por técnica (NLP → ML/DL → transformers). Dentro do escopo coberto, **nenhum trabalho isola "resignação funcional" como construto medido**, nem reporta precisão de detecção desse construto isoladamente — o UBW é, até onde a SLR alcança, o primeiro a fazê-lo |

**Síntese da Trilha 1.** O protocolo canônico do campo é: **2 anotadores** (quase sempre os
próprios autores), amostra no padrão **95%/±5% (~366–385 itens)**, **κ de Cohen** com limiar
de Landis & Koch, **rodada de calibração com discussão** e desempate por consenso ou terceiro
anotador. O UBW já está nesse padrão ou acima dele (AC1 em paralelo, precisão léxica separada
da precisão do pipeline, negativos adversariais no guideline — nenhum dos estudos acima faz
essas três coisas). As lacunas reais estão em detalhes operacionais (Seção 4).

---

## 2. Trilha 2 — Fora de SATD

### 2.1 Confiabilidade inter-avaliador
- **Landis & Koch (1977):** origem da escala usada no plano (0,61–0,80 substancial; >0,80
  quase perfeito). Vale registrar na dissertação que os próprios autores chamam os cortes de
  arbitrários — o limiar 0,61 é convenção da área, não teorema.
- **Gwet (2008) + Wongpakaran et al. (2013):** o paradoxo do κ — com prevalência muito
  desbalanceada, κ pode sair baixo mesmo com concordância observada altíssima, porque o
  p_e explode. O dataset UBW é o caso típico: se a precisão do léxico for alta (ex.: >85% dos
  candidatos são UBW), a classe `is_ubw=False` fica rara e o κ binário pode despencar sem que
  a concordância real seja ruim. **Por isso o AC1 em paralelo não é ornamento: é a proteção
  contra rejeitar uma anotação boa por artefato estatístico.** Prática recomendada (Wongpakaran):
  reportar sempre a tríade *concordância bruta (%) + prevalência das classes + κ + AC1*, nunca κ
  sozinho. O script 03 hoje reporta κ e AC1; falta a concordância bruta e a prevalência por
  recorte (ajuste pequeno, ver Seção 5).
- Interpretação de divergência κ vs. AC1 (decisão própria, para registrar no relatório de
  concordância): κ baixo + AC1 alto + concordância bruta alta ⇒ paradoxo de prevalência,
  anotação aceitável com justificativa; κ e AC1 ambos baixos ⇒ problema real de guideline/construto.

### 2.2 Boas práticas de anotação em estudos MSR
- **Guideline com exemplos positivos e negativos + regras de desempate:** o
  `ANNOTATION_GUIDELINE.md` já cumpre o estado da arte (condições operacionais, near-misses
  por artefato, precedência B > A > C, papel do 3º anotador fora do κ).
- **Calibração antes da anotação plena:** padrão confirmado (Awon; arXiv 2601.10850; o próprio
  plano). Detalhe operacional que a literatura pressupõe mas o plano não explicita: **os itens
  de calibração não podem entrar na amostra usada para o κ final** — a discussão conjunta
  contamina a independência. O κ da calibração deve ser reportado separadamente, como métrica
  de "aquecimento".
- **Gold set:** prática de NLP/ML importada para MSR — conjunto pequeno, verificado à exaustão,
  usado como teste de regressão de qualquer mudança de léxico/prompt/modelo. Nenhum dos papers
  de SATD da Trilha 1 mantém um; o plano UBW já o prevê (agente B). Mantê-lo versionado no repo.
- **Amostragem:** Baltes & Ralph (2022, EMSE, *Sampling in Software Engineering Research*) —
  reportar frame amostral, técnica e limitações; sobre-amostragem desproporcional de estratos
  raros é legítima **desde que a estimativa global seja reponderada pelos pesos reais dos
  estratos** (o risco nº 4 do plano de validação já registra isso; formalizar no relatório do B).
- **Tamanho de amostra:** 385 vale para população >5.000 (round_3000 já tem 3.217 registros e a
  coleta segue; o consolidado A+B provavelmente passa de 5.000). Se o consolidado ficar menor,
  aplicar correção de população finita (o ~366 de Bavota & Russo é exatamente isso). Para
  estratos minúsculos (Categoria C), amostrar não faz sentido — ver P1 na Seção 5.

### 2.3 Análise temática para a survey de RQ3 (respostas abertas)
- **Braun & Clarke (2006):** as 6 fases da análise temática — familiarização, códigos iniciais,
  temas, revisão, definição, relato. É a âncora natural para codificar o campo aberto da survey.
- **Braun & Clarke (2019, análise temática *reflexiva*):** os autores **desaconselham** medir
  IRR/κ na variante reflexiva (o codificador é instrumento, não máquina de rotular). Isso cria
  uma bifurcação metodológica que precisa ser decidida **antes** da survey: (a) *codebook TA*
  com dois codificadores e κ/AC1 sobre um subconjunto (~20–25% das respostas), consistente com o
  resto do desenho UBW; ou (b) TA reflexiva sem κ, com trilha de auditoria (codebook versionado,
  memos). **Recomendação (decisão própria): (a)**, por coerência com o restante do protocolo e
  com o que o comitê de ética e os revisores de MSR esperam ver.

### 2.4 Anonimização, LGPD/GDPR e contato com desenvolvedores (alimenta o Agente D)
- **Gold & Krinke (2022, EMSE, *Ethics in the mining of software repositories*)** — referência
  central, confirmada via web: (i) MSR é pesquisa **com seres humanos** (dados de interação de
  desenvolvedores); (ii) minerar dados públicos de commit tende a ser lícito sob **legítimo
  interesse** (GDPR art. 6(1)(f); guidance da Linux Foundation citada no paper); (iii)
  **profiling** — analisar/predizer comportamento, desempenho ou confiabilidade de indivíduos —
  normalmente exige **consentimento explícito**, com direito de retirada. Consequência direta
  para o UBW: agregações por autor (ex.: "o autor X domina os stopgaps do repo Y", achado do
  round_800 §4) são aceitáveis como estatística de qualidade de dados, mas qualquer análise
  publicada centrada em indivíduos identificáveis muda a base legal.
- **Pseudonimização ≠ anonimização:** GDPR (Recital 26) e LGPD (Lei 13.709/2018, art. 13 §4º e
  art. 5º) tratam dado pseudonimizado como **dado pessoal** — o `author_hash` SHA-256 sem salt é
  reidentificável por qualquer um com a lista de logins do GitHub (o próprio schema.py já admite
  isso). Publicar o hash é publicar dado pessoal pseudonimizado: ou (a) declara-se isso
  explicitamente na documentação do dataset (prática comum na área; o dado de origem já é
  público), ou (b) usa-se HMAC com salt secreto, perdendo linkabilidade externa mas mantendo a
  interna (mesmo autor ⇒ mesmo pseudônimo dentro do dataset — suficiente para RQ3 e para a
  extensão humano-vs-IA do plano de validação §6).
- **Contato com desenvolvedores (survey RQ3):** base legal adequada é **consentimento** (LGPD
  art. 7º I; GDPR art. 6(1)(a)) no primeiro contato, com: identificação do pesquisador e da
  instituição, finalidade, opt-out imediato, não-insistência (máx. 1 lembrete é a norma tácita
  em surveys MSR), e retenção definida. No Brasil, pesquisa com seres humanos via survey
  normalmente requer apreciação por **CEP/Plataforma Brasil** (Resoluções CNS 466/2012 e
  510/2016 — pesquisa em ciências humanas e sociais); confirmar com o comitê da UFCG qual das
  duas resoluções enquadra o caso. E-mails coletados de commits podem ser usados para contato de
  pesquisa sob legítimo interesse segundo parte da prática da área, mas o caminho seguro (e o
  que Gold & Krinke recomendam) é tratar o contato como coleta com consentimento e submeter ao
  comitê **antes** de enviar qualquer e-mail.
- **PII em `body_text`:** trechos de issues/PRs podem conter nomes, e-mails e até tokens. O
  dataset publicável precisa de um passe de mascaramento (regex de e-mail/token + revisão da
  amostra anotada). Isso é do Agente D, mas a âncora é a mesma: minimização de dados (LGPD art.
  6º III; GDPR art. 5(1)(c)).

---

## 3. Tabela-síntese: o que o campo faz × o que o UBW já faz × lacuna/recomendação

| Dimensão | O que o campo faz | O que o UBW já faz | Lacuna / recomendação |
|---|---|---|---|
| **Nº de anotadores** | 2 (geralmente autores), desempate por consenso ou 3º anotador; Maldonado'15 usou 1+validador | Plano: mínimo 2 independentes + 3º para desempate, fora do κ (guideline §7.4) | Nenhuma lacuna de desenho. Operacional: recrutar/confirmar o 2º anotador **antes** de fechar a amostra; registrar perfil (experiência em dev) no relatório, como Awon faz |
| **Amostra** | 95%/±5% ⇒ ~366–385 (Bavota & Russo; Pham et al. 2025); estratificação simples | ~385 estratificada por categoria × artefato, com script pronto (`03 ... sample`) | (1) Congelar amostra só após consolidar fatias A+B (já no plano de validação); (2) correção de população finita se N < 5.000; (3) **Categoria C por censo, não amostra** — com 1–10 registros por rodada, amostrar C é inútil; anotar todos (P1) |
| **Métricas de concordância** | κ de Cohen quase universal; limiar 0,61 (Landis & Koch); AC1 é raro em SATD | κ + AC1 implementados, por tarefa (binária vs. categoria em TPs) e por artefato — acima do padrão do campo | Adicionar concordância bruta (%) e prevalência de classes a cada linha do relatório (Wongpakaran et al. 2013); registrar a regra de interpretação κ-baixo/AC1-alto (Seção 2.1) |
| **Calibração** | 50 itens por artefato + sessão de discussão (Awon; arXiv 2601.10850); reduz divergências ~30% (Maldonado & Shihab) | Guideline §3 já prescreve exatamente isso | Explicitar que os 200 itens de calibração (50×4) **não entram** na amostra do κ final; reportar o κ da calibração separadamente. Atenção ao custo: 200 de calibração + ~385 plenos + fila LLM ≈ 600+ itens/anotador — o censo de C e a fila de triagem podem ser sobrepostos à amostra para não duplicar esforço |
| **Gold set** | Praticamente inexistente nos papers de SATD; padrão em NLP | Previsto no plano de validação (agente B), ainda não construído | Construir a partir de: exemplos do guideline + itens de calibração pós-consenso + near-misses adversariais. Versionar no repo; usar como teste de regressão de léxico/prompt (qualquer mudança futura roda contra ele antes de re-anotar qualquer coisa) |
| **Triagem LLM** | Emergente; a maioria dos trabalhos usa ML supervisionado, não LLM-triagem; nenhum protocolo canônico de descarte | Fluxo completo implementado: incerto→humano, auditoria 15%, κ LLM-humano com descarte se < 0,61, fail-safe para "incerto" — **à frente do campo** | Documentar duas decisões na dissertação: (1) a binarização do rótulo LLM no κ (UBW-verdadeiro vs. resto — "incerto" conta como negativo nessa checagem); (2) o rótulo do LLM nunca é exibido ao anotador antes da decisão (já na spec do B). São escolhas defensáveis, mas precisam estar escritas |
| **Validade de remoção** | Zampetti et al. 2018: 20–50% das remoções são acidentais; distinção via inspeção do diff (mudança dirigida vs. deleção em bloco); ~8% reconhecidas em commit | Plano §4: deleção de arquivo/arquivamento ⇒ censura, não evento; operacionalização conservadora por desaparecimento textual | O desenho está alinhado; falta **auditar a implementação**: amostrar eventos `removed_at` de `code_comment` e verificar no diff se a remoção foi dirigida ou em bloco (tarefa já prevista para o Agente C). Reportar a taxa de remoção acidental encontrada e comparar com a faixa 20–50% de Zampetti como validação externa |
| **Anonimização / ética** | Gold & Krinke 2022: legítimo interesse para minerar; consentimento para profiling e contato; datasets SATD publicam texto bruto sem política explícita na maioria dos casos | Schema já separa campos brutos de `author_hash`; dois datasets (trabalho vs. publicável) previstos; salt em aberto | (1) Decidir salt: recomendação — HMAC com salt secreto guardado fora do repo (preserva linkabilidade interna p/ RQ3 e extensão humano-vs-IA; elimina reidentificação trivial); se optar por manter sem salt, **declarar pseudonimização** na ficha do dataset; (2) máscara de PII em `body_text` no export; (3) survey RQ3: consentimento + CEP/Plataforma Brasil (CNS 466/2012 ou 510/2016) antes de qualquer e-mail; máx. 1 lembrete |

---

## 4. Onde o UBW já está acima do benchmark (não mexer)

1. **Separar precisão léxica bruta da precisão do pipeline** (amostra pré-LLM) — nenhum estudo
   da Trilha 1 faz; é um diferencial metodológico a destacar na dissertação.
2. **AC1 em paralelo ao κ** — raro em SATD, correto para a prevalência esperada.
3. **Negativos adversariais no guideline e na amostra** — mede especificidade, não só precisão.
4. **κ da categoria restrito aos verdadeiros positivos** — evita inflar a concordância da
   taxonomia com os casos fáceis de `is_ubw=False`.
5. **Léxico congelado com CHANGELOG e aval do orientador** — disciplina que Potdar & Shihab
   (2014) e sucessores não tinham.

---

## 5. Lista priorizada de ajustes ao protocolo

| # | Ajuste | Âncora |
|---|---|---|
| **P1** | **Categoria C por censo:** anotar TODOS os registros C do consolidado (dezenas, não centenas) pelos dois anotadores, fora da alocação proporcional; reportar precisão de C com IC exato. A amostra proporcional daria 1–3 itens de C — estatisticamente inútil | Decisão própria, motivada pelos dados (C = 1/108, 3/931, 10/3.217); coerente com a sobre-amostragem já prevista no mandato do B |
| **P2** | **Congelar a amostra só após consolidar fatias A+B**; aplicar correção de população finita se o consolidado ficar < 5.000 | Já no plano de validação §5; Bavota & Russo (2016) |
| **P3** | **Excluir os itens de calibração da amostra do κ final** e reportar o κ de calibração à parte | Prática implícita em Awon (2024) e arXiv 2601.10850; explicitação = decisão própria |
| **P4** | **Adicionar concordância bruta (%) e prevalência por classe** ao `agreement_report` (script 03), e registrar a regra de interpretação κ×AC1 | Wongpakaran et al. (2013); Gwet (2008) |
| **P5** | **Gold set versionado** = exemplos do guideline + calibração pós-consenso + near-misses; teste de regressão obrigatório para qualquer mudança de léxico/prompt | Decisão própria (prática de NLP); já prevista no plano de validação §6 |
| **P6** | **Reponderar a precisão global pelos pesos reais dos estratos** ao reportar (a sobre-amostragem de C e ⚠ envieza a média crua) | Baltes & Ralph (2022); risco nº 4 do plano de validação |
| **P7** | **IC de precisão por expressão via intervalo de Wilson** (melhor que Wald para n pequeno e p extremo, exatamente o caso das expressões raras) | Decisão própria ancorada em estatística padrão (Brown, Cai & DasGupta, 2001 — *Interval Estimation for a Binomial Proportion*; **a confirmar** citação exata se for para a dissertação) |
| **P8** | **Auditoria de remoção acidental** (Agente C): amostrar eventos de remoção de `code_comment`, classificar dirigida vs. em bloco, comparar com a faixa 20–50% | Zampetti et al. (2018) — confirmado |
| **P9** | **RQ3: fixar codebook TA com 2 codificadores + κ/AC1 em ~20–25% das respostas** (não TA reflexiva sem IRR), decidido antes de desenhar o instrumento | Braun & Clarke (2006; 2019); escolha entre variantes = decisão própria |
| **P10** | **Ética antes de qualquer contato:** decisão de salt documentada, máscara de PII no export, submissão ao CEP antes do primeiro e-mail da survey | Gold & Krinke (2022); LGPD 13.709/2018; GDPR Recital 26; CNS 466/2012–510/2016 |
| P11 | Corrigir a citação de Awon (2024) em `plano.md`: fonte web indica **tese de doutorado (University of Victoria)**, não dissertação de mestrado (**a confirmar** no documento original antes de corrigir) | Verificação desta revisão |

---

## 6. Insumos para B, C e D

### Agente B — Auditor de Falsos Positivos
- **Categoria C entra por censo** (P1); a alocação proporcional do `sample` vale para A e B; as
  expressões ⚠ restantes (`stopgap`) merecem estrato mínimo próprio (≥ 30 itens se houver).
- **Calibração de 50 itens/artefato fora da amostra do κ** (P3); planejar o orçamento humano
  total: ~200 calibração + ~385 plenos + censo C + fila LLM — sobrepor conjuntos onde possível
  para não passar de ~600 itens/anotador.
- **Relatório de concordância:** acrescentar % bruta e prevalência (P4); reportar κ binário e κ
  de categoria (TPs) separados, por artefato — o script 03 já quebra assim.
- **Precisão por expressão com IC de Wilson (P7), reponderada pelos estratos (P6)**; comparar a
  precisão medida com as estimativas informais da mineração (`LEXICO.md`) como sanity check.
- **Gold set (P5):** origem = guideline + calibração consensuada + near-misses adversariais;
  formato versionado no repo; nenhum item do gold set pode ser usado como few-shot no prompt do LLM.
- Nunca exibir `llm_label`/`llm_rationale` ao anotador antes da decisão; documentar a
  binarização do κ LLM-humano ("incerto" ⇒ negativo nessa checagem).

### Agente C — Auditor de Mineração
- **Auditoria Zampetti (P8):** amostrar ~50–100 eventos `is_censored=0` de `code_comment`,
  classificar a remoção como dirigida (diff toca o trecho anotado) vs. em bloco
  (arquivo/método deletado); esperado ficar fora/abaixo da faixa de 20–50% de remoções
  acidentais *contadas como evento* — se estiver dentro, a censura não está funcionando.
- Verificar que a purga de contaminação (dedup de `body_text`, `search_index.js`, `.min.*`,
  quebra-de-linha em `expression_in_text`) segura no consolidado A+B — os bugs já corrigidos
  (round_800 §2.6, round_3000 §2) são os casos de teste naturais.
- Checar concentração por autor (caso `ableplayer`/stopgap): reportar nº de registros por
  `author_hash` por repo; alimenta a decisão de normalização estatística, não é exclusão.
- Bots: o filtro atual é por login; procurar bots que escapam (`*-ci`, `*-automation`, e-mail
  `noreply` sem sufixo `[bot]`) — quantificar antes de propor política.
- Sanidade temporal: `time_to_event_days` < 0 ou nulo com `is_censored=0`; `removed_at` <
  `created_at`; commits sempre censurados por construção.

### Agente D — Anonimização & Ética
- **Base legal dupla:** mineração de dados públicos ⇒ legítimo interesse (Gold & Krinke 2022;
  LGPD art. 7º IX / GDPR art. 6(1)(f)); contato para survey ⇒ **consentimento** (LGPD art. 7º I),
  com CEP/Plataforma Brasil (CNS 466/2012 ou 510/2016 — confirmar enquadramento com a UFCG)
  **antes** do primeiro e-mail.
- **`author_hash` sem salt é pseudonimização, não anonimização** (GDPR Recital 26; LGPD art. 13
  §4º): recomendação — HMAC com salt secreto mantido fora do repositório (preserva linkabilidade
  interna para RQ3 e para a extensão humano-vs-IA; mata a reidentificação por dicionário).
  Alternativa aceitável: manter sem salt e declarar pseudonimização na ficha do dataset.
- **Dois datasets:** publicável sem `author_name/login/email` E com máscara de PII em
  `body_text` (regex de e-mail/token + revisão manual da amostra anotada); o de trabalho nunca
  sai da máquina/da equipe.
- **Profiling é a linha vermelha:** análises publicadas não podem caracterizar indivíduos
  identificáveis (ex.: ranking de autores por UBW); agregações por repositório/categoria são o
  formato seguro.
- Norma de contato: identificação institucional, finalidade, opt-out, no máximo 1 lembrete,
  registro de quem pediu remoção (o pedido vale também para o dataset de trabalho).

---

## Referências verificadas nesta revisão (além das já listadas em `plano.md` §10)

- Zampetti, Serebrenik & Di Penta (2018), MSR'18 — [ACM DL](https://dl.acm.org/doi/10.1145/3196398.3196423) · [TU/e](https://research.tue.nl/en/publications/was-self-admitted-technical-debt-removal-a-real-removal-an-in-dep/)
- Li, Soliman & Avgeriou (2023), EMSE 28(3) — [Springer](https://link.springer.com/article/10.1007/s10664-023-10297-9) · [arXiv 2202.02387](https://arxiv.org/abs/2202.02387)
- Sutoyo & Capiluppi — SLR de detecção de SATD — [arXiv 2312.15020](https://arxiv.org/abs/2312.15020)
- SATDAUG (MSR'24) — [arXiv 2403.07690](https://arxiv.org/pdf/2403.07690)
- Multi-Artifact SATD in Scientific Software — [arXiv 2601.10850](https://arxiv.org/abs/2601.10850)
- Awon (2024), tese UVic — [DSpace UVic](https://dspace.library.uvic.ca/bitstreams/862ca44f-6240-440e-95a9-023f14eb359c/download)
- Trabalho correlato adjacente (priorização/sentimento/propagação multi-artefato) — [arXiv 2603.15883](https://arxiv.org/abs/2603.15883) / [PEARC'26](https://dl.acm.org/doi/10.1145/3785462.3815801)
- Gold & Krinke (2022), EMSE — [Springer](https://link.springer.com/article/10.1007/s10664-021-10057-7) · [PDF UCL](http://www0.cs.ucl.ac.uk/staff/j.krinke/publications/emse22.pdf)
