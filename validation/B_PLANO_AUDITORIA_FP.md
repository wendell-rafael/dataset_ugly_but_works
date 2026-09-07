# Agente B — Auditoria de Falsos Positivos (Validade de Construto)

**Mandato:** Seção 3 (`Agente B`) do `PLANO_VALIDACAO_COWORK.md`, princípios da Seção 2, riscos da
Seção 5. **Insumos de entrada:** `validation/A_REVISAO_LITERATURA.md` (Seção "Insumos para B, C e
D"). **Data:** 2026-07-27. **Modo:** PREPARAÇÃO — `data/full_run/` não tem `COLLECTION_COMPLETE`
(a fatia A ainda coleta; a fatia B está em outra máquina). Nenhuma amostra oficial foi gerada,
nenhum batch definitivo foi enviado a anotador. Tudo abaixo está especificado, revisado por dry-run
mecânico e pronto para disparar quando `data/consolidated/` (ou equivalente) existir.

**O que este documento entrega:**
1. Gap analysis de `scripts/03_metrics_llm_triage.py` contra o plano + insumos do Agente A.
2. Spec de amostragem final (estratos, alocação, near-miss, reponderação).
3. Protocolo de batches (sem vazar `llm_label`).
4. Protocolo do gold set (com uma semente v0 já materializada).
5. Três specs delegáveis a modelo barato, cada uma com script pronto, testado por dry-run.

Três scripts novos foram escritos — **nenhuma linha de `03_metrics_llm_triage.py` foi alterada**:

| Arquivo | Papel |
|---|---|
| `scripts/03b_final_sampling.py` | Amostra final: censo C, sobre-amostragem por raridade, near-miss, correção de população finita, pesos de reponderação |
| `scripts/03c_generate_batches.py` | Batches por anotador sem vazar `llm_label`/estratégia de amostragem; resolução de desempate |
| `scripts/03d_precision_report.py` | Precisão por expressão/categoria/artefato com IC de Wilson, precisão global reponderada, especificidade sobre near-miss |

Todos os três foram rodados de ponta a ponta sobre o CSV parcial (`data/full_run/ubw_collected_full.csv`,
73.447 linhas, só fatia A, **sem** `COLLECTION_COMPLETE`) com saídas gravadas em `validation/sample_dryrun/`,
`validation/batches_dryrun/` e `validation/DRYRUN_precision_report/` — todas rotuladas
`calibracao_processo`, nenhuma delas é amostra oficial (ver Seção 6).

---

## 0. Achado crítico antes de tudo: o mandato cita expressões que já saíram do léxico

O mandato do orquestrador (`PLANO_VALIDACAO_COWORK.md`, Seção 3, Agente B) manda "sobre-amostrar a
categoria C e as expressões marcadas ⚠ (`magic number`, `don't touch`, `hope everything will
work`)". Conferindo `LEXICO.md` e `ubw/lexicon.py` (fonte de verdade da coleta real):

- `magic number` e `don't touch` foram **removidas do léxico oficial em 2026-07-01** (CHANGELOG.md,
  linha 194-200; `ubw/lexicon.py::REMOVED_EXPRESSIONS`) — 0/22 verdadeiros positivos combinados no
  piloto. `ubw/lexicon.py::HIGH_RISK_EXPRESSIONS` está **vazio** hoje; não há nenhuma expressão
  marcada ⚠ por precisão baixa no léxico ativo.
- No CSV coletado real (fatia A parcial, 73.447 linhas) não existe nenhum registro com essas duas
  expressões — confirmado por contagem direta. Não há nada para sobre-amostrar com esses nomes.
- `hope everything will work` continua ativa (Categoria C) e é, de fato, a mais rara do léxico
  inteiro no corpus atual: **14 candidatos** em 73.447 linhas.

**Consequência para este plano:** em vez de seguir literalmente uma lista de nomes que ficou
desatualizada, a Seção 2 abaixo generaliza a intenção do mandato (proteger contra expressões raras
e de alto risco) com uma regra **mecânica e auto-ajustável**: qualquer expressão em
`HIGH_RISK_EXPRESSIONS` (léxico) OU com contagem total abaixo de um limiar de raridade entra
automaticamente na sobre-amostragem — o que também pega casos que o mandato não previu, como
`terrible but works` (4 candidatos) e `horrible but works` (9 candidatos), ambas Categoria A, uma
categoria tida como "baixo risco" mas que tem expressões individualmente raríssimas. Isso é
implementado em `scripts/03b_final_sampling.py::watch_list_expressions()` e testado no dry-run
(Seção 6). Reportar esse achado ao orientador/orquestrador é parte da entrega — não é uma correção
silenciosa do próprio agente ao léxico (esse continua congelado; aqui só se corrige a leitura do
mandato de validação, não o léxico de coleta).

---

## 1. Gap analysis — `scripts/03_metrics_llm_triage.py` vs. plano + insumos de A

### 1.1 O que o script 03 já cobre (não refazer)

| Item | Onde | Avaliação |
|---|---|---|
| Cohen's κ e Gwet's AC1, implementados corretamente (fórmulas conferem com Landis & Koch / Gwet 2008) | `cohens_kappa()` L70-95, `gwets_ac1()` L98-128 | Sólido |
| κ e AC1 separados para `is_ubw` (binário) e `category_confirmed` **restrito aos TPs** (ambos anotadores marcaram `is_ubw=True`) | `agreement_report()` L169-229, especialmente L206-215 | **Já implementa exatamente o pedido do Risco/insight "κ por categoria, não só global" — não é gap, é o oposto: já está feito** |
| Quebra por `artifact_type` para as duas métricas | `agreement_report()` L198-215 | Sólido |
| Aviso automático quando κ de categoria < 0,61 | L219-227 | Sólido |
| Amostragem estratificada por categoria × artefato, proporcional, com piso de 1/estrato | `stratified_sample()` L234-288 | Correta para o caso geral; não trata os casos especiais (ver 1.2) |
| Pré-triagem LLM com fail-safe para "incerto", roteamento "incerto → obrigatório" + auditoria de 15% do resto | `run_llm_triage*`, `_apply_audit_sampling()` L473-501 | Sólido, à frente do padrão do campo (confirmado por A) |
| κ LLM-vs-humano com descarte automático se < 0,61 | `validate_llm_against_human()` L615-633 | Sólido |
| Checkpoint/retomada tolerante a falha na triagem LLM | `run_llm_triage_incremental()` L544-612 | Sólido, não é escopo de B mas não atrapalha |

### 1.2 O que falta (gaps) e a proposta concreta para cada um

Nenhuma proposta abaixo altera `03_metrics_llm_triage.py`. Todas viraram função em
`03b_final_sampling.py` (importa `stratified_sample` de 03, não duplica) ou em `03d_precision_report.py`
(importa `agreement_report` de 03).

| # | Gap | Por que é um gap | Proposta |
|---|---|---|---|
| G1 | **Categoria C tratada como estrato comum** — `stratified_sample` alocaria a C uma fração proporcional de 385 (com N_C=256 na fatia parcial, isso daria ~1-2 itens), estatisticamente inútil para estimar precisão de C com IC aceitável | `stratified_sample()` não distingue C das demais; é genérica por design (correto para A/B) | `03b_final_sampling.py::build_all_pools()` separa C **antes** de chamar `stratified_sample` e faz censo (com teto de segurança — ver G7) |
| G2 | **Sem sobre-amostragem por raridade/risco de expressão** — o piso de "1 item/estrato" de `stratified_sample` é por (categoria, artefato), não por expressão; uma expressão rara dentro de um estrato grande pode sair zerada da amostra por puro acaso | Nenhuma lógica de piso por `matched_expression` existe hoje | `watch_list_expressions()` + `build_watch_pool()` em `03b`: piso configurável (default 30) para toda expressão rara (< limiar) ou marcada `HIGH_RISK_EXPRESSIONS`; ver Seção 0 sobre por que isso substitui a lista fixa do mandato |
| G3 | **Sem near-miss adversarial deliberado** — a amostra proporcional pega near-misses só por acaso, na proporção em que ocorrem naturalmente (baixa, já que são a minoria dos candidatos) | Não existe no script 03 | `build_near_miss_pool()` em `03b`: 6 heurísticas mecânicas (regex) derivadas 1-a-1 dos negativos do guideline (Seção 6) — string de teste/fixture, citação de terceiro, negação, remoção/undo, diretiva de tooling/gerado, uso não-técnico. Testado no dry-run: 17.575/70.k+ candidatos flagados por pelo menos uma heurística na fatia parcial (heurísticas são de alto recall/baixa precisão por construção — o julgamento fica com o humano) |
| G4 | **Sem IC de Wilson** — nenhuma estimativa de intervalo de confiança para precisão por expressão existe no script 03 (ele só faz κ/AC1, que são sobre concordância, não sobre precisão) | Não é escopo do script 03 hoje | `wilson_ci()` em `03d_precision_report.py`, fórmula fechada (Brown, Cai & DasGupta, 2001), usada em `precision_table()` |
| G5 | **Sem reponderação da precisão global** — se a amostra final tiver censo de C e piso de expressões raras, uma média crua de precisão sobre todos os itens anotados fica enviesada para C/raras (Risco 4 do plano de validação; insumo A, P6) | Não é escopo do script 03 | `reweighted_global_precision()` em `03d`: `p_hat = Σ_h w_h · p_hat_h`, pesos = tamanho real do estrato no corpus / N total (gravados por `03b::compute_stratum_weights()`); só usa estratos representativos (`main` + `census_c`), exclui `watch`/`near_miss` do denominador populacional |
| G6 | **Sem κ/precisão de calibração separados da amostra final** — o guideline (Seção 3) e o insumo de A (P3) exigem que os 200 itens de calibração (50×4 artefatos) fiquem fora do κ final, porque a independência foi quebrada pela discussão em grupo; o script 03 não distingue isso, ele calcularia κ sobre qualquer CSV de anotações que receber | Implícito no protocolo, não implementado em código | `03c_generate_batches.py` gera a calibração como pool **separada** desde a origem (nunca mistura com a amostra plena); `03d_precision_report.py::cmd_report` **descarta automaticamente** `sample_stratum == "calibration"` antes de chamar `agreement_report` |
| G7 | **Sem correção de população finita** (insumo A, P2; Bavota & Russo 2016 — ~366 em vez de 385 quando N<5.000) | Não implementado | `finite_population_correction()` em `03b`, aplicada tanto ao `main_n` quanto ao censo de C se este ultrapassar um teto de segurança (ver G-extra abaixo) |
| G8 | **Sem geração de batch de anotador** — o mandato do orquestrador (Seção 3) e o próprio texto desta tarefa mencionam um `annotation_template.csv` como se já existisse; **não existe**. `scripts/03_metrics_llm_triage.py` não tem nenhum subcomando que gere um CSV pronto para anotador a partir de candidatos — só gera a amostra "crua" (`sample`) ou o resultado da triagem LLM (`llm-triage`), nenhum dos dois no formato/forma que um anotador deveria receber (sem colunas de rótulo em branco, sem checagem de vazamento de `llm_label`) | Achado de gap, não estava documentado em lugar nenhum do repositório | `03c_generate_batches.py`: junta as pools de `03b`, remove defensivamente `llm_label`/`llm_rationale`/`requires_human_review`/`human_review_reason`/`sample_stratum`/`near_miss_flags`, randomiza ordem por anotador, adiciona colunas em branco (`is_ubw`, `category_confirmed`, `confidence`, `observacao`) |
| G9 | **Sem geração do batch de desempate (3º anotador)** — guideline Seção 7, regra 4 | Não implementado | `03c_generate_batches.py resolve`: compara dois CSVs preenchidos, identifica divergência binária OU divergência de categoria entre TPs, gera batch cego (sem os rótulos anteriores) |
| G10 | **Sem concordância bruta (%) nem prevalência ao lado do κ** (insumo A, P4; Wongpakaran et al. 2013 — nunca reportar κ sozinho) | `agreement_report()` retorna só κ/AC1/n, sem `p_o` bruto nem prevalência de classe | **Não corrigido nesta entrega** — fica registrado como pendência de baixo custo para quem rodar a unidade delegável (c) da Seção 5: ao invés de mexer em `agreement_report`, o relatório de precisão (`03d`) já reporta `n`/`true_positives`/`precision` por grupo, que dá a prevalência; falta só adicionar `p_o` (% bruta) ao lado do κ no `agreement_report.csv` final — 3 linhas de pós-processamento sobre a saída de `03d`/`03` combinadas, não requer novo script. Documentado aqui para não se perder |
| G11 | **Gold set inexistente** | Não existe em lugar nenhum do repo antes desta entrega | Seção 4 — semente v0 já materializada em `validation/gold_set/gold_set_v0_seed.csv` (14 itens dos exemplos do guideline) |

---

## 2. Spec de amostragem final

### 2.1 Estratos

| Estrato | Regra de alocação | Por quê |
|---|---|---|
| **Categoria C** (todos os artefatos) | **Censo** até um teto de segurança de 500 itens; acima disso, amostra do tamanho do teto **com correção de população finita** sobre o N real de C (nunca "silenciosamente vira amostra proporcional") | Categoria C é sistematicamente rara (256 na fatia A parcial — já mais que os "1-10/dezenas" observados em rodadas menores, insumo de A parcialmente desatualizado, ver nota abaixo) e é a de maior risco de FP (plano.md §3.2). Amostra proporcional dentro de 385 daria ~1-2 itens — inútil para IC |
| **Categoria A/B × 4 tipos de artefato** (8 estratos) | Amostra proporcional ao tamanho real de cada estrato, `total_n=385` (ou ajustado por FPC se N<5.000), piso de 1/estrato — **reusa `stratified_sample()` de 03 sem alterar** | Padrão da área (Bavota & Russo 2016; Pham et al. 2025), já implementado e testado |
| **Expressões-alvo (piso de raridade)** | Piso de 30 itens (ou censo se a expressão tiver ≤30 candidatos), aplicado a toda expressão em `HIGH_RISK_EXPRESSIONS` OU com contagem total < 50 no corpus, restrito a A/B (C já é censo) | Generaliza a intenção do mandato (Seção 0) de forma que sobrevive a mudanças futuras no léxico sem precisar editar este documento |
| **Near-miss adversarial** | Pool de ~100 itens, distribuído entre as 6 heurísticas (~17 cada), amostrado do que sobrar depois de C/watch/calibração | Mede especificidade, não precisão — não deve contaminar a estimativa populacional (por isso fica fora da reponderação global) |
| **Calibração** | 50 itens por tipo de artefato (200 total), sorteados do frame inteiro **antes** de qualquer outro corte, removidos do pool remanescente | Guideline §3; nenhum item aparece em duas pools ao mesmo tempo |

**Nota sobre a Categoria C ter crescido mais do que o esperado:** o insumo do Agente A (P1) foi
escrito com base em rodadas menores ("C = 1/108, 3/931, 10/3.217" — dezenas, não centenas). Com o
corpus real em 73.447 linhas (só fatia A, parcial), C já está em 256. É bem possível que, após
consolidar A+B, C passe de 500-600. Por isso o teto de segurança de 500 com FPC — em vez de
seguir cegamente "censo sempre", o script decide dinamicamente e **registra a decisão no
manifest**, nunca de forma silenciosa.

### 2.2 Near-miss adversarial: como identificar mecanicamente

Seis heurísticas (regex, `03b_final_sampling.py::NEAR_MISS_PATTERNS`), uma para cada padrão
negativo do guideline (Seção 6):

| Heurística | Padrão do guideline que ela mira | Regex (resumo) |
|---|---|---|
| `string_teste_fixture` | 6.1: expressão dentro de string testada por `assert` | `def test_`, `assert `, `pytest`, `fixture`, `mock` |
| `citacao_terceiro` | 6.1: "o revisor comentou que era 'a dirty hack'" | `said`, `commented`, `reviewer`, `reopened`, `reported`, `according to`, `called it` |
| `negacao` | Seção 4, condição 4 | `not a`, `isn't a`, `never a`, `no longer a` |
| `remocao_undo` | 6.2: "remove duct tape fix... root cause fixed" | `remove(d)?`, `deleted`, `delete this`, `root cause fixed`, `no longer needed` |
| `tooling_generated` | 6.3: "AUTO-GENERATED FILE. Don't touch" | `AUTO-GENERATED`, `DO NOT EDIT`, `codegen`, `generated by` |
| `nao_tecnico` | 6.3: onboarding/RH | `onboarding`, `process`, `workflow`, `roadmap`, `HR` |

Essas heurísticas são **de alto recall e baixa precisão por construção** — o dry-run (Seção 6)
mostrou 17.575 candidatos flagados numa amostra de 70 mil (≈25%), a maioria dos quais provavelmente
NÃO são near-miss de verdade (ex.: "remocao_undo" bate em qualquer menção à palavra "removed", que
pode aparecer dentro de um positivo genuíno). Isso é esperado e correto: a função da heurística é
**enriquecer o pool candidato**, não decidir — a decisão final continua 100% humana. O pool de
near-miss final (~100 itens) é sorteado desse conjunto flagado, distribuído entre as 6 heurísticas
para não deixar uma dominar.

### 2.3 Fórmula de reponderação da precisão global

```
p_hat_global = Σ_h  w_h · p_hat_h        (soma sobre os estratos h ∈ {A×artefato, B×artefato, C})

w_h = N_h / N        (N_h = tamanho real do estrato no corpus consolidado; N = corpus total A+B+C)
p_hat_h = precisão observada (proporção de is_ubw=True confirmado) dentro da amostra do estrato h
```

Implementada em `03d_precision_report.py::reweighted_global_precision()`. **Só usa os estratos
`main` (A/B proporcional) e `census_c`** — os pools `watch` (piso de raridade) e `near_miss`
(adversarial) são diagnósticos, não representativos da população, e por isso não entram no
denominador `N`. Se algum estrato ficar sem cobertura (não teve item anotado), o script avisa e
reporta a fração de peso populacional efetivamente coberta — nunca finge 100% de cobertura quando
não há.

### 2.4 Correção de população finita

```
n_ajustado = n / (1 + (n - 1) / N),   aplicada só quando N < 5.000
```

Aplicada tanto ao `n=385` da amostra principal quanto ao teto de censo de C, se este for acionado
(`finite_population_correction()` em `03b`). Na fatia A parcial (N=73.447), não é acionada —
`main_n_adjusted = 385` no manifest do dry-run confirma isso.

---

## 3. Protocolo de batches

### 3.1 Geração (sem vazar `llm_label`)

`03c_generate_batches.py build`:

1. Carrega as 5 pools de `03b` (`calibration`, `census_c`, `watch`, `near_miss`, `main`).
2. Concatena tudo, calcula `item_id` estável = `repo_full_name|artifact_type|artifact_id|matched_expression`
   (mesma lógica de chave já usada em `03_metrics_llm_triage.py::_candidate_key`).
3. Verifica que não há `item_id` duplicado entre pools (erro fatal se houver — sinal de bug na
   remoção incremental do pool remanescente em `03b`).
4. **Remove defensivamente** as colunas proibidas antes de gerar qualquer CSV de anotador:
   `llm_label`, `llm_rationale`, `requires_human_review`, `human_review_reason` (sinal do LLM) e
   `sample_stratum`, `near_miss_flags` (sinal da estratégia de amostragem — saber que um item foi
   escolhido a dedo como "provável near-miss" enviesaria o anotador). Isso é defensivo porque, na
   prática, as pools de `03b` já vêm de candidatos pré-LLM (Seção 5.1 do plano: a amostra de
   precisão é extraída ANTES da triagem LLM rodar) — mas o filtro roda mesmo assim, com `assert`
   final que quebra a execução se alguma coluna proibida escapar.
5. Campos que o anotador VÊ: `item_id`, `repo_full_name`, `artifact_type`, `matched_expression`,
   `category_ubw` (categoria léxica — **intencionalmente exibida**, porque o guideline usa
   explicitamente `matched_expression → category_ubw` como regra de desempate de categoria default,
   Seção 7 regra 1; não exibi-la obrigaria o anotador a adivinhar algo que o próprio protocolo diz
   para usar como referência), `body_text`, `created_at`, `url`, mais as colunas em branco
   `is_ubw`, `category_confirmed`, `confidence`, `observacao`.
6. Ordem **randomizada de forma independente por anotador** (seed distinto por `annotator_id`),
   para que não seja possível cruzar "item na posição N do anotador A" com "item na posição N do
   anotador B" e inferir algo sobre o outro rótulo antes de decidir.
7. Calibração e anotação plena saem em arquivos **separados** por anotador
   (`batch_{id}_calibracao_{label}.csv`, `batch_{id}_plena_{label}.csv`) — a plena nunca é
   split entre anotadores; cada anotador primário anota o conjunto inteiro de forma independente
   (guideline Seção 3, item 3: "de forma independente, sem consultar os outros anotadores").
8. Um arquivo interno **não entregável ao anotador** (`_internal_stratum_map_{label}.csv`) guarda
   `item_id → sample_stratum` (+ `near_miss_flags` quando aplicável), usado só depois pelo
   `03d_precision_report.py` para reponderação e especificidade.

### 3.2 Onde entram os itens de calibração, e por que ficam fora do κ final

Os 200 itens de calibração são sorteados do frame **inteiro**, antes de qualquer outro corte —
incluem uma mistura natural de itens fáceis, de C, e potencialmente de near-miss (não são
filtrados para isso, mas por vir do frame completo tendem a refletir a mesma distribuição de
dificuldade que o resto). Cada anotador primário anota a calibração de forma independente primeiro
(como qualquer outro batch), e **depois** disso acontece a sessão de discussão conjunta (fora do
escopo de código — é humana, Seção 3 do guideline). A partir daí:

- O rótulo de calibração **pós-discussão** (consenso) é um candidato natural para entrar no gold
  set (Seção 4) — é humano, verificado, com múltiplos olhos.
- Esse mesmo rótulo **nunca entra no cálculo de κ/AC1 final**, porque a independência entre
  anotadores foi quebrada pela discussão (insumo do Agente A, P3). `03d_precision_report.py`
  aplica isso automaticamente: qualquer linha com `sample_stratum == "calibration"` é descartada
  antes de chamar `agreement_report()`.

### 3.3 Desempate (3º anotador)

`03c_generate_batches.py resolve` recebe os dois CSVs de anotação plena já preenchidos, calcula:
- **divergência binária:** `is_ubw` diferente entre os dois anotadores;
- **divergência de categoria:** ambos marcaram `is_ubw=True` mas `category_confirmed` diferente
  (guideline Seção 7, regra 4).

Gera um batch cego para o 3º anotador — mesmas colunas visíveis de sempre, **sem** as colunas de
rótulo dos dois primeiros (`assert` no código garante isso). A decisão do 3º anotador é final para
aquele item no dataset, mas **não entra no κ/AC1 do par primário** (mesma regra do guideline).

---

## 4. Protocolo do gold set

### 4.1 Critério de entrada

Um item entra no gold set quando tem rótulo humano **verificado por mais de uma pessoa**, com uma
das três origens:

1. **Exemplos do guideline** (`ANNOTATION_GUIDELINE.md`, Seção 6) — já são, por construção,
   consensuados entre quem escreveu o guideline e o orientador que o aprovou. **14 itens**
   materializados agora em `validation/gold_set/gold_set_v0_seed.csv` (positivo/negativo para cada
   categoria A/B/C, incluindo os dois casos de `magic number`/`don't touch` — mantidos como teste
   conceitual da fronteira aceitação-vs-prevenção mesmo após a remoção dessas duas expressões do
   léxico ativo, ver nota na própria linha do CSV).
2. **Itens de calibração pós-consenso** (Seção 3.2) — adicionados depois da primeira rodada real de
   anotação, quando existir.
3. **Near-miss adversarial confirmado** — itens do pool `near_miss` cujo rótulo humano final
   (consenso ou desempate) confirma que era de fato um near-miss (`is_ubw=False` apesar de bater a
   heurística) ou, o caso mais informativo, confirma que a heurística errou (`is_ubw=True` apesar
   de bater a heurística — um "falso near-miss", ainda mais valioso para o gold set porque testa a
   fronteira de perto).

### 4.2 Versionamento

`validation/gold_set/gold_set_v{N}.csv` — cada versão é imutável depois de publicada; qualquer
adição vira `v{N+1}`. Colunas: `item_id`, `source` (`guideline`/`calibration`/`near_miss`),
`artifact_type`, `category_lexical_or_na`, `body_text_excerpt`, `is_ubw_gold`, `category_gold`,
`note`. A v0 (semente) já está em `validation/gold_set/gold_set_v0_seed.csv` com os 14 itens do
guideline — pronta para uso imediato, não depende do corpus consolidado.

**Regra dura (insumo do Agente A):** nenhum item do gold set pode ser usado como few-shot no prompt
da triagem LLM (`LLM_TRIAGE_USER_PROMPT_TEMPLATE` em `03_metrics_llm_triage.py` hoje é zero-shot —
checagem feita, não há violação atual; a regra existe para impedir contaminação se alguém decidir
adicionar few-shot no futuro).

### 4.3 Uso como teste de regressão

Qualquer mudança futura de léxico (após reaprovação do orientador — o léxico segue congelado),
prompt de triagem LLM, ou modelo de LLM usado na triagem deve rodar contra o gold set **antes** de
qualquer re-anotação em escala: gerar as previsões da nova configuração sobre os `item_id` do gold
set, comparar com `is_ubw_gold`/`category_gold`, reportar precisão/recall. Uma queda de precisão no
gold set é sinal de regressão e bloqueia o rollout da mudança até investigação — o gold set não
troca de versão para "passar" no teste; a mudança é revertida ou ajustada.

---

## 5. Specs delegáveis (modelo barato)

Três unidades fechadas, cada uma com entrada exata, comando, saída e critério de "pronto". Todas
já foram exercitadas por dry-run (Seção 6) — o que falta é só apontar para o corpus consolidado
oficial.

### (a) Rodar a amostragem sobre o consolidado

- **Entrada:** `data/consolidated/ubw_consolidated.csv` (ou caminho equivalente definido na
  consolidação A+B), com o schema de `ubw/schema.py::COLLECTION_SCHEMA_COLUMNS`.
- **Pré-condição:** `data/full_run/COLLECTION_COMPLETE` (fatia A) existe **e** a fatia B já foi
  mesclada/deduplicada (ver `validation/RELATORIO_QUALIDADE_DADOS.md`, achado de dedup
  cross-artefato do Agente C — rodar a dedup **antes** de amostrar, senão a amostra herda
  duplicatas).
- **Comando:**
  ```bash
  python scripts/03b_final_sampling.py build \
      --candidates data/consolidated/ubw_consolidated.csv \
      --label oficial --confirm-consolidated "SIM, A+B consolidados" \
      --out-dir validation/sample_final --seed 42
  ```
- **Formato de saída:** `validation/sample_final/sample_{calibration,census_c,watch,near_miss,main}_oficial.csv`,
  `sampling_weights_oficial.csv`, `sampling_manifest_oficial.json`.
- **Critério de "pronto"/verificador:**
  - o comando recusa rodar (`SystemExit`) sem `--confirm-consolidated` exato quando `--label oficial`
    — isso já é o primeiro verificador embutido;
  - `sampling_manifest_oficial.json` tem `census_c_is_full_census: true` OU, se `false`, o log
    explica por que (teto de segurança acionado) — checar manualmente essa linha;
  - soma dos tamanhos das 5 pools bate com o que está em `pool_sizes` do manifest;
  - `sampling_weights_oficial.csv` tem exatamente 9 linhas (8 estratos A/B × artefato + 1 `C|censo`)
    e a soma da coluna `weight` é 1,0 (± arredondamento).

### (b) Gerar os batches

- **Entrada:** as 5 pools de (a), mais a lista de IDs dos anotadores reais (ex.: `ana,bruno`).
- **Comando:**
  ```bash
  python scripts/03c_generate_batches.py build \
      --pools-dir validation/sample_final --label oficial \
      --annotators <id1>,<id2> --out-dir validation/batches_final --seed 42
  ```
- **Formato de saída:** `batch_{id}_calibracao_oficial.csv`, `batch_{id}_plena_oficial.csv` por
  anotador, `_internal_stratum_map_oficial.csv` (não entregar), `batches_manifest_oficial.json`.
- **Critério de "pronto"/verificador:**
  - `assert not (FORBIDDEN_COLUMNS & set(batch.columns))` já roda dentro do script — se passou sem
    exceção, não há vazamento de `llm_label` nem de `sample_stratum`;
  - checar manualmente que `header` de qualquer `batch_*.csv` NÃO contém `llm_label`, `llm_rationale`,
    `requires_human_review`, `human_review_reason`, `sample_stratum`, `near_miss_flags` (comando
    rápido: `head -1 batch_*.csv | grep -Ei "llm_|sample_stratum|near_miss"` deve retornar vazio);
  - os dois (ou mais) anotadores têm o **mesmo conjunto** de `item_id` na anotação plena (join por
    `item_id`, `set` igual), só a ordem das linhas difere.
- **Depois da anotação (não delegável — humano):** rodar
  `python scripts/03c_generate_batches.py resolve --annotator-a <csv_A> --annotator-b <csv_B> --out <csv_desempate>`
  se houver divergência, e coletar a decisão do 3º anotador antes da unidade (c).

### (c) Computar κ/AC1/precisões pós-anotação

- **Entrada:** um CSV longo único juntando as anotações preenchidas dos 2 (+1) anotadores, com
  colunas `item_id, artifact_type, matched_expression, category_ubw, annotator_id, is_ubw,
  category_confirmed, confidence`, junto (merge por `item_id`) com `_internal_stratum_map_oficial.csv`
  de (b) para trazer `sample_stratum` (e `near_miss_flags` se existir); mais
  `sampling_weights_oficial.csv` de (a).
- **Comando:**
  ```bash
  python scripts/03d_precision_report.py report \
      --annotations validation/annotations_long_final.csv \
      --weights validation/sample_final/sampling_weights_oficial.csv \
      --tiebreak-annotators <id_do_3o_anotador> \
      --out-dir validation/precision_report_final
  ```
- **Formato de saída:** `agreement_report.csv` (κ/AC1 — mesmo formato que `03_metrics_llm_triage.py
  metrics` já produzia), `resolved_labels.csv`, `precision_by_{expression,category,artifact_type}.csv`
  (com IC de Wilson), `precision_global_summary.txt`, `precision_global_detail.csv`,
  `specificity_near_miss.csv`.
- **Critério de "pronto"/verificador:**
  - `agreement_report.csv` não tem `n_items=0` em nenhuma linha do escopo `geral` (senão a junção
    com `_internal_stratum_map` falhou silenciosamente em algum item);
  - todo `precision.csv` gerado tem `wilson_ci_low <= precision <= wilson_ci_high` em toda linha
    (checagem de sanidade da fórmula);
  - **verificador forte, o gold set:** antes de aceitar o relatório como válido, rodar o mesmo
    `03d_precision_report.py` (ou uma comparação direta) sobre os `item_id` do gold set que também
    caíram na amostra oficial (se algum caiu) e conferir que o `resolved_labels.csv` bate com
    `is_ubw_gold`/`category_gold` — divergência aqui é sinal de erro no pipeline de resolução de
    rótulo, não do dataset;
  - se `agreement_report.csv` mostrar κ de `category_confirmed (TP), geral` < 0,61, o critério de
    "pronto" inclui **escalar para humano** (não é um erro de execução, é o alerta já embutido em
    `agreement_report()`, linha 219-227 de `03_metrics_llm_triage.py` — "a contribuição central do
    estudo fica fragilizada").

---

## 6. Dry-run realizado (evidência mecânica, NÃO é amostra oficial)

Rodado sobre `data/full_run/ubw_collected_full.csv` (73.447 linhas, só fatia A, sem
`COLLECTION_COMPLETE`), com `--label calibracao_processo` em todos os comandos — o guarda-corpo de
`--confirm-consolidated` bloqueou qualquer tentativa de rotular como `oficial`.

| Passo | Comando | Resultado |
|---|---|---|
| (a) amostragem | `03b_final_sampling.py build --label calibracao_processo` | `calibration=200`, `census_c=253` (censo integral, abaixo do teto de 500), `watch=98` (5 expressões de raridade: `crude but it works`, `duct tape fix`, `horrible but works`, `messy but works`, `terrible but works` — nenhuma delas é `magic number`/`don't touch`, confirmando a Seção 0), `near_miss=100`, `main=385`. `main_n_adjusted=385` (sem FPC, N>5.000) |
| (b) batches | `03c_generate_batches.py build --annotators ana,bruno` | 200 itens de calibração + 836 de anotação plena por anotador (836 = 253+98+100+385); header confere sem nenhuma coluna proibida |
| (c) precisão | `03d_precision_report.py report` sobre anotações **sintéticas** (preenchidas por um script aleatório só para validar que o pipeline não quebra — não são rótulos reais, não usar para nenhuma conclusão sobre o dataset) | Rodou de ponta a ponta sem erro: `agreement_report.csv`, `precision_by_*.csv`, `precision_global_summary.txt=0.9701` (número sem significado — dado sintético), `specificity_near_miss.csv`. Efeito colateral instrutivo: como o preenchimento sintético é quase aleatório, o κ binário geral saiu **0,0432 ("leve")** enquanto o AC1 saiu **0,6326** — uma ilustração ao vivo do paradoxo do κ em prevalência desbalanceada que justifica reportar os dois em paralelo (Gwet 2008; insumo do Agente A) |

Saídas em: `validation/sample_dryrun/`, `validation/batches_dryrun/`, `validation/DRYRUN_precision_report/`,
`validation/DRYRUN_synthetic_annotations_long.csv` (as anotações sintéticas usadas só para testar o
código) — todos com sufixo/label deixando claro que é calibração de processo.

---

## 7. O que fica pendente (depende só do consolidado existir)

1. Consolidar fatia A (aguardar `COLLECTION_COMPLETE`) + fatia B (mesclar do outro arquivo/máquina)
   — fora do escopo deste agente, é do orquestrador/Agente C.
2. Rodar dedup cross-artefato (achado do Agente C, `RELATORIO_QUALIDADE_DADOS.md`) **antes** da
   unidade delegável (a) — amostrar sobre um corpus com duplicatas infla artificialmente a
   contagem de alguns estratos.
3. Recrutar/confirmar o 2º anotador humano e o critério de desempate (3º) — decisão humana, fora de
   escopo de código.
4. Disparar as 3 unidades delegáveis da Seção 5, nessa ordem: (a) → (b) → anotação humana → (b)
   `resolve` se houver divergência → (c).
5. Item de baixo custo ainda em aberto (G10): adicionar % de concordância bruta e prevalência ao
   lado de κ/AC1 no relatório final — não bloqueia a validação, mas deve entrar antes do relatório
   ir para a dissertação (Wongpakaran et al., 2013).
6. Expandir o gold set (Seção 4) com itens de calibração pós-consenso e near-miss confirmados assim
   que a primeira rodada real de anotação terminar.
