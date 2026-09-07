# Agente D — Export do dataset publicável e varredura de PII em body_text

**Mandato:** Seção 3 do `PLANO_VALIDACAO_COWORK.md` (Agente D). **Data:** 2026-07-27.
**Escopo:** o mecanismo (script de export + varredura de PII), não a política. A política de
anonimização/ética escrita (consentimento, base legal LGPD, retenção, checklist para o comitê de
ética) é entrega de outra etapa (Fable) — este documento levanta os fatos e implementa o
mecanismo que essa política vai configurar via `--salt`/`--hmac-key`.

**Estado dos dados (leia antes de usar estes números):** a coleta da fatia A ainda está rodando
em `data/full_run/` — não existe sentinela `COLLECTION_COMPLETE` (verificado nesta sessão) e o
processo de coleta (`run_chain.sh`, pid ativo) segue em execução. A fatia B foi coletada em outra
máquina e **não** está incluída aqui. Todos os números abaixo são sobre
`data/full_run/ubw_collected_full.csv` no momento da varredura (2026-07-27, 73.412 linhas) —
**parciais**, não o corpus consolidado. Re-rodar a varredura sobre o dataset final antes de
fechar a política é obrigatório (mesmo aviso já vale para a amostragem do Agente B, Seção 5 do
plano).

---

## 1. O script — `scripts/06_export_publishable.py`

Implementa o princípio 3 da Seção 2 do plano: **dois datasets, um de trabalho (com PII) e um
publicável (sem PII bruta)** — o de trabalho nunca é publicado.

### Subcomandos

| Subcomando | O que faz |
|---|---|
| `export` | Lê o CSV de trabalho, escreve o CSV publicável + manifesto JSON |
| `scan` | Varredura de PII em `body_text` — só quantifica, não escreve CSV (usado para gerar os números da Seção 2 deste documento) |
| `self-test` | Teste rápido embutido (fixture sintética, não precisa de `--candidates`) |

### O que `export` faz

1. **Remove `author_name`, `author_login`, `author_email`** do CSV de saída. `author_hash` é
   mantido (`RAW_PII_COLUMNS` / `PUBLISHABLE_COLUMNS` no script).
2. **Mascara PII estrutural em `body_text`** antes de escrever, substituindo cada ocorrência por
   um placeholder (`[PII_EMAIL_REDACTED]`, `[PII_TOKEN_GITHUB_PAT_CLASSIC_REDACTED]`,
   `[PII_COAUTHOR_TRAILER_REDACTED]`, etc.) — ver categorias na Seção 2.
3. **Recalcula `author_hash` só se `--salt` ou `--hmac-key` for passado.** Por padrão (nenhum dos
   dois), `author_hash` é herdado do dataset de trabalho sem alteração — SHA-256 sem salt, o
   mesmo já computado por `ubw.schema.compute_author_hash`. Isso é mecanismo à disposição da
   política, não uma escolha feita aqui (ver Seção 3).
4. **Escreve um manifesto** (`--manifest-json`) com: SHA-256 do CSV de entrada, contagem de
   linhas de entrada/saída, colunas removidas/mantidas, modo de `author_hash`, contagem de PII
   mascarada por categoria em `body_text`, versão do script.

### Self-test (executado nesta sessão — passou)

```
$ python3 06_export_publishable.py self-test
...
SELF-TEST OK — nenhuma coluna/valor de PII bruta sobreviveu; máscara de body_text,
manifesto e recálculo opcional de author_hash (--salt/--hmac-key) se comportaram como esperado.
```

O teste constrói um CSV sintético (2 linhas, PII fake — token `ghp_` inventado, e-mails
`@example.com`, trailers `Co-authored-by`/`Signed-off-by`, uma URL com credencial, uma
`@menção` e, de propósito, `@Override`/`@property` para provar que anotações de código **não**
são destruídas) e verifica, via `assert`:
- nenhuma das 3 colunas de PII bruta sobrevive no header de saída;
- `author_hash` é preservado sem `--salt`/`--hmac-key`, e muda de forma diferente com cada um
  (prova que os dois mecanismos existem e são independentes);
- nenhum segredo/e-mail/nome de trailer sobrevive em texto claro no `body_text` mascarado;
- `@Override`/`@property` (anotação de código, não pessoa) **não** são mascarados — prova que o
  filtro de falsos positivos de menção funciona;
- o manifesto tem as chaves e contagens esperadas;
- `--salt`/`--hmac-key` normalizam case/espaço da mesma forma que
  `schema.compute_author_hash` (preservação de linkage interno — ver Seção 3).

### Rodada real sobre o dataset de trabalho parcial (evidência, não vai para o repositório)

```
$ python3 06_export_publishable.py export \
    --candidates ../data/full_run/ubw_collected_full.csv \
    --out-csv ../data/full_run/ubw_publishable_partial.csv \
    --manifest-json ../data/full_run/ubw_publishable_partial.manifest.json
...
Export concluído: 73412 -> 73412 linhas. Colunas removidas: ['author_name', 'author_login',
'author_email']. author_hash: unsalted_sha256_unchanged. (27,9s; SHA-256 do CSV de 127MB domina
o tempo.)
```

Confirmado manualmente: o header de saída não tem `author_name/author_login/author_email`; 9.217
linhas têm placeholder `[PII_...]` no `body_text` de saída, batendo com a varredura da Seção 2.
`data/full_run/ubw_publishable_partial.csv` e o manifesto ficam fora do controle de versão
(`data/` e `*.csv` estão em `.gitignore`) — é saída de execução, não artefato do repositório.

### Desempenho — achado que vale documentar

A primeira versão rodava 15 `re.sub` sequenciais sobre `body_text` inteiro por linha; extrapolado
para as 73 mil linhas do CSV parcial, isso passava de 45s por chamada (barreira real do ambiente
de execução desta sessão). Um regex único combinado (todas as categorias como alternativas nomeadas
num só padrão) **não ajudou** — o motor de regex do Python ainda tenta cada alternativa em cada
posição do texto, mesmo custo assintótico. O que resolveu: um **pré-filtro de substring barata**
(`"ghp_" in text`, `"AKIA" in text`, etc.) antes de cada `re.sub`, pulando o regex inteiro quando
o texto não tem a menor chance de casar — a maioria das linhas não contém nenhum
token/chave/URL-com-credencial. Resultado: ~150s (estimado) → ~5s no CSV de 73 mil linhas.

---

## 2. Varredura de PII em `body_text` — resultados quantificados

Rodada: `python3 06_export_publishable.py scan --candidates ../data/full_run/ubw_collected_full.csv`,
2026-07-27, **73.412 linhas** (parcial — ver aviso no topo). JSON completo em
`validation/pii_scan_full_run_raw.json`.

### 2.1 Visão geral

| Métrica | Valor |
|---|---|
| Linhas no arquivo | 73.412 |
| Linhas com pelo menos 1 achado de PII em `body_text` | 9.217 (**12,6%**) |
| commit_message | 3.906 / 27.185 (14,4%) |
| issue_body | 2.651 / 15.540 (17,1%) |
| pr_body | 2.064 / 14.504 (14,2%) |
| code_comment | 596 / 16.176 (3,7%) |

`code_comment` tem a menor taxa — esperado, é o único artefato onde `body_text` não é prosa livre
de autor (é o comentário de código em si, já filtrado de vendor/build pelo léxico).

### 2.2 Contagem por categoria (ocorrências, não linhas — uma linha pode ter várias)

| Categoria | Ocorrências | O que é | Confiabilidade do sinal |
|---|---:|---|---|
| `coauthor_trailer` | 15.159 | Linha `Co-authored-by: Nome <email>` inteira | Alta — padrão estrutural fixo do Git/GitHub |
| `signedoff_trailer` | 8.091 | Linha `Signed-off-by: Nome <email>` inteira | Alta — idem (DCO) |
| `mention` | 18.518 | `@handle` (após filtro de ~70 anotações de código conhecidas, ex. `@Override`, `@property`) | **Média** — ver 2.3, ~26% são falso positivo de escopo de pacote npm, não pessoa |
| `email` | 7.949 | E-mail solto (fora de trailer) | Alta |
| `url_credential` | 61 | `scheme://user:senha@host` | Alta |
| `token_jwt` | 29 | Token com formato `eyJ...eyJ...` (3 segmentos base64url) | **Baixa-média** — ver 2.3, inclui falsos positivos de parâmetros de URL não-JWT |
| `token_aws_access_key_id` | 9 | Prefixo `AKIA`/`ASIA` + 16 chars | Alta (formato exclusivo da AWS) |
| `private_key` | 4 | Bloco `-----BEGIN ... PRIVATE KEY-----` | Alta (mas indeterminado se é chave real ou fixture de teste — ver 2.3) |
| `token_generic_bearer` | 4 | `Bearer <token>` | Média — token genérico, sem como confirmar validade |
| `token_github_pat_classic` | 1 | `ghp_...` | Alta (formato exclusivo do GitHub) |
| `token_github_pat_fine_grained`, `token_google_api_key`, `token_slack_token`, `token_stripe_key`, `token_npm_token` | 0 cada | — | — |

**Total de ocorrências mascaradas nesta rodada: 50.816** (soma da tabela). Dominado por
`coauthor_trailer` + `signedoff_trailer` (23.250, ~46% do total) — a implicação prática é que
**remover só as colunas `author_*` não é suficiente**: nome completo + e-mail do(s) coautor(es)
frequentemente reaparecem em texto livre dentro do próprio `commit_message`, exatamente o
cenário que o mandato do plano (item "PII no body_text") pedia para verificar.

### 2.3 Exemplos truncados/mascarados (nunca o segredo/PII inteiro)

- **`coauthor_trailer`** — `"Co-authored-by: <redigido>"` (nome + e-mail nunca reproduzidos).
- **`signedoff_trailer`** — `"Signed-off-by: <redigido>"`.
- **`email`** — `"je…@10up.com"`, `"gm…@gmail.com"` (local-part truncado, domínio preservado —
  domínio sozinho não reidentifica).
- **`url_credential`** — `"http://<credencial_redigida>@localhost:15984…"`; achado real:
  `ansible-collections/community.aws#637` (issue_body) tem uma URL presignada da AWS colada de um
  log de CI, com `X-Amz-Credential=AKIA5Q…` — 8 das 9 ocorrências de `token_aws_access_key_id`
  vêm dessa única issue; a 9ª é de `nextcloud/server#40082`.
- **`token_jwt`** — `"eyJhbG…(len=101)"`. Amostra manual dos 6 primeiros achados: 2 são
  claramente **fixtures de teste** (`auth0/java-jwt`: `static final String TOKEN = "eyJ..."`),
  2 são exemplos colados em relatos de bug (`AzureAD/...`, `grails-spring-security-rest`), e 1 é
  **falso positivo** — `CleverRaven/Cataclysm-DDA`: um parâmetro `dib=` de URL de rastreamento da
  Amazon que por acaso tem o formato de 3 segmentos base64url. Ou seja, a categoria mistura
  segredo real, fixture inócua e falso positivo estrutural — precisa de revisão manual antes de
  qualquer decisão além de mascarar (mascarar por excesso de cautela é seguro; **não** mascarar
  seria o erro caro).
- **`private_key`** — bloco inteiro nunca reproduzido, nem truncado. 3 issues/PRs distintos
  (`brianc/node-postgres#2303`, `esp8266/Arduino#9170`, `rapid7/metasploit-framework#12024`);
  o último em particular (ferramenta de segurança ofensiva) tem probabilidade alta de ser
  fixture/payload de exploit, não segredo real — de novo, indistinguível sem leitura manual, e de
  novo mascarar por padrão é a escolha segura.
- **`mention`** — exemplos: `@0no-co`, `@gql`, `@Dominik1999`. **Achado de falso positivo
  quantificado:** dos ~20.532 handles que casam o padrão `@algo` antes do filtro de anotações de
  código, **5.378 (26,2%) são imediatamente seguidos de `/`** — ou seja, são nomes de escopo de
  pacote npm (`@0no-co/graphqlsp`, `@angular/core`), não menção a uma pessoa. O filtro atual
  (`_MENTION_BLOCKLIST`, ~70 anotações Java/Python/JS conhecidas) não cobre esse caso. Ação
  recomendada para uma iteração futura do script (não feita aqui, para não mudar o mecanismo
  no meio da varredura): excluir `@handle` imediatamente seguido de `/`.
- **`token_generic_bearer`** — `"Bearer…(len=43)"` — categoria mais genérica e mais sujeita a
  falso positivo (qualquer string após "Bearer " conta); tratar como sinal fraco.

### 2.4 Limitações conhecidas da varredura (declarar, não esconder)

- **Nomes em texto livre fora de `@menção`/trailer não são detectados.** Ex.: "thanks John for
  the fix" — sem NER, um detector baseado em regex estrutural não pega isso. Os `body_text` de
  `issue_body`/`pr_body` certamente têm nomes soltos não cobertos; isso é uma lacuna real, não uma
  omissão de relatório.
- **Segredos sem prefixo reconhecível não são cobertos** (ex.: `password = "hunter2"`,
  `api_key: "abc123"` genérico) — cobertura restrita a formatos com prefixo estruturado
  (`ghp_`, `AKIA`, `AIza`, `xox`, `sk_live_`/`sk_test_`, `npm_`, `eyJ...`, `Bearer `,
  `-----BEGIN...PRIVATE KEY-----`) para manter baixo risco de falso positivo massivo; segredos
  genéricos exigiriam heurística de contexto (nome de variável + atribuição), fora do escopo
  desta rodada.
- **`@menção` tem ~26% de falso positivo por escopo npm** (ver 2.3) — a contagem de 18.518 deve
  ser lida como teto, não como "18.518 pessoas mencionadas".
- **`token_jwt`/`token_generic_bearer`/`private_key` não distinguem segredo real de fixture de
  teste/exploit** — mascarar por padrão é a escolha segura, mas os números não devem ser lidos
  como "N segredos vazados", e sim "N candidatos que merecem não aparecer em texto claro na
  versão publicável".
- **Coleta parcial.** Estes números cobrem só a fatia A, e só até onde a coleta chegou nesta
  sessão. Recontar depois da consolidação fatia A + B.

---

## 3. `author_hash` — opções de salt, sem decisão

O schema já registra isto (`ubw/schema.py`, comentário acima de `compute_author_hash`):
`author_hash` hoje é **SHA-256 sem salt** do identificador mais forte disponível (e-mail > login >
nome, normalizado). O script implementa duas alternativas, **ambas desligadas por padrão**:

### (a) Manter sem salt (padrão atual, `--salt`/`--hmac-key` ausentes)

- **O que é:** pseudonimização declarada, não anonimização formal. Qualquer pessoa com acesso à
  lista de candidatos plausíveis (o próprio GitHub é público) pode calcular SHA-256 do e-mail/login
  de um usuário conhecido e comparar com `author_hash` — ataque de dicionário trivial, sem
  força bruta necessária, porque o espaço de "e-mails/logins do GitHub" é enumerável.
- **Efeito em RQ3 (linkage):** preserva 100% do linkage — o mesmo hash sempre corresponde ao mesmo
  autor, e **qualquer pessoa** pode reproduzir esse linkage externamente (não só o time do UBW).
- **Efeito na extensão humano vs. IA (Seção 6 do plano):** preserva a possibilidade de cruzar
  `author_hash` com metadados externos de autoria (ex.: bots de IA identificáveis por padrão de
  commit) sem precisar da chave/segredo do UBW — qualquer pesquisador terceiro poderia reproduzir
  esse cruzamento de forma independente, o que é bom para reprodutibilidade mas ruim para
  privacidade dos autores reais.

### (b) `--salt <valor>` — SHA-256(salt + identificador)

- **O que é:** ainda reidentificável por dicionário se o salt vazar (ou for adivinhado — um salt
  curto/óbvio não muda a categoria de risco); a única diferença de (a) é que quem tenta reidentificar
  precisa conhecer o salt exato. Não é criptograficamente equivalente a HMAC (SHA-256 com prefixo
  concatenado tem histórico de ataques de extensão de comprimento em outros contextos, embora não
  se aplique diretamente aqui já que não há verificação de integridade envolvida).
- **Efeito em RQ3:** preserva linkage interno **desde que o mesmo salt seja usado
  consistentemente** entre exports — o script normaliza case/espaço da mesma forma que
  `compute_author_hash`, então "Jane Doe" com variações de capitalização ainda cai no mesmo hash
  salgado (verificado no self-test).
- **Efeito na extensão humano vs. IA:** um terceiro sem o salt não consegue reproduzir o linkage
  externo — reduz reprodutibilidade para quem não tem acesso ao segredo, mas isso é justamente o
  ponto de privacidade.

### (c) `--hmac-key <segredo>` — HMAC-SHA256(chave, identificador)

- **O que é:** mais forte que (b) contra ataque de dicionário — HMAC é projetado para resistir a
  isso mesmo com o algoritmo hash público, **desde que a chave permaneça secreta** (ao contrário
  do salt, que só precisa ser "desconhecido", a garantia formal do HMAC depende de a chave nunca
  vazar). Sem a chave, reidentificação por lista de candidatos deixa de ser viável na prática.
- **Efeito em RQ3 — ponto que o mandato pediu para destacar:** **HMAC com chave FIXA preserva
  linkage interno integralmente** (mesma propriedade determinística de (a)/(b): mesmo autor →
  mesmo hash, sempre, enquanto a chave não mudar). A troca não é "perder a capacidade de ligar o
  mesmo autor entre registros" — é perder a capacidade de um **terceiro sem a chave** fazer esse
  linkage. Quem tem a chave (o time do UBW, para a survey de RQ3) mantém 100% do linkage interno
  necessário para RQ3; quem baixa o dataset publicável não consegue.
- **Efeito na extensão humano vs. IA:** mesma lógica — o time do UBW pode cruzar `author_hash`
  publicável com metadados internos (a lista de candidatos original, mantida só no dataset de
  trabalho) para a extensão humano/IA; um terceiro reproduzindo só a partir do CSV publicável não
  consegue, o que é aceitável porque essa extensão é trabalho futuro do próprio grupo, não um
  requisito de reprodutibilidade externa.

### Resumo para a política decidir

| Opção | Reidentificável por terceiro com lista de candidatos? | Linkage interno (RQ3) preservado? | Linkage externo reproduzível por terceiro? |
|---|---|---|---|
| Sem salt (padrão atual) | **Sim, trivialmente** | Sim | Sim |
| `--salt` | Só se o salt vazar/for adivinhado | Sim (mesmo salt entre exports) | Não, sem o salt |
| `--hmac-key` | Não, na prática, enquanto a chave for secreta | Sim | Não, sem a chave |

Nenhuma das três é "a errada" — é trade-off entre reprodutibilidade externa (favorece (a)) e
proteção dos autores identificados (favorece (c)), e cabe à política (com aval de ética/LGPD)
decidir. O mecanismo para aplicar qualquer uma das três já está pronto e testado.

---

## 4. Entregas desta rodada

- `scripts/06_export_publishable.py` — script de export com `export`/`scan`/`self-test`.
  Self-test passou (Seção 1).
- Este documento (`validation/D1_EXPORT_PII_FINDINGS.md`).
- `validation/pii_scan_full_run_raw.json` — saída bruta (JSON) da varredura, para auditoria dos
  números da Seção 2.
- **Não versionado** (por design — `.gitignore`): `data/full_run/ubw_publishable_partial.csv` e
  `.manifest.json`, gerados nesta sessão como prova de que `export` roda de ponta a ponta sobre
  dados reais (parciais).
