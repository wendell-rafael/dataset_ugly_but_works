# Espelho publicável de `validation/`

Cópias sem PII dos 34 arquivos de validação que não podem ser versionados como
estão. Geradas por `scripts/16_mascara_validation.py`; **não editar à mão** —
rodar o script de novo.

O repositório é público. Os originais seguem em disco como versão de trabalho,
fora do git (enumerados um a um no `.gitignore` da raiz).

## O que muda em relação ao original

**`body_text` mascarado** pelo mesmo mascarador do export do corpus
(`scripts/06_export_publishable.py:apply_pii_masking`), para os dois artefatos
não divergirem em política. Nesta rodada: **1.424 e-mails** e **771 menções**
substituídos por placeholder, em 34 arquivos.

O e-mail vinha do texto do próprio artefato coletado, em trailers
`Signed-off-by:` e `Co-authored-by:`. A forma que aparecia, com o endereço
substituído aqui também:

```
antes:   ...setup of the i2s block.Signed-off-by: Nome do Autor <ENDEREÇO>
depois:  ...setup of the i2s block.Signed-off-by: Nome do Autor <[PII_EMAIL_REDACTED]>
```

Esta era a parte não óbvia do problema: **nenhuma coluna se chama "email"**, e
só 5 dos 34 arquivos têm coluna `author_*`. Checar cabeçalho de CSV não acha os
outros 23.

**As quatro colunas de identidade removidas** — `author_name`, `author_login`,
`author_email`, `author_hash` — nos 5 arquivos que as tinham
(`sample_final_v2/*` e `sample_code_comment/amostra_code_comment.csv`).

`author_hash` sai junto das outras três de propósito. É SHA-256 **sem salt** do
e-mail ou do login (`ubw/schema.py:compute_author_hash`), e o próprio schema o
descreve como "reidentificável com uma lista de candidatos". Lista de logins do
GitHub é trivial de obter, então em repositório público a pseudonimização não se
sustenta. Nas amostras de validação a identidade do autor não entra em nenhuma
análise, logo não há o que perder removendo.

## Critério de seleção

Entra no espelho todo arquivo com e-mail literal em qualquer campo, com coluna
`author_*`, **ou com coluna `body_text`** — este último mesmo sem e-mail hoje.
"Não tem e-mail agora" não é garantia se o arquivo for regerado a partir do
corpus; selecionar por conteúdo atual deixaria um arquivo de fora sempre que a
amostra mudasse. Foi o caso de `batches_3anotadores/REVISAO_385_nao_unanimes.csv`,
que tem `body_text` e zero e-mails.

## Verificação

`manifest.json` traz, por arquivo: sha256 de origem e de saída, contagem de
máscaras por tipo, colunas removidas, e `emails_restantes` (vazio em todos).

Para conferir de forma independente:

```bash
python3 scripts/14_check_pii.py $(find validation/publicavel -type f)
```

O guard varre e-mail literal em qualquer campo, não só nome de coluna, e sai com
código 1 se achar algo.

## O que este espelho não resolve

Os `body_text` seguem sendo texto de repositórios públicos identificáveis, com
URL e nome de repo preservados. Isso é dado público, mas a anotação acrescenta um
juízo ("este código é feio") atrelado a commit identificável — a questão ética
levantada em `../CHECKLIST_ETICA_RQ3.md`, que é decisão de política, não de
script. Ver também `../POLITICA_ANONIMIZACAO.md` e `../D1_EXPORT_PII_FINDINGS.md`.
