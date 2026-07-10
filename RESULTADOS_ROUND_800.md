# UBW: Resultados da Rodada Intermediária (784 repositórios)

**Data de corte:** 2026-07-06 | **Corpus:** 784 repositórios canônicos (triados de uma amostra de 800 no SEART-GHS) | **Dataset:** `data/round_800/ubw_collected_full.csv`

Esta é a primeira rodada em escala real desde a consolidação final do pipeline (`RESULTADOS_FINAL.md`, 134 repositórios), usada como ponte de validação antes do corpus completo. Rodou com 4 tokens do GitHub em rotação (do usuário + 3 colaboradores, fine-grained, somente leitura em repositórios públicos) e 8 workers paralelos para `code_comment`.

## 1. Resumo executivo

**931 registros em 244 repositórios** (número final, após a purga de falsos positivos descrita na Seção 3 — a coleta bruta original tinha 984 registros em 249 repos). Mesmo depois da purga, ainda é quase 9x o volume da rodada de 134 repos. As expressões promovidas pela mineração de padrões seguem dominando o dataset, confirmando o achado da rodada anterior em escala maior.

O subconjunto de sobrevivência (RQ2, threshold ≥3 ocorrências) saltou de **7 para 66 repositórios** (653 registros) — o primeiro volume realmente utilizável para a análise de sobrevivência do plano.

**Por artefato:** code_comment 439, commit_message 277, issue_body 118, pr_body 97.
**Por categoria:** B 607, A 321, C 3.

## 2. Uso de recursos (armazenamento, memória, tempo)

Esta seção documenta o comportamento operacional da rodada, incluindo um bug real encontrado e corrigido durante a execução.

### 2.1 Armazenamento

| Item | Tamanho |
|---|---|
| `ubw_collected_full.csv` | 1,1 MB |
| `ubw_collected_rq2_subset.csv` | 796 KB |
| `collect_run.log` | 268 KB |
| `collection_state.json` (checkpoint) | 196 KB |
| **Clones locais durante a execução (pico)** | **~15 GB órfãos** (bug, ver 2.3) |
| **Clones locais após a coleta (correto)** | **0 B** (todos apagados por repositório, como projetado) |

O comportamento esperado — e confirmado — é que os dados persistentes (CSV, checkpoint, log) somam poucos megabytes mesmo em centenas de repositórios; os clones git são transitórios e não deveriam se acumular. Isso só falhou no cenário de erro descrito em 2.3.

### 2.2 Memória e CPU

A máquina (12 núcleos, 31GB RAM) nunca chegou perto de ser o gargalo: durante a execução, uso de memória ficou bem abaixo da capacidade (a maior parte da RAM ficada ocupada é cache de disco do Linux, não memória realmente reservada por processos). Não havia instrumentação de monitoramento contínuo de pico de memória durante a execução (só o estado do sistema logo depois foi capturado); se isso for útil para rodadas futuras, dá para adicionar um logger de `psutil` no script.

O verdadeiro limitador identificado foi outro: **`git clone` roda sem autenticação de token** (usa a URL pública HTTPS), então não se beneficia da rotação de 4 tokens — o teto prático de paralelismo em `--parallel-workers` é a tolerância do GitHub a clones concorrentes por IP, não CPU/RAM da máquina.

### 2.3 Bug encontrado: timeout de clone deixava 15GB de lixo em disco

**Sintoma:** ao investigar o uso de armazenamento pós-coleta, `data/round_800/clones/` tinha 15GB em 7 diretórios, quando o esperado era ~0 (cada worker apaga o próprio clone ao terminar).

**Causa raiz (dupla):**
1. Sete repositórios (`55gms/55GMS`, `7aGiven/Phigros_Resource`, `0auBSQ/OpenTaiko`, `Abdess/retrobios`, `abhisheks008/DL-Simplified`, `abpframework/abp`, `Aceship/AN-EN-Tags`) têm muito asset binário no histórico (jogos de ritmo com áudio/imagem, coleções de projetos de ML) e estouravam os 900s de timeout de clone. O clone é sempre completo (sem `--depth`) por necessidade metodológica — a Seção 4 do plano exige o histórico inteiro para achar o commit de introdução do comentário, que pode ser muito mais antigo que os últimos N commits; um clone raso quebraria o cálculo de `time_to_event`.
2. `subprocess.run(..., timeout=900)` lança `subprocess.TimeoutExpired`, que **não estava sendo capturada** dentro de `clone_repo()` (`scripts/02_collect_multiartifact.py`). A exceção escapava antes do `try/finally` do chamador (`process_repo_code_comment`), que é onde a limpeza do diretório de clone acontece — resultado: (a) a lógica de retry nunca rodava para esse tipo de falha, (b) o diretório parcial nunca era apagado, e (c) numa retomada futura, `clone_repo()` reaproveitaria cegamente esse diretório corrompido (`if dest_dir.exists(): reutiliza`, sem checar integridade).

**Correção aplicada** (`scripts/02_collect_multiartifact.py`):
- `subprocess.TimeoutExpired` agora é capturada explicitamente, limpa o diretório parcial e desiste sem gastar as tentativas de retry (retry não ajudaria — o mesmo teto de tempo estouraria de novo).
- Adicionado `--filter=blob:limit=1m` ao comando de clone: como a coleta só olha comentários em extensões de código-fonte (`CODE_EXTENSIONS`), blobs binários acima de 1MB (áudio, imagem, dataset) nunca são baixados.
- **Teste manual de validação (2026-07-06)** contra `55gms/55GMS` (um dos 7 repositórios problemáticos): o filtro reduz o volume transferido, mas **não é garantia universal** — esse repositório específico tem tantos arquivos pequenos (cada um abaixo do limite de 1MB) que ainda estourou 300s de teste. Para repositórios assim, o valor real da correção não é "sempre conseguir clonar", é falhar de forma limpa (sem lixo em disco, sem gastar retries à toa) em vez de silenciosamente corromper o estado — o que já é uma melhoria real sobre o comportamento anterior.

**Ação corretiva imediata:** os 15GB órfãos foram apagados manualmente (nenhum estava marcado como concluído no checkpoint, então nada de dados coletados foi perdido). Os 7 repositórios ficam pendentes; alguns devem se beneficiar do filtro de blob, outros (como `55gms/55GMS`) provavelmente continuarão falhando de forma limpa e ficando de fora do `code_comment` desse repositório — uma limitação aceita e documentada, não um erro silencioso.

### 2.4 Retomada após queda de energia

No meio da execução, a máquina precisou ser reiniciada. O checkpoint (`collection_state.json`) funcionou exatamente como projetado: a retomada identificou 473 pares (repositório, artefato) já concluídos e pulou direto para o trabalho pendente, sem duplicar nenhum registro. Único cuidado manual necessário: apagar os clones que estavam em andamento no momento da queda (6 diretórios, ~1,3GB) antes de retomar, já que `clone_repo()` não valida a integridade de um diretório existente antes de reaproveitá-lo — isso é uma limitação ainda não resolvida para o caso de queda abrupta (diferente do timeout, que agora é tratado). Recomendação: em caso de nova queda inesperada, sempre inspecionar e limpar `clones/` antes de retomar.

**Achado colateral:** o `.log` da rodada ficou com um byte nulo corrompido bem no ponto da queda de energia (recuperação do sistema de arquivos zerando um bloco parcialmente escrito). Isso faz o `grep` tratar o arquivo inteiro como binário e silenciosamente não encontrar nada (inclusive `grep -c ERROR` retornando 0 mesmo com erros reais no arquivo) — o Python (`open(..., 'rb')` + `.replace(b'\x00', b'')`) lê normalmente. Vale lembrar disso para debugging de logs futuros que tenham sobrevivido a uma queda abrupta.

### 2.5 Tempo de execução

| Trecho | Intervalo | Duração |
|---|---|---|
| 1ª execução (até a queda) | 11:42 → (queda, hora exata perdida na corrupção do log) | não determinado com precisão |
| 2ª execução (retomada) | 12:02 → 14:12 | ~2h10min |
| Trabalho processado na retomada | 2.663 dos 3.136 pares totais (473 já concluídos antes) | — |

### 2.6 Bug encontrado durante a pré-triagem LLM: casamento de frase atravessando quebra de linha

Ao inspecionar manualmente classificações "não-UBW" da pré-triagem LLM (Seção 4), o modelo apontou que a frase de algumas expressões multi-palavra "não aparecia" no texto — o que não deveria ser possível, já que `expression_in_text()` (`ubw/lexicon.py`) supostamente já garantia isso na coleta. Investigação confirmou um bug real, presente desde a implementação desse filtro (2026-07-03, ver `RESULTADOS_FINAL.md`).

**Causa raiz:** `_normalize_for_phrase_match()` colapsava **qualquer** sequência de caracteres não-alfanuméricos — incluindo quebras de linha — em um único espaço, antes de checar se a frase aparecia como substring. Isso apagava a fronteira entre itens de lista/linhas diferentes. Exemplo real encontrado (mensagem de commit squash em `abacusmodeling/abacus-develop`):

```
- set default pexsi_temp
- fix md in pexsi
```

Depois de normalizado, virava `"...pexsi temp fix..."` — o `_` de `pexsi_temp` e a quebra de linha antes do próximo item de lista desapareciam, juntando o final de uma palavra (`temp`) com o início de um item de lista completamente diferente (`fix`) numa frase que nunca existiu no texto original. Isso gerou **18 falsos positivos de "temp fix" só nesse repositório**.

Uma investigação correlata revelou um segundo bug independente, no canal de `code_comment`: `find_raw_events_for_expression()` (`scripts/02_collect_multiartifact.py`) nunca usava `expression_in_text()` — usava um substring puro sem fronteira de palavra (`if expression.lower() not in text.lower()`), então "stopgap" casava dentro de `histopgap` (um identificador de variável em código C/Fortran de engenharia — ex: `hisxitop`, `histopele`).

**Correção aplicada:**
- `expression_in_text()` reescrita para checar a frase **linha por linha** (cada linha normalizada independentemente), em vez de normalizar o texto inteiro de uma vez. Uma primeira tentativa de correção (usando um marcador de fronteira em vez de checar por linha) tinha uma regressão sutil — um marcador vazio "colava" a última palavra de uma linha com a primeira da linha seguinte, quebrando até expressões de uma palavra só. A versão final evita isso completamente.
- `find_raw_events_for_expression()` (canal `code_comment`) agora usa `lexicon.expression_in_text()` em vez do substring cru, fechando o segundo bug para coletas futuras.
- **Trade-off aceito conscientemente:** uma frase multi-palavra genuína que apareça quebrada por uma quebra de linha real (ex: texto com quebra de linha manual no meio de uma frase) agora é rejeitada. Prioriza precisão sobre recall, consistente com decisões anteriores do projeto (remoção de "magic number"/"don't touch").

**Escopo da contaminação medida** (com a versão corrigida, não a primeira tentativa com regressão):

| Dataset | Total antes | Falsos positivos purgados | % |
|---|---|---|---|
| `data/final` (134 repos) | 108 | 5 | 4,6% |
| `data/round_800` (784 repos) | 984 | 53 | 5,4% |

**Ação corretiva:** ambos os datasets foram purgados (backup em `ubw_collected_full_pre_purge_backup.csv`, registros removidos auditáveis em `purged_records_2026-07-06.csv`), RQ2/contagens recalculados, e o resultado da pré-triagem LLM (`llm_triage_results.csv`) também teve as linhas correspondentes removidas. Números finais já refletem a purga em todo este relatório.

## 3. O dataset coletado (após purga)

**Por artefato:** code_comment 439, commit_message 277, issue_body 118, pr_body 97.

**Por categoria:** B (workaround/urgência) 607, A (estética/hack explícito) 321, C (resignação/incerteza) 3 — a mesma escassez de C observada na rodada de 134 repos se confirma em escala maior, reforçando que é característica real do fenômeno, não artefato de amostra pequena.

**Top expressões:**

| Expressão | Registros |
|---|---|
| temporary fix | 286 |
| this is a hack | 142 |
| stopgap | 102 |
| ugly hack | 90 |
| temp fix | 82 |
| dirty hack | 82 |
| quick and dirty | 71 |
| workaround for now | 41 |

**Linguagens mais presentes entre os repositórios com ocorrência:** C++ (206), JavaScript (169), Python (151), TypeScript (80), C (73), Go (63), C# (44).

**RQ2 (threshold ≥3 ocorrências):** 66 repositórios, 653 registros — contra 178 repositórios que não atingem o threshold.

## 4. Achado de qualidade: concentração por estilo de um único autor

`ableplayer/ableplayer` tem 55 ocorrências de `stopgap`, todas em `code_comment`, todas em artifact_id distintos (arquivos/linhas diferentes) — não é vendoring nem duplicação. Investigação manual confirmou: o autor do projeto usa "stopgap" como jargão pessoal recorrente ("stopgap to prevent X from happening") em vários arquivos do código. É sinal genuíno (Categoria B legítima), não ruído — mas é um lembrete de que um único desenvolvedor prolífico pode dominar a contagem de um repositório, algo a considerar na análise estatística (ex: normalizar por repositório, não só contar registros brutos).

## 5. Pré-triagem LLM (OpenRouter / DeepSeek V4 Flash)

Rodada completa nos 931 registros pós-purga, via `scripts/03_metrics_llm_triage.py --provider openrouter` (modelo `deepseek/deepseek-v4-flash`, custo real na casa de centavos de dólar).

| Rótulo do LLM | Registros |
|---|---|
| UBW-verdadeiro | 796 |
| não-UBW | 78 |
| incerto | 57 |

(931 registros no total, já pós-purga; a fila de revisão humana obrigatória — incertos + amostra de auditoria de 15% dos aceitos — tem 188 itens em `llm_triage_results_human_review_queue.csv`)

**Achado de qualidade:** o modelo corretamente identificou casos como "Get rid of dirty hack in select() coroutine" como `não-UBW` — reconhecendo que o commit **remove** o hack em vez de mantê-lo, uma distinção semântica que o léxico sozinho não capta (o texto contém a frase gatilho, mas em sentido oposto ao de resignação funcional). Isso confirma o valor da pré-triagem como filtro adicional antes da anotação humana.

**Limitação técnica observada:** ~2% das chamadas (20/984 antes da purga) esgotaram as 3 tentativas de retry por respostas vazias/mal formadas do modelo, caindo em "incerto" por fail-safe (nenhum crash, comportamento correto). Isso é uma taxa aceitável, mas junto com a ausência de checkpoint incremental no script (rodou ~2h11min sem nenhuma visibilidade de progresso), motivou a tarefa pendente de portar o padrão de checkpoint/log do script 02 para o 03 antes do corpus completo.

## 6. Próximos passos

1. Repositórios pendentes por causa do bug de timeout (item 2.3) podem ser retomados agora com a correção — basta rodar o mesmo comando de novo (checkpoint cuida do resto).
2. Corpus completo do SEART-GHS ainda não foi gerado — esta rodada de 784 valida que a infraestrutura (tokens múltiplos, checkpoint, paralelismo, dashboard) aguenta escala real.
3. Checkpoint/log incremental no script 03 (pré-triagem LLM) — pendência registrada, ver Seção 5.
4. Anotação humana (Kappa/AC1) segue pendente, agora com a fila de revisão já pronta (188 itens) e um dataset bem maior para validar.

## 7. Reprodutibilidade

```bash
# Canonicalização (feita uma vez, gera data/round_800/repos_to_mine_canonical.csv)
python scripts/05_canonicalize_repos.py \
    --repos-csv ../data/repos_to_mine_800.csv \
    --out-csv ../data/round_800/repos_to_mine_canonical.csv

# Coleta (idempotente — retoma do checkpoint se interrompida)
export GITHUB_TOKENS="tok1,tok2,tok3,tok4"
python scripts/02_collect_multiartifact.py \
    --repos-csv ../data/round_800/repos_to_mine_canonical.csv \
    --out-dir ../data/round_800 \
    --state-file ../data/round_800/collection_state.json \
    --clone-dir ../data/round_800/clones \
    --parallel-workers 8
```

Dashboard de acompanhamento em tempo real: `data/dashboard.html` (servir com `python3 -m http.server 8765` a partir de `data/`).
