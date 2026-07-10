# Léxico UBW — Expressões e Padrões em Uso

Este documento consolida **todas** as expressões e padrões usados no pipeline, em dois níveis distintos:

1. **Léxico oficial** (`ubw/lexicon.py`): fechado, usado na coleta real do dataset (`scripts/02_collect_multiartifact.py`). Qualquer alteração exige aval do orientador e fica registrada em CHANGELOG.
2. **Padrões exploratórios** (`ubw/patterns.py`): usados só na mineração (`scripts/04_pattern_mining.py`) para descobrir candidatos a novas expressões — nunca tocam o dataset coletado nem o léxico oficial diretamente.

Última atualização: 2026-07-08.

---

## 1. Léxico oficial (25 expressões ativas)

### Categoria A — Julgamento estético e hacks explícitos (menor risco de FP)

| Expressão | Origem |
|---|---|
| `ugly but it works` | Original (plano, Seção 3.2) |
| `ugly but works` | Original |
| `dirty hack` | Original |
| `this is a hack` | Original |
| `hacky but works` | Original |
| `horrible but works` | Original |
| `terrible but works` | Original |
| `messy but works` | Original |
| `ugly hack` | **Promovida** 2026-07-03 (mineração: 8 candidatos, ~7-8 TP) |

### Categoria B — Workarounds e urgência (risco intermediário)

| Expressão | Origem |
|---|---|
| `ugly workaround` | Original |
| `dirty workaround` | Original |
| `quick and dirty` | Original |
| `crude but it works` | Original |
| `not pretty but it works` | Original |
| `band-aid fix` | Original |
| `duct tape fix` | Original |
| `temporary fix` | **Promovida** 2026-07-03 (mineração: 23 candidatos, todos TP aparentes — sozinha já passou do mínimo de 20 exigido pela Seção 3.1) |
| `temp fix` | **Promovida** 2026-07-03 (mineração: 6 candidatos, 6 TP) |
| `stopgap` ⚠️ | **Promovida** 2026-07-03 (mineração: 4/4 TP após filtro de path — ver Seção 3 abaixo). Palavra única, sensível a path/nome de arquivo |
| `workaround for now` | **Promovida** 2026-07-03 (mineração: 1/1 TP; amostra pequena, mas FP improvável por construção) |

### Categoria C — Resignação funcional e incerteza (maior risco de FP)

| Expressão | Origem |
|---|---|
| `not ideal but it works` | Original |
| `not elegant but works` | Original |
| `ugly solution but` | Original |
| `ugly code but` | Original |
| `hope everything will work` | Original |

> Categoria C é sistematicamente rara nos dados coletados (1-3 registros por rodada, mesmo em centenas de repositórios) — achado consistente entre rodadas, tratado como característica real do fenômeno, não falha de amostragem.

### Removidas do léxico (CHANGELOG 2026-07-01)

| Expressão | Motivo da remoção |
|---|---|
| `magic number` | 0/10 verdadeiro positivo em amostra manual (54 candidatos no piloto de 140 repos); jargão técnico legítimo (bytes mágicos, IDs de protocolo, fast inverse square root) ou commits de **remoção** de magic number (sentido oposto a UBW) |
| `don't touch` | 0/12 verdadeiro positivo; comentário funcional ou diretiva de tooling ("auto-gerado, não tocar"), nunca admissão de medo/incerteza |

Decisão do orientador (Prof. João Arthur Brunet Monteiro), 2026-07-01, com base em `RESULTADOS_PILOTO.md` (Seção 7). Juntas, essas duas respondiam por 66% dos registros coletados na rodada 2 do piloto.

---

## 2. Filtros de precisão aplicados a TODO o léxico oficial

Nenhuma expressão do léxico é aceita "crua" — todo candidato passa por estes filtros antes de virar registro:

| Filtro | O que faz | Por quê |
|---|---|---|
| `expression_in_text()` | Exige a frase literalmente presente no corpo do artefato (tolera pontuação/quebra de linha entre palavras, mas não stemming, e não casa através de uma quebra de linha) | A busca por frase da GitHub Search API faz stemming ("temporary fix" casava com "temporarily fix") e às vezes a frase indexada nem está no corpo retornado (changelog truncado de dependabot) |
| Descarte de autor bot | Remove PRs/issues/commits de `dependabot[bot]`, `renovate[bot]`, etc. | Essas admissões são do autor da dependência de terceiros, não do time do repositório |
| `is_vendored_path()` | Exclui comentários de código dentro de `vendor/`, `node_modules/`, diretórios com sufixo de versão (`rocksdb-8.1.1/`), etc. | Achado do piloto: 73% dos matches de um repo vinham de uma lib vendorizada — não é SATD do time |
| `looks_like_comment()` | Exige que o match esteja de fato num comentário de código (não string literal/fixture de teste) | Heurística por linguagem (token de comentário de linha/bloco) |
| `match_is_path_only()` | Para expressões de **1 palavra só** (hoje: `stopgap`), descarta se TODAS as ocorrências estiverem em contexto de path/nome de arquivo (ex: `/Tools/stopGap/gClient.py`) | "stopgap" batia dentro de nomes de arquivo; frases com espaço não têm esse problema |

---

## 3. Expressão sensível a path

```python
PATH_SENSITIVE_EXPRESSIONS = {"stopgap"}
```

Qualquer expressão futura de uma palavra só entra automaticamente nesse conjunto (é calculado dinamicamente a partir do léxico, não é uma lista mantida à mão).

---

## 4. Padrões estruturais exploratórios (`ubw/patterns.py`)

Não são frases fixas — são regex que capturam uma **estrutura sintática**, usados só para descobrir candidatos novos via mineração. Cada padrão tem 3 formas: `git_ere` (filtro frouxo via `git grep -E`), `python_re` (filtro fino com `\b`) e `api_keywords` (para alargar a query da Search API, que não aceita regex).

| Padrão | Estrutura | Status (última medição: 50 repos, 2026-07-03) |
|---|---|---|
| `but_works` | `<adjetivo de qualidade> ... but ... works` (ex: "ugly but it works", "janky but it works") | 2 candidatos, ambos TP — incluiu a descoberta orgânica de **"janky"** (fora do léxico oficial, em observação) |
| `concessive_works` | `although/though/despite ... works` | 0 hits |
| `but_passes_tests` | `but ... passes the tests/CI` | 0 hits |
| `concessive_passes_tests` | `although/despite ... passes the tests/CI` | 0 hits |

> Estes 4 padrões correspondem diretamente à sugestão do orientador ("works BUT / although/despite etc it works" e "feio mas passa nos testes / embora passe nos testes"). Uma nova rodada com amostra maior (100 repos do corpus canônico de 784) está em andamento — ver `data/pattern_mining_round800/`.

### `but_works`: termos que travam o padrão (`QUALITY_ADJECTIVES`)

A versão original de `but_works` (sem exigir um adjetivo antes de "but") gerou 61 candidatos com **0/12 verdadeiro positivo** em 20 repos — ruído do tipo "X funciona no Chrome mas não no Firefox" (relato de bug de compatibilidade, não resignação técnica). Refinado para exigir um destes termos logo antes de "but":

```
ugly, janky, hacky, messy, dirty, crude, brittle, fragile,
sloppy, kludgy, kludge, hackish, gross, nasty, clunky, jury-rigged
```

Curada a partir da literatura (Maldonado et al., 2017; Ren et al., 2019) + achado orgânico do próprio piloto ("janky").

### Candidatas literais testadas via mineração (`LITERAL_CANDIDATES`)

Frases fixas propostas, testadas pelo mesmo pipeline de mineração antes de entrarem (ou não) no léxico oficial:

| Frase | Categoria proposta | Status |
|---|---|---|
| `ugly hack` | A | **Promovida** ao léxico oficial |
| `temporary fix` | B | **Promovida** ao léxico oficial |
| `temp fix` | B | **Promovida** ao léxico oficial |
| `stopgap` | B | **Promovida** ao léxico oficial |
| `workaround for now` | B | **Promovida** ao léxico oficial |
| `kludge` | A | 0 hits — em observação |
| `stopgap fix` | B | 0 hits — subsumida por "stopgap" — em observação |
| `not the best solution but` | C | 0 hits — em observação |
| `i know this is bad but` | C | 0 hits — em observação |
| `not proud of this but` | C | 0 hits — em observação |

---

## 5. Filtros auxiliares da mineração exploratória

- **`looks_like_path_context()`** (reexportada de `ubw/lexicon.py`): mesma lógica de filtro de path usada no léxico oficial, aplicada às candidatas literais durante a mineração.
- **`extract_slots()`**: extrai o que aparece antes/depois de "but"/"works" numa janela de contexto — alimenta o relatório de frequência (`pattern_mining_frequency_report.json`) usado para propor novas frases literais.

---

## 6. Onde cada coisa está no código

| Arquivo | Papel |
|---|---|
| `ubw/lexicon.py` | Léxico oficial fechado (`UBW_LEXICON`), CHANGELOG, todos os filtros de precisão (`expression_in_text`, `match_is_path_only`, `is_vendored_path`, `looks_like_comment`) |
| `ubw/patterns.py` | Padrões estruturais e candidatas literais exploratórias (`PATTERN_TEMPLATES`), nunca usado na coleta oficial |
| `scripts/02_collect_multiartifact.py` | Coleta oficial — usa só `ubw/lexicon.py` |
| `scripts/04_pattern_mining.py` | Mineração exploratória — usa `ubw/patterns.py`, gera candidatos para revisão manual, nunca escreve no dataset oficial |
