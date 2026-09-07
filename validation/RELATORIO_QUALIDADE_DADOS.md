# Relatório de Qualidade de Dados — Agente C (Auditor de Mineração)

**Pergunta que este relatório responde:** a coleta capturou o que diz que
capturou? É forense de dados sobre o CSV coletado, independente da anotação
humana (isso é trabalho do Agente B). Nenhuma linha do CSV foi editada à mão
— toda correção proposta aqui é patch de código para `ubw/lexicon.py` ou
`scripts/02_collect_multiartifact.py`.

## 0. Estado dos dados no momento desta auditoria

A fatia A **ainda está coletando** (`data/full_run/`, sem
`COLLECTION_COMPLETE`). Todos os números abaixo foram calculados sobre o
snapshot de `data/full_run/ubw_collected_full.csv` capturado em 2026-07-27:
**73.389 registros em 16.613 repositórios**. Isso é aproximadamente 22% do
corpus canônico completo (74.807 repos) — os números deste relatório são
**auditoria de processo**, não os números finais do dataset.

**O script `validation/c_audit_checks.py` é reexecutável** sobre o corpus
consolidado (fatia A + fatia B) assim que a coleta terminar:

```bash
python validation/c_audit_checks.py --csv <caminho do CSV consolidado> \
    --out-json validation/audit_flags_consolidado.json
```

Ele detecta automaticamente se `COLLECTION_COMPLETE` existe no diretório do
CSV e avisa se o corpus ainda é parcial.

### O que já estava resolvido antes desta auditoria (não redescoberto aqui)

Lidos `RESULTADOS_ROUND_800.md` e `RESULTADOS_ROUND_3000.md` antes de propor
qualquer coisa nova, conforme o mandato:

- **Contaminação por arquivo gerado/build** (31,2% dos `code_comment` brutos
  na rodada de 3.000 repos, causada por `search_index.js` do Documenter.jl e
  bundles com hash) foi corrigida em `is_vendored_path`/`VENDORED_FILENAMES`
  + `_dedup_identical_body_text()`. **Verificado nesta auditoria que a
  correção segura em escala**: o Check 5.1 (abaixo) confirma **0 registros**
  ainda passando pelo filtro oficial em 16.160 `code_comment` do corpus atual
  (22% do total) — a correção não regrediu.
- **Filtro de fronteira de linha em `expression_in_text()`** (bug de frase
  atravessando quebra de linha, corrigido em 2026-07-06) — não re-testado
  aqui porque já tem cobertura própria descrita no RESULTADOS_ROUND_800.md;
  o Check 1 (sanidade temporal) não encontrou nenhum sintoma residual
  compatível com esse bug.
- **Bug de timeout de clone / 15GB órfãos** — infraestrutural, fora do escopo
  de uma auditoria de CSV.

O que esta auditoria adiciona é além do que a correção retroativa já cobriu:
o filtro de vendoring por **path/nome** está limpo, mas há um gap de
**recall** (bibliotecas vendorizadas sem convenção de nome reconhecível —
Check 5.2) que nenhuma correção anterior tratou.

---

## Resumo das flags

| # | Check | Contagem | % | Severidade |
|---|---|---|---|---|
| 1.1 | `time_to_event_days` negativo | 0 / 73.389 | 0,00% | — |
| 1.2 | `time_to_event_days` == 0 | 10.928 / 73.389 | 14,89% | Baixa |
| 1.3 | `removed_at` < `created_at` | 0 / 73.389 | 0,00% | — |
| 1.4 | `is_censored=1` com `removed_at` preenchido | 0 / 73.389 | 0,00% | — |
| 1.5 | `is_censored=0` com `removed_at` nulo | 0 / 73.389 | 0,00% | — |
| 1.6 | `time_to_event_days` > `repo_age_days` (impossível) | 20.434 / 73.389 | **27,84%** | **Alta** |
| 2 | Amostra Zampetti (remoção acidental vs. real) | 25 amostrados / 8.557 elegíveis | — | Não verificável nesta rodada (ver Seção 3) |
| 3.1 | `body_text` duplicado dentro do mesmo repo+artefato | 3.225 / 73.389 | 4,39% | Média |
| 3.2 | Chave (repo, artefato, `artifact_id`, expressão) repetida | 46 / 73.389 | 0,06% | Baixa |
| 3.3 | `body_text` idêntico entre `commit_message` e `pr_body` | 11 pares | 0,01% | Média |
| 3.4 | `body_text` idêntico entre `issue_body` e `pr_body` | 0 pares | 0,00% | — |
| 4.1 | Contas bot que escapam do filtro (`author_login`) | 715 / 73.389 | 0,97% | **Alta** |
| 4.2 | Contas bot que escapam do filtro (`author_name`, sem login) | 147 / 73.389 | 0,20% | Média |
| 5.1 | `code_comment` ainda em path vendorizado pelo filtro oficial | 0 / 16.160 | 0,00% | — (confirma correção anterior) |
| 5.2 | `code_comment` em lib de terceiros conhecida sem marcador oficial | 644 / 16.160 | **3,99%** | Alta |
| 5.3 | `code_comment` em bundle minificado/hasheado residual | 25 / 16.160 | 0,15% | Média |
| 6 | Reprodutibilidade | procedimento documentado, não executado | — | Ver Seção 6 |

---

## 1. Sanidade temporal

**Achados limpos (Flags 1.1, 1.3, 1.4, 1.5 — 0 ocorrências):** nenhum
`time_to_event_days` negativo, nenhuma `removed_at` anterior a `created_at`,
e `is_censored` é 100% coerente com `removed_at` nulo/preenchido em 73.389
registros. Isso é evidência forte de que a lógica de pareamento de eventos
(`pair_events_into_records`, `_build_issue_pr_record`, `_build_commit_record`
em `scripts/02_collect_multiartifact.py`) está internamente consistente.

### Flag 1.2 — `time_to_event_days == 0` (14,89%, severidade baixa)

Concentrado em `pr_body` (7.232/14.504 = **49,9%** dos PRs têm `time_to_event_days=0`)
e `issue_body` (2.607/15.540 = 16,8%). Não é, por si só, um bug: PRs pequenos
(sobretudo bumps de dependência) são frequentemente merged no mesmo dia da
abertura, e `days_between()` arredonda para baixo (`.days` de um timedelta).
Mas é um sinal a cruzar com a **Flag 4.1** (contas bot): parte desse volume
de "eventos" de zero dias em `pr_body` são PRs de bots merged quase
instantaneamente — infla a contagem de "eventos observados" sem representar
uma decisão humana de resignação técnica.

**Recomendação:** não é uma correção de coleta — é um cuidado de análise.
Ao calcular estatísticas de sobrevivência de `pr_body`/`issue_body`, reportar
a fração de `time_to_event_days=0` separadamente e considerar excluir PRs de
bot (Flag 4) antes de interpretar tempos de resolução.

### Flag 1.6 — `time_to_event_days > repo_age_days` (27,84%, **severidade alta**)

Este é o achado mais significativo do Check 1. Um evento não pode levar mais
dias para se resolver do que a idade calculada do próprio repositório — se
isso acontece, `repo_age_days` está errado, não `time_to_event_days`.
Afeta **84,2% de `code_comment`** (13.606/16.158) e **25,0% de
`commit_message`** (6.797/27.185); `issue_body`/`pr_body` praticamente
imunes (31 e 0 casos).

**Duas causas raiz distintas, confirmadas por leitura de código:**

**(a) `code_comment` — assimetria de refs entre duas chamadas de `git log`.**
`get_first_commit_date()` (linha 743 de `scripts/02_collect_multiartifact.py`)
usa `git log --reverse --pretty=format:%aI -1` **sem `--all`** — só enxerga
o histórico alcançável a partir de HEAD. Já `find_raw_events_for_expression()`
(linha 831) usa `git log --all ... -S expression` — **todas** as
refs/branches/tags. Se o comentário for introduzido num commit alcançável
só por uma branch antiga, tag, ou histórico importado que não é ancestral
do HEAD atual, sua data de introdução pode ser mais antiga que o "primeiro
commit" calculado só a partir de HEAD, inflando `time_to_event_days` além de
`repo_age_days`. Exemplos concretos: `UnNetHack/UnNetHack`
(`repo_age_days=23`, mas comentário introduzido em 1990/1993 — 12-13 mil
dias de excesso); `davidgiven/ack` (`repo_age_days=2`, comentário de 1990).

**(b) `commit_message`/`issue_body` — `repo_age_days` usa metadado do
GitHub, não o histórico git real.** Para artefatos vindos da Search API,
`repo_age_days = days_between(repo.get("created_at"), COLLECTION_CUTOFF)`
(linha 1326), onde `created_at` é o timestamp de criação da **entidade
repositório no GitHub** (SEART/REST API), não o primeiro commit real. Quando
o histórico git foi importado de outra origem (conversão de CVS/SVN,
transferência de organização, fork destacado que virou independente), o
GitHub "criou" o repositório muito depois de commits que já existiam nele.
Exemplos: `BRL-CAD/brlcad` (commit de 1988, `repo_age_days=1947` ≈ 5,3 anos
— BRL-CAD é um projeto CAD de origem militar dos anos 80, história real
bem documentada); `davidgiven/ack` (commit de 1987, compilador ACK
originado nos anos 80); `libjpeg-turbo/libjpeg-turbo` (comentário de 1994,
`repo_age_days=0` — herda o histórico completo do libjpeg original).

**Achado colateral: `ourbigbook/ourbigbook`, um commit com
`created_at = 1970-01-01T00:00:00+00:00`** (epoch zero) — não é uma data
real, é o valor default de uma conversão de timestamp ausente/corrompida.
Esse único registro por si só produz `time_to_event_days=20.655` (56 anos),
o maior outlier do dataset.

**Por que isso importa para a dissertação:** `repo_age_days` é listado no
`plano.md` (Seção 6, trabalho futuro) como covariável do modelo Cox de
RQ2. Um covariável errado em 27,8% das linhas (84% em `code_comment`, que é
justamente o único artefato usado para medir remoção real — Seção 4 do
plano) compromete a validade de qualquer inferência que use `repo_age_days`
como controle de confusão, mesmo que `time_to_event_days` (a variável
dependente) esteja correto.

**Recomendação (patch de código, não de CSV):**
1. Em `get_first_commit_date()`, mudar para `git log --all --reverse
   --pretty=format:%aI -1` para usar o mesmo escopo de refs de
   `find_raw_events_for_expression()` — resolve a causa (a) para coletas
   futuras. Recalcular `repo_age_days` nos registros já coletados exigiria
   reabrir cada clone (não recomendado retroativamente; documentar como
   limitação conhecida do dataset atual).
2. Para artefatos de API (causa b), considerar usar
   `GitHubClient.get_repo_commit_count`-like: uma chamada adicional para
   obter a data do primeiro commit real via `GET /repos/{owner}/{repo}/commits`
   com `?until=<created_at>&per_page=1` seguido do último link de paginação,
   OU documentar explicitamente no dataset publicado que `repo_age_days`
   para `commit_message`/`issue_body`/`pr_body` é "idade da entidade GitHub",
   não "idade do histórico git", e não deve ser usado como covariável sem
   essa ressalva.
3. Adicionar um teste de sanidade equivalente à Flag 1.6 ao final de
   `apply_threshold_and_split()` em `scripts/02_collect_multiartifact.py`
   (`logger.warning` se a fração ultrapassar um limiar, no mesmo padrão do
   aviso de threshold de RQ2 que já existe ali) — hoje esse problema só é
   visível auditando o CSV depois, não durante a coleta.
4. Tratar `created_at` epoch (1970-01-01) como valor nulo/inválido em vez de
   data real — adicionar uma validação em `parse_iso_datetime()` que rejeite
   timestamps antes de, por exemplo, 1970-01-02 (a data 1970-01-01T00:00:00Z
   nunca é uma data de commit genuína nesta escala de projetos).

---

## 2. Remoção acidental vs. real (Zampetti et al., 2018)

**Não foi possível executar a verificação de fato nesta sessão** — ver
Seção "Restrições do ambiente" ao final. O procedimento completo está
implementado em `validation/c_audit_checks.py::live_check_removal_validity()`
e documentado abaixo para execução posterior com acesso a rede/clones.

### Limitação estrutural encontrada (independente da falta de rede)

O schema de coleta (`ubw/schema.py`, Tabela 3.5) **não retém o SHA do commit
de remoção** — só `removed_at` (timestamp ISO). O código de coleta
(`pair_events_into_records`, linha 902 de `scripts/02_collect_multiartifact.py`)
efetivamente TEM essa informação no momento da coleta (a variável `ev.sha`
dentro do loop de pareamento), mas descarta antes de gravar o `UBWRecord`.
Isso significa que qualquer checagem Zampetti pós-hoc — inclusive esta
auditoria — precisa **re-derivar** o commit de remoção rodando
`git log --all -S <expressão> -- <path>` de novo e casando por data mais
próxima de `removed_at`, em vez de simplesmente checar `git diff-tree` no
SHA já conhecido. Isso é mais caro computacionalmente e introduz uma fonte
de erro (duas datas de commit muito próximas podem ser casadas com o commit
errado).

**Recomendação (patch de schema, para a próxima rodada, não retroativo):**
adicionar um campo `removal_sha` (ou `introduction_sha` + `removal_sha`) ao
schema de `code_comment` — o custo de gravação é zero (a informação já
existe em memória no momento em que o registro é construído,
`ev.sha` em `pair_events_into_records`), e o ganho é permitir checagens de
validade de remoção (Zampetti) e auditoria de reprodutibilidade
determinísticas sem precisar re-rodar `git log -S`. Como o léxico está
congelado mas o *schema* de coleta não é o léxico, isso não deveria exigir
aval do orientador da mesma forma — mas fica registrado aqui como
recomendação, não como alteração feita.

### Procedimento completo (Seção 6 de `plano.md`, alinhado a Zampetti et al. 2018)

1. Amostrar `N` registros de `code_comment` com `is_censored=0` (25 amostrados
   nesta rodada, um por repositório distinto, `random_state=42` —
   reprodutível via `check_removal_validity_sample()`).
2. Para cada um, localizar o clone local do repositório (ou clonar, se a
   coleta principal não estiver rodando concorrentemente).
3. `git log --all -S "<matched_expression>" --pretty=format:"%H|%aI" --
   <path>` e escolher o commit cuja data está mais próxima de `removed_at`.
4. `git diff-tree --no-commit-id --name-status -r <sha> -- <path>`:
   - status `D` (arquivo inteiro deletado) → **remoção acidental**: o
     registro deveria ter `is_censored=1`, não `is_censored=0` — é
     exatamente o padrão descrito por Zampetti et al. (2018), que encontram
     20–50% de remoções acidentais em datasets de SATD.
   - status `M` (modificação) → remoção textual genuína, coerente com a
     Seção 4 do `plano.md`.
5. Cruzar com o status do repositório (`GET /repos/{owner}/{repo}` →
   `archived`): se o repositório está arquivado hoje, é um sinal adicional
   (não definitivo — o arquivamento pode ter ocorrido bem depois da
   remoção) de que o "evento" pode refletir o fim de vida do projeto, não
   uma decisão editorial sobre o comentário.

**Amostra extraída nesta rodada** (25 repositórios, ver
`validation/c_audit_checks.py` saída "2.0" e o JSON anexo) inclui casos como
`alekmaul/pvsneslib` (`compiler/tcc-65816/816-gen.c`, "dirty hack", 2019→2022)
e `apache/cordova-lib` (`AudioPlayer.java`, "this is a hack", 2013, resolvido
em ~5 meses) — nenhum desses foi verificado quanto a deleção de arquivo
inteiro nesta rodada; ficam como ponto de partida para a próxima execução
com rede disponível.

**Severidade:** não quantificável nesta rodada — **pendência explícita**,
não "0 problemas encontrados". Não confundir ausência de verificação com
ausência de risco.

---

## 3. Deduplicação em escala

### Flag 3.1 — `body_text` duplicado dentro do mesmo repo+artefato (4,39%, severidade média)

A correção de contaminação por arquivo gerado/build (RESULTADOS_ROUND_3000,
`_dedup_identical_body_text()`) **só roda para `code_comment`**, e só
**dentro de uma única chamada** de `collect_code_comment_records()` (por
repositório, por execução). Ela nunca foi desenhada para cobrir
`commit_message`/`issue_body`/`pr_body`. O Check 3.1 confirma que esses três
tipos concentram 100% das duplicatas exatas remanescentes:
`commit_message` 2.047, `issue_body` 649, `pr_body` 529 — zero em
`code_comment` (evidência adicional de que a correção de 2026-07-14 continua
segurando para esse artefato).

**Maior ofensor:** `CTSRD-CHERI/cheribsd` — 380 mensagens de commit
duplicadas (de 402 registros de `commit_message` do repositório inteiro,
ou seja, quase todas). Inspeção manual confirma a causa: mensagens idênticas
em SHAs *diferentes* e até em timestamps idênticos (ex.: dois SHAs distintos
com a mesma mensagem "1) added proc file system..." datados exatamente de
`1993-12-12T12:22:57+00:00`, um assinado "David Greenman" e outro "dg" — o
mesmo autor, dois formatos de nome). Esse é um artefato clássico de
importação de histórico CVS/SVN antigo para git (comum em projetos BSD/
kernel com décadas de história pré-GitHub): o mesmo commit lógico aparece
replicado em múltiplas branches de manutenção com SHA diferente porque foi
re-commitado/cherry-picked, não porque a coleta duplicou algo.

**Segundo maior:** `logicalclocks/rondb` (132 duplicatas em
`commit_message`) — mesma classe de causa provável (fork/histórico
compartilhado com MySQL/NDB Cluster).

**Impacto:** para RQ1 (prevalência), cada mensagem de commit duplicada é
contada como uma ocorrência UBW independente, inflando a contagem por
categoria/expressão nesses repositórios específicos sem representar uma
segunda decisão editorial distinta.

**Recomendação:** estender `_dedup_identical_body_text()` (hoje interna a
`collect_code_comment_records`) para os três artefatos de API, aplicada
**por (repo, artifact_type)** depois que todos os registros desse par já
estiverem escritos — hoje o CSV é *append*, então isso precisaria virar um
passo de pós-processamento (como `apply_threshold_and_split`), não um filtro
em tempo de coleta. Sugestão de implementação: uma função
`dedup_identical_body_text_post_hoc(csv_path)` chamada no fim de `main()`,
mesma lógica de `_dedup_identical_body_text` mas operando sobre o CSV
completo agrupado por `(repo_full_name, artifact_type)`, com log de quantas
linhas foram removidas por repo (auditável, como já é o padrão do projeto
com `purged_records_2026-07-06.csv`).

### Flag 3.2 — chave `(repo, artifact_type, artifact_id, matched_expression)` repetida (0,06%, severidade baixa)

**Não é bug de reprocessamento.** Inspeção manual das 46 linhas (23 pares)
confirma ciclos genuínos de introdução→remoção→reintrodução na mesma
localização (`path:line`). Exemplo: `ApolloAuto/apollo`,
`modules/canbus/vehicle/lexus/protocol/shift_rpt_228.cc:152`, "temporary
fix" introduzido em 2018-10-11, removido em 2022-11-16, **reintroduzido no
mesmo lugar** em 2022-11-17 e removido de novo em 2022-11-29 — dois eventos
de sobrevivência genuinamente distintos na mesma linha de código ao longo do
tempo. O algoritmo de pareamento (`pair_events_into_records`) está correto
em tratar isso como dois registros.

**Recomendação (documentação, não código):** deixar explícito no dicionário
de dados/README que `(repo_full_name, artifact_type, artifact_id,
matched_expression)` **não é uma chave única** — quem for agregar por
`artifact_id` (por exemplo, para juntar com anotação humana) precisa incluir
`created_at` na chave de junção, ou vai colapsar dois eventos reais em um.

### Flag 3.3 — `body_text` idêntico entre `commit_message` e `pr_body` (11 pares, severidade média)

Confirma exatamente o padrão citado no mandato do Agente C: mesma admissão
textual contada duas vezes, uma como `commit_message` e outra como
`pr_body`, no mesmo repositório. Exemplos: `numpy/numpy` (commit
`7b137ab0...` = PR #6786), `dotnet/efcore` (commit `a63e8d08...` = PR #148),
`HabitRPG/habitica` (PR #4191). O mecanismo mais provável é squash-merge
(o GitHub copia a descrição do PR para a mensagem do commit squashed) ou PR
de commit único. Volume baixo em termos absolutos (11/73.389 = 0,01%), mas
sistemático — cada instância é uma dupla-contagem certa, não uma
possibilidade.

**Recomendação:** para RQ1, ao agregar por repositório+categoria, aplicar um
dedup **cross-artifact** por `(repo_full_name, _body_norm)` antes de contar
— manter apenas o registro com `artifact_type` de maior prioridade
metodológica (sugestão: `pr_body` > `commit_message`, porque o PR carrega
mais contexto/metadado de autor via `login`, enquanto o commit squashed é
derivado). Implementar como uma função `dedup_cross_artifact()` separada em
`c_audit_checks.py` ou nos scripts de análise de RQ1, nunca reescrevendo o
CSV de coleta.

### Flag 3.4 — `issue_body` × `pr_body` idêntico (0 pares)

Nenhuma ocorrência no snapshot atual. Mantido no script para re-checagem no
corpus consolidado (pode aparecer em maior volume).

---

## 4. Contas automatizadas

### Flag 4.1 — `author_login` bot-like que escapa do filtro atual (715 registros, 0,97%, **severidade alta**)

O filtro atual (`_is_bot_login()`, linha 349 de
`scripts/02_collect_multiartifact.py`) só bloqueia logins que contêm o
literal `"[bot]"` ou que batem exatamente com
`{"dependabot", "renovate", "github-actions", "greenkeeper", "snyk-bot", "pull"}`.
Qualquer login com sufixo diferente (`-bot`, `bot` sem colchetes, `-robot`,
`Bot` em CamelCase misturado ao nome) passa direto.

**`pyup-bot` é sozinho responsável por 277 dos 715 registros** (38,7%) —
exatamente o caso citado no mandato do Agente C. Exemplo concreto
verificado: `addok/addok`, PR #695, expressão "stopgap", corpo do PR:

> This PR updates [pytest](https://pypi.org/project/pytest) from **6.1.2**
> to **7.0.0**. \<details>\<summary>Changelog\</summary> ### 7.0.0 [...]
> Deprecations [...]

A palavra "stopgap" (ou qualquer expressão do léxico) aparece dentro do
**changelog colado do pacote pytest**, escrito pelos mantenedores do
`pytest`, não por ninguém do repositório `addok/addok`. Isso viola
diretamente a condição 1 da Seção 4 do `ANNOTATION_GUIDELINE.md`
("auto-admissão... não descrevendo, de forma abstrata ou de terceiros...").

Outros bots com volume relevante: `renovate-bot` (42 — variante de nome do
`renovate` que já é bloqueado só na forma exata "renovate"),
`semantic-release-bot` (23), `jenkins-infra-bot` (23), `BrewTestBot` (22),
`glassfishrobot` (18), `greenkeeperio-bot` (13 — variante do `greenkeeper`
já parcialmente coberto), `k8s-ci-robot` (9), entre outros 145 logins
distintos.

**Recomendação (patch em `ubw/lexicon.py` ou módulo equivalente,
compartilhado entre coleta e auditoria):**
```python
def _is_bot_login(login: Optional[str]) -> bool:
    if not login:
        return False
    lowered = login.lower()
    return (
        "[bot]" in lowered
        or lowered in _BOT_LOGIN_EXACT
        or lowered.endswith("-bot")
        or lowered.endswith("bot")          # cobre "TurboTurtle"? não — ver ressalva abaixo
        or lowered.endswith("-robot")
        or lowered.endswith("robot")
    )
```
**Ressalva:** um sufixo puro `"bot"` sem separador (`endswith("bot")`) tem
risco de falso positivo em nomes de usuário legítimos que terminem com essas
letras por coincidência (raro, mas o dataset já mostra `"MotorBottle"` e
`"BoboTiG"` como near-misses de substring "bot" que NÃO são bots — ver Flag
4.2). Recomenda-se `endswith(("-bot", "_bot", "-robot", "[bot]"))` (com
separador explícito) em vez de sufixo puro, para reduzir o risco de novo
falso positivo introduzido pela própria correção. Testar contra a lista de
715 logins encontrados aqui como gold set de regressão antes de aplicar.

### Flag 4.2 — `author_name` bot-like sem `author_login` bot-like (147 registros, 0,20%, severidade média)

Gap independente do 4.1: para `commit_message`, o filtro de bot
(`_passes_content_filters`, chamado só com `author_login`) nunca olha
`commit_info.get("author", {}).get("name")`. Isso deixa passar commits cujo
autor é claramente um bot pelo *nome* do commit mas cujo `login` da API não
foi resolvido/está vazio: `github-actions[bot]`, `autonoma-github-bot[bot]`,
`aks-node-sig-release-assistant[bot]`, `zeebe-bors[bot]` — todos com `"[bot]"`
literal no nome, que já seria capturado pela lógica de `_is_bot_login` **se
fosse aplicada ao nome também**, não só ao login.

**Nota sobre falso-positivo evitado:** dois nomes aparecem na lista por
conterem a substring "bot" sem serem bots — "Stefan Kroboth" (contém
"**bot**h") e "Vladimir Chebotarev" / "excitoon" (contém "che**bot**arev").
Confirma que qualquer regra de detecção por nome **precisa ser baseada em
`"[bot]"` literal ou sufixo com separador**, nunca substring livre de
"bot" — o mesmo cuidado da ressalva do Flag 4.1.

**Recomendação:** em `_build_commit_record()`
(`scripts/02_collect_multiartifact.py`, linha 440), passar também
`commit_info.get("author", {}).get("name")` para `_passes_content_filters`
e checar `"[bot]" in name.lower()` além do login — usando o marcador
literal `[bot]`, não substring de "bot", para não reintroduzir o
problema que a Flag 4.2 evitou por sorte nesta amostra.

---

## 5. Efetividade do filtro de path vendorizado

### Flag 5.1 — `code_comment` ainda em path vendorizado pelo filtro oficial (0/16.160 = 0,00%)

**Filtro oficial confirmado limpo em escala.** Nenhum registro do corpus
atual (22% do total esperado) passa `lexicon.is_vendored_path()` como
verdadeiro — ou seja, a correção de 2026-07-14 (RESULTADOS_ROUND_3000, Seção
2) continua segurando conforme o corpus cresce 20x. Esta é a re-verificação
explícita pedida no mandato ("verificar se a correção segura em escala") e o
resultado é positivo.

### Flag 5.2 — `code_comment` em lib de terceiros conhecida sem marcador oficial (644/16.160 = **3,99%**, severidade **alta**)

Esta é a descoberta central do Check 5. O filtro oficial reconhece
vendoring por **convenção de path** (`vendor/`, `node_modules/`, sufixo
`-N.N.N/`) ou por **nome de arquivo específico** (`VENDORED_FILENAMES`, uma
lista fixa de ~20 libs JS conhecidas). Ele não reconhece bibliotecas C/C++
amplamente vendorizadas sob nomes de diretório genéricos que não seguem
nenhuma dessas duas convenções. Uma varredura heurística (lista curada de
~35 nomes de projeto open-source amplamente embarcados como cópia de
código-fonte — Eigen, Boost, googletest, OpenSSL/LibreSSL, FreeType, zlib,
jQuery, entre outros) encontra **644 comentários em 16.160** (3,99%) dentro
de diretórios com esses nomes.

Exemplos verificados manualmente (não apenas por regex — path lido e
confirmado como biblioteca vendorizada real):

| Repositório | Path | Biblioteca embarcada |
|---|---|---|
| `gnina/gnina` | `src/eigen/demos/mandelbrot/mandelbrot.cpp` + `Eigen/src/Core/arch/SSE/Complex.h` | Eigen (álgebra linear C++) — 2 registros no mesmo repo |
| `3dem/relion` | `src/Eigen/src/Core/CoreEvaluators.h` | Eigen |
| `3MFConsortium/lib3mf` | `Libraries/libressl/apps/openssl/s_client.c` | LibreSSL |
| `ablab/spades` | `assembler/ext/include/boost/config/suffix.hpp` | Boost |
| `ablab/spades` | `.../googletest/googletest/test/gtest_unittest.cc` | googletest |
| `accellera-official/systemc` | `src/sysc/packages/boost/config/suffix.hpp` | Boost |
| `AdaEngine/AdaEngine` | `Modules/msdf-atlas-gen/freetype/src/gzip/ftgzip.c` | FreeType |
| `acornjs/acorn` | `test/jquery-string.js` | jQuery (dentro de teste, provável false-positive de outra natureza — string literal de teste, não vendoring) |
| `kinectron/kinectron` (achado durante a amostragem manual do Check 2/6, fora da varredura automática) | `app/assets/js/peerjsv104.noerror.js` | PeerJS v1.0.4 |

O "dirty hack"/"temporary fix" registrado dentro de `Eigen/src/Core/...` é
uma admissão dos mantenedores do Eigen, não do time de `gnina/gnina` ou
`3dem/relion` — mesma classe de violação de validade de construto que o
Flag 4.1 (contas bot), mas via path em vez de autor.

**Ressalva metodológica:** esta é uma heurística de **candidatos**, não um
filtro pronto para aplicar automaticamente — `acornjs/acorn` mostra que
"jquery" no path pode ser um arquivo de teste/fixture legítimo do próprio
projeto (que aliás já deveria cair no filtro de `looks_like_comment` vs.
string de teste, território do Agente B), não vendoring de verdade. Cada
ocorrência exige checagem manual antes de virar regra de exclusão
automática — daí a recomendação abaixo ser "candidato a marcador", não
"marcador definitivo".

**Recomendação:** revisar os 644 candidatos (lista completa disponível
rodando `c_audit_checks.py --out-json`) e promover os confirmados para
`VENDORED_PATH_MARKERS`/`VENDORED_FILENAMES` em `ubw/lexicon.py`, seguindo o
mesmo processo já usado para `search_index.js` (registro explícito em
LEXICO.md/CHANGELOG, não alteração silenciosa). Como isso é o filtro de
vendoring, não o léxico semântico, não deveria exigir o mesmo nível de aval
do orientador que uma mudança de expressão — mas o registro em CHANGELOG
continua sendo boa prática do projeto.

### Flag 5.3 — bundle minificado/hasheado residual (25/16.160 = 0,15%, severidade média)

Casos como `Addepar/ember-table` →
`versions/master/assets/vendor-1cbfbdc539760dce4b368016d4563d38.js` (nome de
bundle com hash de conteúdo, mesma classe do `search_index.js` já corrigido,
mas hash diferente por build) e `antvis/S2` →
`styles-9f38b0ecd2c2801b58f4.js`. Volume baixo (25 registros), mas confirma
que a heurística por sufixo `.min.js`/`.min.css` não cobre 100% dos bundles
— arquivos de build modernos frequentemente não usam `.min.` no nome, só um
hash. `_dedup_identical_body_text()` (que já pega bundles com conteúdo
idêntico entre commits) não ajuda aqui se o conteúdo do bundle mudar a cada
build (hash muda, texto do comentário pode mudar também).

**Recomendação:** adicionar um padrão de regex a `is_vendored_path()`:
arquivo `.js`/`.css` cujo nome termina em `-[0-9a-f]{8,}\.(js|css)$` (hash
hexadecimal de 8+ caracteres antes da extensão) dentro de diretórios como
`assets/`, `packs/`, `public/`, `versions/*/assets/` — mesma lógica de
"nome de bundle não convencional" já usada para justificar o dedup por
conteúdo, mas capturando pelo padrão de nome antes mesmo de comparar
conteúdo.

---

## 6. Reprodutibilidade

**Procedimento documentado, não executado nesta sessão** — ver função
`describe_reproducibility_procedure()` em `validation/c_audit_checks.py`
para a versão executável do texto abaixo.

**Objetivo:** confirmar que re-rodar a coleta sobre o mesmo repositório em
outro momento produz um conjunto de registros consistente, dentro da
variação esperada por a Search API do GitHub mudar no tempo (Seção 3.4 do
`plano.md`).

**Procedimento:**
1. Escolher 2–3 repositórios já 100% concluídos no checkpoint (todos os 4
   `artifact_types`), pequenos/médios (evita timeout de clone de 900s).
2. Rodar `scripts/02_collect_multiartifact.py` de novo, isolado, com
   `--out-dir`/`--clone-dir`/`--state-file` apontando para um diretório
   **temporário**, nunca `data/full_run/`.
3. Comparar: para `code_comment`, os pares (path, expressão, `created_at`)
   devem bater exatamente — `git log -S` é determinístico sobre o mesmo
   histórico; `is_censored` pode diferir se uma remoção real aconteceu entre
   as duas datas de corte (não é erro). Para `issue_body`/`pr_body`/
   `commit_message`, a contagem pode crescer (itens novos indexados entre as
   duas coletas) mas **nenhum registro da coleta original deveria
   desaparecer** da nova.
4. Critério de aceite: 0 registros de `code_comment` da coleta original
   ausentes na re-coleta; ≥95% de presença para os artefatos via API
   (tolerância à evolução da Search API).

**Por que não foi executado agora:** a coleta da fatia A está rodando neste
exato instante em `data/full_run/`, usando os 5 tokens GitHub disponíveis em
`.env` em rotação contra o limite de 30 req/min/token da Search API. Uma
re-coleta concorrente competiria pelo mesmo orçamento e arriscaria condição
de corrida em `data/full_run/clones/` se por acaso mirasse os mesmos
repositórios que um worker de `code_comment` está processando agora — o
mandato deste agente explicitamente pede para não interferir na coleta em
andamento.

**Restrições do ambiente confirmadas nesta sessão** (relevantes também para
o Check 2, que também precisa de rede):
- Chamadas HTTP diretas à API do GitHub a partir do shell/bash deste
  ambiente de auditoria retornam `403 Forbidden` no proxy de saída — sem
  acesso de rede autenticado disponível para scripts Python rodando aqui.
- O único canal de rede funcional (`web_fetch`) faz requisições **não
  autenticadas** (sem usar os tokens do `.env`, que também não deveriam ser
  gastos nesta verificação para não competir com a coleta) e esgotou o
  limite de 60 req/h não autenticado do GitHub depois de ~9 chamadas nesta
  sessão — insuficiente para validar a amostra completa dos Checks 2 e 6.

**Recomendação:** rodar este procedimento manualmente depois que
`COLLECTION_COMPLETE` existir em `data/full_run/` (ou, para o Check 2, em
paralelo à coleta se rodado de uma máquina/rede diferente com seu próprio
token, para não competir por rate limit).

---

## Tabela consolidada de recomendações por prioridade

| Prioridade | Recomendação | Onde | Tipo |
|---|---|---|---|
| 1 | Corrigir gap de bot: sufixo `-bot`/`-robot`/`[bot]` com separador em `_is_bot_login`, aplicado também a `author_name` de `commit_message` | `scripts/02_collect_multiartifact.py` | patch de código, futuras coletas |
| 2 | Revisar e promover os 644 candidatos de vendoring (Flag 5.2) para `VENDORED_PATH_MARKERS` | `ubw/lexicon.py` + `LEXICO.md`/`CHANGELOG.md` | patch de código + registro |
| 3 | Documentar que `repo_age_days` de artefatos via API é "idade da entidade GitHub", não idade real do histórico git — não usar sem essa ressalva no modelo Cox de RQ2 | `plano.md` / dicionário de dados | documentação |
| 4 | Alinhar `get_first_commit_date()` para usar `--all` (mesmo escopo de refs da busca de eventos) | `scripts/02_collect_multiartifact.py` | patch de código, futuras coletas |
| 5 | Adicionar `removal_sha`/`introduction_sha` ao schema de `code_comment` | `ubw/schema.py` | patch de schema, futuras coletas |
| 6 | Dedup cross-artifact (`commit_message` × `pr_body`) como passo de pós-processamento na análise de RQ1, nunca no CSV bruto | scripts de análise (novo) | patch de código |
| 7 | Estender `_dedup_identical_body_text` para os 3 artefatos de API, como passo pós-hoc auditável | `scripts/02_collect_multiartifact.py` | patch de código |
| 8 | Executar Check 2 (Zampetti) e Check 6 (reprodutibilidade) de fato, com rede/token dedicado, fora da máquina da coleta em andamento | operacional | ação humana |
| 9 | Rodar `c_audit_checks.py` sobre o corpus consolidado (fatia A + B) antes de qualquer número final na dissertação | operacional | ação humana |

---

## Como reexecutar esta auditoria

```bash
cd dataset_ugly_but_works
python validation/c_audit_checks.py --csv data/full_run/ubw_collected_full.csv
# ou, no corpus consolidado final:
python validation/c_audit_checks.py --csv <caminho consolidado> \
    --out-json validation/audit_flags_consolidado.json
```

O script imprime cada flag com contagem, percentual, severidade e exemplos
concretos, e grava tudo em JSON se `--out-json` for informado. Ele é
somente-leitura: nunca escreve no CSV de coleta nem no
`collection_state.json`.
