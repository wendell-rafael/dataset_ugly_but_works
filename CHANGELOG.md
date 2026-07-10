# Changelog

Histórico consolidado da infraestrutura de software (não do dataset em si —
para resultados de cada rodada de coleta, ver `RESULTADOS_*.md`). Datas
refletem quando o problema foi identificado e corrigido, não necessariamente
commits formais (o projeto ainda não tinha controle de versão até este
registro).

## 2026-07-09 — revisão de robustez de API (3 correções pós-review)

Achados de um code review focado em boas práticas de mineração/limitações de
API, corrigidos no mesmo dia:

- **Truncamento silencioso no teto de 1000 da Search API** (`github_api.py`,
  `02_collect_multiartifact.py`): a Search API retorna no máximo 1000
  resultados por query; como a coleta batched cobre ~8 repos numa só query
  (`repo:` OR), esses repos dividiam um único orçamento de 1000 e, com
  `order=asc`, os resultados mais recentes eram descartados sem aviso. Agora
  a coleta detecta quando uma expressão atinge o teto (`SEARCH_API_CAP =
  1000`), emite `warning` e refaz a busca daquela expressão por repositório
  individual (cada um com seu próprio orçamento de 1000), recuperando o
  recall. Só paga chamadas extras quando o truncamento de fato acontece.
  Lógica item→`UBWRecord` extraída em helpers (`_build_issue_pr_record`,
  `_build_commit_record`) compartilhados entre o caminho batched e o
  fallback per-repo.
- **Rate limit secundário sem `Retry-After` abortava a coleta**
  (`github_api.py`, `request()`): um 403 de abuse detection sem o header
  `Retry-After` e sem `remaining==0` caía no `raise` (tratado como permissão
  negada). Agora detecta a mensagem "secondary rate limit" no corpo e recua
  ≥60s (mínimo documentado pelo GitHub) antes de retentar; só 403 genuíno de
  permissão levanta erro.
- **`total_repositories` do meta.json subcontava em retomada** (`01_screening
  _seart.py`): após `--resume-from-page`, `len(rows)` só contava as linhas
  desta invocação, não o total no CSV. Passou a contar as linhas de dados do
  CSV de saída real (`_count_csv_data_rows`).

## 2026-07-09 — checkpoint incremental na triagem (script 01)

- `01_screening_seart.py`: `screen_repositories()` gravava CSV e arquivo
  bruto apenas ao final do loop de paginação inteiro — uma rodada de
  triagem sem limite de repositórios leva dezenas de minutos a horas, e uma
  interrupção no meio perdia tudo. Corrigido para escrita incremental
  (append + flush por página); arquivo bruto passou de um único JSON para
  JSONL (uma página por linha). Novo parâmetro `--resume-from-page`.
- Bug pego no smoke test da correção acima: o corte por `--max-repos` só
  truncava a lista em memória — o CSV incremental já tinha gravado a
  página inteira antes do corte ser aplicado, produzindo mais linhas do
  que o limite pedido. Corrigido truncando a página antes de escrever.
- Confirmado que os critérios default do script já correspondiam
  exatamente à Seção 2.2 do plano (não era necessário nenhum ajuste de
  parâmetro para uma rodada "oficial").

## 2026-07-08 — descoberta de escala do corpus e tolerância a falhas end-to-end

- Descoberto que o corpus elegível do SEART-GHS (aplicando os critérios da
  Seção 2.2) é da ordem de dezenas de milhares de repositórios e
  continua crescendo — o serviço é ativamente mantido (dump no máximo 15
  dias atrás do GitHub real), não uma base estática. Implicação
  metodológica: "processar todo o corpus" não tem alvo fixo sem declarar
  uma data de snapshot explícita.
- `03_metrics_llm_triage.py`: nova função `run_llm_triage_incremental()`
  (default da CLI; `--no-resume` mantém o comportamento antigo em
  memória). O próprio CSV de saída funciona como checkpoint, chaveado por
  `(repo, tipo de artefato, id, expressão)`. Testado ponta a ponta
  (interrupção simulada em 5 de 8 candidatos, retomada classifica só os 3
  restantes e recalcula a amostragem de auditoria sobre o conjunto
  completo).
- `04_pattern_mining.py`: `_save_candidates()` passou a ser chamado após
  cada lote e cada worker concluído, não só no bloco `finally` — uma
  rodada real de ~1h contra 784 repositórios morreu por interrupção
  externa do processo depois que a fase de API tinha terminado mas antes
  de qualquer worker de `code_comment` completar, e como o `finally` nunca
  roda em kill externo (sem exceção Python), toda a fase de API foi
  perdida. Também ganhou suporte a múltiplos tokens e a mesma correção de
  `TimeoutExpired` do item abaixo.
- `tls_fix.py`: certificado de `seart-ghs.si.usi.ch` expirou (confirmado
  via `openssl s_client`, não era relógio local). Em vez de desabilitar
  verificação TLS por completo, implementada fixação de impressão digital
  SHA-256 (`verify_pinned_fingerprint`, `get_session_trusting_pinned_cert`)
  — só aceita a conexão se o certificado bater exatamente com o valor
  conhecido, ignorando apenas a checagem de data. Ativado via flag
  explícita `--allow-expired-cert-pin`, nunca como padrão silencioso.
- Campos de identidade do autor de introdução adicionados ao schema
  (`author_name`, `author_login`, `author_email`, `author_hash` — SHA-256
  sem salt, pseudonimização não anonimização formal) em
  `ubw/schema.py`/`UBWRecord`, populados nos três canais de coleta
  (`02_collect_multiartifact.py`). Disponibilidade varia por canal:
  `commit_message` tem os 4 campos; `issue_body`/`pr_body` só login;
  `code_comment` tem nome+e-mail (sem login, via `git log` local).
- Mineração de padrões estruturais sugeridos pelo orientador (`but_works`,
  `concessive_works`, `but_passes_tests`, `concessive_passes_tests`)
  rodada em escala (784 repositórios, 866 candidatos totais). Achado
  paralelo: contaminação por jQuery vendorizado sob nomes de pasta não
  cobertos pelas heurísticas existentes — corrigido com detecção por nome
  de arquivo (`VENDORED_FILENAMES` em `ubw/lexicon.py`).

## 2026-07-06 — bug de correspondência cross-linha e otimização de token/desempenho

- **Bug metodológico real**: `expression_in_text()` em `ubw/lexicon.py`
  normalizava quebras de linha junto com pontuação comum antes de checar
  substring, permitindo que uma frase de duas palavras casasse através de
  itens de lista/linhas diferentes (ex.: `"...pexsi_temp\n- fix..."` virava
  `"...pexsi temp fix..."` e casava com a expressão "temp fix"). Contaminou
  ~4,6–5,4% dos registros já coletados em dois datasets. Corrigido para
  checar a frase linha por linha. Bug irmão: `code_comment` usava
  substring cru sem fronteira de palavra (`"stopgap"` casava dentro de
  `"histopgap"`) — corrigido para usar a mesma função de correspondência
  dos outros canais.
- Rotação de múltiplos tokens GitHub (`ubw/github_api.py`, `_TokenSlot`,
  round-robin) para multiplicar o teto de requisições da Search API.
- Otimização de batching: múltiplos qualificadores `repo:` numa única
  query da Search API (semântica OR, verificada empiricamente), reduzindo
  a fase de busca via API de ~5,8h para ~48min.
- `GIT_TIMEOUT_SECONDS` elevado de 120s para 300s (`git log -S` sobre
  repositórios grandes estourava o timeout anterior em algumas
  expressões).
- Rodada de referência de 784 repositórios (`data/round_800/`) concluída
  com 4 tokens em rotação e 8 workers paralelos — checkpoint de coleta
  testado sob interrupção real (reinício de máquina no meio da rodada,
  retomada correta via `collection_state.json`).
- Dashboard de acompanhamento em tempo real (`data/dashboard.html`, sem
  dependências externas) lendo `collection_state.json` diretamente.

## 2026-07-03 — consolidação da rodada final do piloto

- Filtros de precisão adicionados: descarte de artefatos de bots por login,
  exigência de correspondência textual normalizada (a Search API do
  GitHub faz stemming e retorna falsos positivos).
- `scripts/05_canonicalize_repos.py`: repositórios renomeados entre a
  indexação do SEART-GHS e a coleta quebravam o qualificador `repo:` da
  Search API (HTTP 422) e podiam duplicar entradas no corpus. Resolvido
  via redirect da REST API (`GET /repos/{owner}/{name}`), que ao
  contrário da Search API segue renomeações.

## 2026-07-01/02 — piloto exploratório (rodadas 1 e 2, 20 → 140 repositórios)

- Identificado e corrigido problema de contaminação por código vendorizado
  (73% dos registros de `code_comment` na rodada 1) via filtro de path.
- Duas expressões de alto risco no léxico ("magic number", "don't touch")
  identificadas como baixa precisão (0/22 verdadeiros positivos em amostra
  manual) e removidas.

## Nota de ambiente

Após reinício da máquina em algum ponto de julho/2026, `python3` passou a
resolver para Python 3.12 sem `pandas` instalado, enquanto `python3.10`
manteve o ambiente funcional. Usar `python3.10` explicitamente para
qualquer análise ad-hoc dependente de `pandas` nesta máquina até
investigação/correção definitiva do ambiente.
