# Análise de erro — meta_llama_llama_3_3_70b_instruct_fewshot_fixed

Conjunto `gold_dev_200`: 200 itens, 173 positivos e 27 negativos no gabarito humano.
O juiz erra em **19 itens (9.5%)**, contando abstenção como não-alerta.

## Tipo de erro

| tipo                               |   itens |
|:-----------------------------------|--------:|
| deixou passar (FP não detectado)   |      12 |
| alerta indevido (item bom marcado) |       7 |

## Onde o erro se concentra

### Por tipo de artefato

| artifact_type   |   itens |   erros |   taxa_erro |
|:----------------|--------:|--------:|------------:|
| code_comment    |      57 |       0 |       0     |
| commit_message  |      95 |      14 |       0.147 |
| pr_body         |      48 |       5 |       0.104 |

### Por expressão do léxico (só as com 5+ itens)

| matched_expression   |   itens |   erros |   taxa_erro |
|:---------------------|--------:|--------:|------------:|
| quick and dirty      |      22 |       3 |       0.136 |
| ugly hack            |      19 |       2 |       0.105 |
| dirty hack           |      11 |       1 |       0.091 |
| temporary fix        |      68 |       6 |       0.088 |
| stopgap              |      24 |       2 |       0.083 |
| temp fix             |      24 |       2 |       0.083 |
| this is a hack       |      14 |       0 |       0     |

### Por comprimento do texto

- Mediana de caracteres nos itens **certos**: 309
- Mediana de caracteres nos itens **errados**: 137

### Sobreposição com a discordância humana

| Itens | Total | Erros do juiz | Taxa |
|---|---|---|---|
| Humanos **unânimes** | 188 | 14 | 7.4% |
| Humanos **divergiram** | 12 | 5 | 41.7% |

Se a taxa de erro é muito maior onde os humanos divergiram, o juiz está errando na zona de ambiguidade genuína do critério, não em casos claros — leitura mais branda do erro.

## Exemplos — justificativa do modelo vs. do anotador

**`stopgap`** · commit_message · humano: **UBW-verdadeiro** · modelo: **não-UBW**

> Dev (#8185)* added cpp client build docs (#7942)* fixed IMU units (#7960)* Update README.md with new TinyURL links (#7988)* Added inverse transform (#7999)Co-authored-by: glopezdiest <[PII_EMAIL_REDACTED]>* Aaron/fixwheelchair (#8001)* Fix OSM2ODR build* Updated

- *Modelo:* A expressão 'stopgap' não está presente no trecho fornecido, o que indica que o disparo foi falso positivo ou o trecho não contém a expressão que disparou a coleta.
- *Anotador:* ""This makes evident that this is a stopgap measure, and should be looked into further down the line

**`ugly workaround`** · commit_message · humano: **não-UBW** · modelo: **UBW-verdadeiro**

> Bumping gaia.json for 3 gaia revision(s) a=gaia-bump========https://hg.mozilla.org/integration/gaia-central/rev/a7eca2fffd83Author: Rick Waldron <[PII_EMAIL_REDACTED]>Desc: Bug 957714 - [Messages] Interacting with message field prevents recipients field from

- *Modelo:* O trecho contém a expressão 'ugly workaround' e o contexto indica que o autor admite ter implementado uma solução tecnicamente subótima para resolver o Bug 956811, caracterizando uma resignação funcional.
- *Anotador:* Não entendi seesse commit resolve um bug com ugly workaround, ou se ele implementa um ugly workaround para resolver um bug

**`temporary fix`** · commit_message · humano: **não-UBW** · modelo: **UBW-verdadeiro**

> fix new chat regression (#305151)* Sessions - temporary fix* better fix---------Co-authored-by: Ladislau Szomoru <[PII_EMAIL_REDACTED]>

- *Modelo:* O trecho expressa claramente uma solução temporária e subótima, indicada pela expressão 'temporary fix', que é usada para descrever a solução adotada para um problema de regressão no chat.
- *Anotador:* Não consegui identificar se a mensagem do commit indica que uma solução melhor foi adicionada no lugar de uma solução ubw ou se a essa solução ubw ainda permanece no código.

**`workaround for now`** · pr_body · humano: **não-UBW** · modelo: **UBW-verdadeiro**

> Resolves #39201## SummaryWhen an export specifier name (`as`) shadows an import-default name (`name`), then the resulting `name` would be replaced with a namespace member access. However, member accesses of `.default` are never valid, since they can CommonJS-b

- *Modelo:* O trecho expressa claramente uma solução temporária e subótima, com a autora admitindo que o 'workaround, for now' é necessário devido a limitações na implementação atual, indicando resignação funcional.
- *Anotador:* resolvido em calibração (convergiu com Wendell)

**`temporary fix`** · commit_message · humano: **UBW-verdadeiro** · modelo: **não-UBW**

> fix: ensure Celery tasks are registered at worker startup (main) (#63110)* fix: ensure Celery tasks are registered at worker startupFixes: #63043* fix: add test for celery task registration on import* remove temporary fix scripts* chore: add TODO comment for e

- *Modelo:* A expressão 'temporary fix' está relacionada a scripts que foram removidos, indicando que a solução temporária foi substituída, e não que uma solução feia ou um workaround foi mantida porque funciona.
- *Anotador:* resolvido em calibração (convergiu com Wendell)

**`quick and dirty`** · pr_body · humano: **UBW-verdadeiro** · modelo: **não-UBW**

> Quick and dirty draft upload to have a point-of-reference for the core meeting. Will give a more thorough description after the fact

- *Modelo:* A expressão 'quick and dirty' é usada para descrever a qualidade da descrição do draft upload, não uma solução técnica, e o contexto não indica resignação funcional em relação a uma solução feia ou um workaround.
- *Anotador:* resolvido em calibração (convergiu com Wendell)

**`dirty hack`** · commit_message · humano: **não-UBW** · modelo: **UBW-verdadeiro**

> package fix (tmp, dirty hack)

- *Modelo:* O trecho contém a expressão 'dirty hack' junto com 'tmp', indicando uma solução temporária e tecnicamente subótima, aceita por funcionar. O contexto de commit de pacote sugere uma solução provisória, característica de um 'Ugly But It Works'.
- *Anotador:* resolvido em calibração (convergiu com Wendell)

**`temp fix`** · commit_message · humano: **não-UBW** · modelo: **UBW-verdadeiro**

> Merge pull request #559 from enriquebelarte/temp-fix-libdnfTemporary fix for bootc CI builds

- *Modelo:* O trecho expressa claramente uma solução temporária e subótima, indicada pela expressão 'Temporary fix', que é usada para descrever a mudança feita no código, sugerindo que a solução adotada é provisória e pode não ser ideal, mas funciona para o momento.
- *Anotador:* resolvido em calibração (convergiu com Wendell)
