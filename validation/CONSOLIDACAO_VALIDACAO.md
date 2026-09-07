# Consolidação — Parecer de Validade do Dataset UBW

Consolidação das entregas dos 4 agentes do `PLANO_VALIDACAO_COWORK.md`,
executados em 2026-07-27. Alimenta a seção de ameaças à validade da dissertação.

**Estado dos dados no momento da execução:** `COLLECTION_COMPLETE` ausente —
coleta da fatia A em andamento (73.412 registros / 16.614 repos no CSV parcial),
fatia B em outra máquina. Por isso, o Agente B rodou em **modo preparação** (spec
e scripts prontos, nenhuma amostra oficial fechada), conforme o Risco 2 do plano.

## Entregas por agente

| Agente | Modelo | Entrega |
|---|---|---|
| A · Literatura | Fable | `A_REVISAO_LITERATURA.md` |
| B · Falsos positivos (preparação) | Sonnet | `B_PLANO_AUDITORIA_FP.md` + `scripts/03b/03c/03d` + `gold_set/gold_set_v0_seed.csv` |
| C · Mineração | Sonnet | `RELATORIO_QUALIDADE_DADOS.md` + `c_audit_checks.py` |
| D · Anonimização & ética | Sonnet (script) + Fable (política) | `scripts/06_export_publishable.py` + `D1_EXPORT_PII_FINDINGS.md` + `POLITICA_ANONIMIZACAO.md` + `CHECKLIST_ETICA_RQ3.md` |

---

## 1. Veredito geral

O protocolo UBW já está no padrão do campo ou acima (2 anotadores + desempate,
~385 estratificados, κ+AC1, calibração, triagem LLM com descarte se κ<0,61), e a
lacuna de pesquisa se confirma: a SLR arXiv 2312.15020 mostra que nenhum
trabalho mede precisão de "resignação funcional" isoladamente. Os problemas
encontrados são corrigíveis por código antes da consolidação — nenhum invalida a
coleta, mas dois (repo_age_days e bots) contaminariam análises de RQ2 e a
amostra de validação se não forem tratados agora.

## 2. Achados críticos (validade interna — Agente C)

1. **`repo_age_days`/`time_to_event_days` incoerentes em 27,8% das linhas
   (20.434)** — ALTA. Duas causas com evidência de código: `get_first_commit_date()`
   usa `git log --reverse` sem `--all` enquanto a busca de eventos usa `--all`
   (afeta 84% dos `code_comment` flagados); e `repo_age_days` vem do `created_at`
   da entidade GitHub, não do histórico git real (projetos importados/era CVS —
   há até um `created_at` na época Unix). **Contamina o covariável do Cox de
   RQ2.** Correção: alinhar `--all` e documentar a limitação do `repo_age_days`
   derivado de API.
2. **Filtro de bot vaza 715 linhas (0,97%)** — ALTA. `_is_bot_login` só pega
   `[bot]` e 6 nomes exatos; `pyup-bot` sozinho = 277 linhas (changelog de
   terceiro em PR de bump — falso positivo de construto por definição).
   Correção: sufixos `-bot`/`-robot`/`[bot]` + checar `author_name`.
3. **Vendoring residual: 3,99% dos `code_comment` (644/16.160)** — ALTA. Eigen,
   Boost, googletest etc. sob paths genéricos fora de `VENDORED_PATH_MARKERS`.
   Promover os candidatos ao filtro após revisão manual.
4. **Duplicatas: 4,39% de `body_text` exato por repo+artefato** (maioria
   `commit_message`, cherry-picks de import CVS) **+ 11 pares cross-artefato**
   (squash-merge duplica commit_message→pr_body) — MÉDIA. A dedup precisa rodar
   **antes** da amostragem do B.
5. **Positivo:** a correção de contaminação por arquivo gerado/build de
   2026-07-14 segura em escala 20x (0/16.160).
6. Checagens Zampetti (remoção acidental) e reprodutibilidade não puderam ser
   executadas no sandbox (sem token GitHub / limite de fetch); procedimento
   completo implementado em `c_audit_checks.py` para rodar pós-consolidação.

## 3. Validade de construto (Agente B, preparação)

- **Divergência plano × léxico:** o mandato pedia sobre-amostrar `magic number`
  e `don't touch`, mas ambas foram **removidas do léxico em 2026-07-01** (0/22 TP
  no piloto). A regra virou mecânica: sobre-amostrar `HIGH_RISK_EXPRESSIONS` OU
  qualquer expressão com <50 candidatos — o que capturou casos não previstos
  (`terrible but works`=4, `horrible but works`=9).
- **Gap inesperado:** não existia geração de batch/`annotation_template.csv` no
  repo, apesar de o plano assumir que existia. Criado (`03c`), sem vazar
  `llm_label` ao anotador.
- O script 03 já cobria κ/AC1 e o κ de categoria restrito aos TPs; faltavam e
  foram entregues como scripts novos (03 intocado): censo da categoria C (253
  itens no parcial), piso de raridade, near-misses adversariais mecânicos (6
  heurísticas dos negativos do guideline, ~100 itens), IC de Wilson,
  reponderação da precisão global, correção de população finita, calibração
  (200 = 50×4 artefatos) fora do κ final.
- **Gold set v0** semeado com os 14 itens do guideline
  (`validation/gold_set/gold_set_v0_seed.csv`) — vira teste de regressão para
  qualquer mudança futura de léxico/prompt/modelo.
- Unidades delegáveis a modelo barato pós-consolidação, com verificador:
  (a) `03b_final_sampling.py`, (b) `03c_generate_batches.py`, (c) anotação
  humana → `03d_precision_report.py`.

## 4. Anonimização & ética (Agente D)

- **Remover as colunas `author_*` não basta:** 12,6% das linhas têm PII no
  `body_text` — dominado por 23.250 trailers `Co-authored-by`/`Signed-off-by`
  (nome completo + e-mail, muitos de terceiros), 7.949 e-mails soltos, 61 URLs
  com credencial, tokens/chaves (incl. 1 `ghp_`, 9 AKIA/ASIA, 4 blocos de chave
  privada). O script `06_export_publishable.py` mascara tudo isso (self-test com
  10 asserções passando) e gera manifesto.
- **Recomendação de salt (ao orientador): `--hmac-key`** (HMAC-SHA256, chave
  ≥256 bits, fixa entre exports). Ponto que desfaz o trade-off registrado no
  plano: HMAC com chave fixa **preserva 100% do linkage interno** (mesmo autor →
  mesmo hash), então RQ3 e a extensão humano-vs-IA não perdem nada — o contato
  da survey usa a tabela de correspondência (dataset de trabalho), não o hash.
  Sem salt, o hash é reidentificável por dicionário sobre o espaço enumerável de
  logins do GitHub (GDPR Recital 26 / LGPD art. 13). `--salt` simples é dominado.
  Custódia: chave em duas cópias (pesquisador + orientador), nunca no repo.
- **O publicável é declarado pseudonimizado, não anônimo** — `body_text` é
  buscável no GitHub (limitação estrutural, declarada à la Gold & Krinke, com
  linha vermelha explícita contra profiling de indivíduos).
- **Segredos vivos:** nunca republicar nem testar validade; disclosure
  responsável para os plausivelmente vivos (ex.: URL presignada AWS em
  `ansible-collections/community.aws#637`).
- **CEP/Plataforma Brasil:** dispensa do art. 1º da CNS 510/2016 **não** se
  aplica (participantes identificáveis pelo e-mail de commit). Caminho realista:
  3–5 meses até parecer; nenhum e-mail antes da aprovação; TCLE eletrônico
  (Carta CONEP 1/2021). Iniciar em paralelo à anotação para não virar gargalo.

## 5. Recomendações priorizadas (cross-agente)

**Antes de consolidar as fatias (bloqueiam a amostragem):**
1. Corrigir `get_first_commit_date()` (`--all`) e documentar `repo_age_days` (C).
2. Endurecer o filtro de bot e definir política excluir-vs-marcar (C).
3. Revisar e promover os 644 candidatos a vendoring ao filtro (C).
4. Dedup por repo+artefato e cross-artefato antes do `03b` (C→B).

**No fechamento da amostra (pós-`COLLECTION_COMPLETE` + fatia B):**
5. Congelar amostra só sobre o consolidado; censo da categoria C; calibração
   fora do κ final; reportar concordância bruta + prevalência junto do κ (A→B).
6. Rodar Zampetti e reprodutibilidade com token GitHub (`c_audit_checks.py`) (C).

**Decisões do orientador (não dos agentes):**
7. Salt: adotar `--hmac-key` conforme `POLITICA_ANONIMIZACAO.md` (D).
8. Política de bots (excluir vs. marcar) (C).
9. Qualquer ajuste de léxico que sair das precisões por expressão (B) — léxico
   segue congelado.
10. Submissão ao CEP: disparar cedo, caminho crítico de 3–5 meses (D).

**Correções menores:** Awon (2024) parece ser tese de doutorado (UVic), não
mestrado como no `plano.md` — a confirmar (A, P11).

## 6. Sequenciamento pós-consolidação

```
COLLECTION_COMPLETE + fatia B
  → correções C (bots, vendoring, dedup, datas)   [código, não CSV]
  → 03b (amostra final + pesos)  → 03c (batches)
  → anotação humana (2 + desempate; gargalo real)
  → 03d (κ/AC1, Wilson, precisão reponderada, especificidade)
  → gold set v1  → export publicável (06, com HMAC se aprovado)
Em paralelo desde já: submissão CEP (3–5 meses).
```
