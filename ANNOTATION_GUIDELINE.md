# Guideline de Anotação — Dataset UBW (Ugly But It Works)

**Protocolo formal para anotadores humanos — Seção 5.4 do plano de experimento**

---

## 1. Objetivo

Este documento define como decidir, de forma consistente entre anotadores, se um trecho
coletado automaticamente (via léxico, Seção 3.2) é de fato uma instância de **UBW —
resignação funcional**: um(a) desenvolvedor(a) admitindo, no próprio texto, que manteve
uma solução tecnicamente subótima porque ela cumpre a função.

Cada item anotado recebe **dois rótulos independentes**:

| Rótulo | Domínio | Descrição |
|---|---|---|
| `is_ubw` | booleano | O item é genuinamente uma instância de UBW? |
| `confidence` | `certo`, `provável`, `incerto` | Grau de confiança na própria decisão |

**Nota importante:** A categorização semântica (A, B, C) ainda aparece como `category_ubw` no
CSV — trata-se de metadados de proveniência do léxico, **não de uma tarefa de anotação**. O(a)
anotador(a) não classifica nem confirma categoria; a coluna serve apenas para rastreabilidade
do léxico (Seção 3.2 do plano de experimento).

**O que este guideline NÃO faz:** substituir julgamento humano por regras mecânicas. As
regras abaixo existem para reduzir divergência arbitrária entre anotadores, não para
eliminar a necessidade de leitura do contexto.

---

## 2. Papel do(a) anotador(a) no pipeline

```
Léxico (Seção 3.2) → N candidatos → Pré-triagem LLM (Seção 5.6) → "incerto" (LLM) → OBRIGATÓRIO revisão humana
                                                                  → amostra 15% do resto → revisão humana
                                                                  → restante → aceito com rótulo do LLM
        Amostra estratificada (~385 itens, Seção 5.2) ──────────────────────→ SEMPRE revisão humana
```

A pré-triagem por LLM **nunca é definitiva por si só** para a amostra usada nas métricas
de precisão e concordância (Seção 5.1/5.6). O(a) anotador(a) humano(a) é sempre a
referência (*ground truth*) contra a qual o léxico e o LLM são avaliados.

---

## 3. Processo (Seção 5.4)

Protocolo de três anotadores com duas fases:

1. **Leitura deste guideline**, incluindo todos os exemplos da Seção 6.

2. **Calibração (200 itens):** estratificado por tipo de artefato. Cada um dos três
   anotadores preenche de forma **independente**, sem trocar ideias. Quando os três
   terminarem, marcamos uma sessão de discussão conjunta para os casos com divergência.
   O objetivo é alinhar critério — essa discussão quebra a independência, então os itens de
   calibração são excluídos de todas as métricas de concordância/precisão (validação posterior).
   Awon (2024) obteve κ = 0,926 com esse protocolo; Maldonado & Shihab (2015) reportam
   redução de até 30% nas divergências residuais.

3. **Medição (200 itens, os mesmos três anotadores):** preenchido de forma **independente**
   novamente, sem consultar os colegas **e sem discussão posterior**. Essas 200 respostas são
   as que medem concordância (κ de Cohen e AC1 de Gwet) entre os três anotadores.

4. **Paralelização (restante da amostra):** cada um dos três anotadores cobre um pedaço
   não-sobreposto (sem consultar os outros). A confiabilidade desses rótulos únicos já foi
   validada na etapa de medição — se a concordância ali foi alta, é seguro confiar em um
   único anotador para os itens de paralelização.

5. Cálculo de concordância (κ de Cohen e AC1 de Gwet) sobre os itens de medição apenas
   (script `03d_precision_report.py report`).

**Regra dura:** nunca altere seu próprio rótulo depois de ver o rótulo de outro
anotador, exceto na discussão de calibração (que é explícita e coletiva). Fazer isso
durante medição ou paralelização invalida a medição de concordância.

---

## 4. Definição operacional geral de UBW

Um item é `is_ubw = True` **somente se todas** as condições abaixo forem satisfeitas:

1. **Auto-admissão.** A pessoa autora do texto está falando sobre uma decisão *dela
   própria* (ou da equipe, no mesmo repositório) — não descrevendo, de forma abstrata
   ou de terceiros, uma prática geral de engenharia de software.
2. **Trade-off explícito entre forma e função.** O texto contrasta, implícita ou
   explicitamente, a qualidade da solução ("feio", "hack", "workaround", "não ideal",
   "provisório") com o fato de que ela funciona / resolve o problema / não será mexida.
   Não basta admitir que o código é ruim — é preciso haver, no mesmo trecho, a
   resignação de mantê-lo assim mesmo.

   **Marcador puramente temporal conta como satisfazendo esta condição.** Um trecho
   como "temporary fix for X" ou "temp fix", sem nenhum outro juízo de qualidade,
   já expressa o trade-off: a pessoa admite que a solução não é a definitiva e a
   introduz mesmo assim, porque resolve o problema agora. Decisão registrada em
   2026-08-19, após observar que essa foi a leitura praticada de forma consistente
   pelos três anotadores na amostra oficial (prevalência de 92,2% de `True`,
   incluindo os itens só-temporais). Esta nota resolve a divergência entre o texto
   original desta condição — mais estrito, exigindo resignação explícita além do
   marcador temporal — e a prática de anotação já realizada.
3. **Referência concreta a código/design real neste repositório.** Deve haver um
   deítico (este método, esta função, aqui, essa linha, esse PR) ligando a afirmação a
   uma instância real de código — não uma reflexão genérica sobre a profissão.
4. **Sem negação.** "Isto NÃO é um hack sujo" não é UBW — é o oposto.
5. **Não é ruído de correspondência lexical.** A expressão não está dentro de uma
   string literal de teste, fixture, docstring de terceiros, citação, nome de
   variável/função, ou comentário irônico sem relação com o código real.

Se qualquer uma dessas condições falhar → `is_ubw = False`.

---

## 5. Contexto — Como as categorias surgiram no léxico (referência apenas)

> **IMPORTANTE:** As categorias A, B, C descritas abaixo **não são uma tarefa de anotação**.
> Elas existem no léxico (Seção 3.2 do plano) porque ajudaram a organizar a construção do
> léxico lexicográfico. A coluna `category_ubw` que aparece no CSV é metadados — o(a)
> anotador(a) não confirma nem classifica categoria. Esta seção é para referência apenas,
> para que você entenda melhor o que a expressão matched no seu item tenta capturar.
>
> Referência lexical completa: Seção 3.2 do plano. O critério é o **traço dominante do
> argumento do autor**, não apenas qual palavra do léxico disparou a coleta.

### Categoria A — Julgamento estético e hacks explícitos
**Traço dominante:** a crítica é sobre a *forma* do código (feio, hack, bagunçado),
sem ênfase relevante em urgência temporal ou em incerteza sobre o sistema.

- Teste operacional: se você reescrevesse a frase substituindo o adjetivo estético por
  "isso é feio", o sentido da frase se mantém quase intacto → provavelmente A.

### Categoria B — Workarounds e urgência
**Traço dominante:** a solução é enquadrada como *temporária, emergencial ou paliativa*
— resolve o sintoma, não a causa raiz — com sinalização de que "isso deveria ser
revisado depois" (mesmo que nunca seja).

- Teste operacional: a frase contém (explícita ou implicitamente) uma referência a
  tempo/urgência ("por enquanto", "para não travar o release", "depois eu arrumo",
  "gambiarra", "remendo") → provavelmente B.

### Categoria C — Resignação funcional e incerteza
**Traço dominante:** aceitação vaga de uma solução subótima, frequentemente ligada a
**não entender totalmente o sistema** ou a **medo de causar regressão** ao mexer —
não necessariamente uma crítica estética específica nem uma alegação de urgência.

- Teste operacional: a frase poderia ser resumida como "não sei por que isso funciona
  / tenho medo de mexer / não é o ideal, mas não vou arriscar mudar" → provavelmente C.

### Tabela-resumo

| | A — Estética | B — Workaround/urgência | C — Incerteza/resignação |
|---|---|---|---|
| Ênfase | Forma do código | Tempo / provisoriedade | Compreensão / risco |
| Verbo típico | "é feio, é um hack" | "resolve por agora" | "não sei bem por quê, não mexer" |
| Expressões-âncora | `dirty hack`, `this is a hack`, `messy but works` | `band-aid fix`, `quick and dirty`, `duct tape fix` | `magic number` ⚠, `don't touch` ⚠, `hope everything will work` |
| Risco de falso positivo | Baixo | Médio | Alto |

---

## 6. Exemplos por categoria e tipo de artefato

Cada bloco mostra um exemplo **positivo** (`is_ubw = True`) e um **negativo** (near-miss,
`is_ubw = False`) para ilustrar a fronteira de decisão — o negativo quase sempre contém
a mesma expressão do léxico, para forçar o julgamento pelo contexto.

### 6.1 Categoria A

**`code_comment` — positivo**
```python
# ugly but it works: parsing manualmente porque a lib de XML trava com
# encoding latin-1 e não vamos trocar de lib agora.
def parse_legacy_xml(raw: bytes) -> dict:
    ...
```
→ `is_ubw=True`, `confidence=certo`
(contexto: expressão do léxico Categoria A — forma estética — mas você não preenche isso)

**`code_comment` — negativo (string de teste)**
```python
def test_error_message_for_bad_config():
    with pytest.raises(ConfigError) as exc:
        load_config("bad.yaml")
    assert str(exc.value) == "this is a hack, please fix your config"
```
→ `is_ubw=False` (a expressão é o *conteúdo* de uma mensagem de erro testada, não uma
admissão do autor sobre o próprio código) — `confidence=certo`

**`commit_message` — positivo**
```
fix(auth): dirty hack to bypass token refresh race condition

Not proud of this, but it stops the 500s in prod. Will revisit after
the SSO migration.
```
→ `is_ubw=True`, `confidence=certo`
(contexto: léxico marca como Categoria A, mas tem traços de B também — você não resolve isso)

**`issue_body` — negativo (citação de terceiro)**
```
O revisor comentou no PR #482 que a implementação anterior era "a dirty
hack", e por isso pedimos para reabrir esta issue e refazer do zero.
```
→ `is_ubw=False` (a expressão descreve uma solução que está sendo **rejeitada e
substituída**, não mantida — falha a condição 2 da Seção 4: não há resignação, há
correção ativa)

### 6.2 Categoria B

**`pr_body` — positivo**
```
## O que este PR faz
Aplica um band-aid fix no cálculo de frete: quando o CEP não é
encontrado, usamos o frete médio nacional em vez de falhar o checkout.

Sei que isso é só um workaround — a correção de verdade é revisar toda
a integração com os Correios, que não cabe neste sprint.
```
→ `is_ubw=True`, `confidence=certo`
(contexto: léxico marca como Categoria B — urgência/temporário)

**`pr_body` — negativo (workaround de terceiro, fora do controle do autor)**
```
Este PR atualiza a dependência `libfoo` para 3.2.1, que corrige o bug
onde a própria lib usava um workaround feio para lidar com timezones.
```
→ `is_ubw=False` (o "workaround feio" é de código de terceiros que está sendo
**removido pela atualização** — não é uma decisão do autor de manter algo assim)

**`code_comment` — positivo**
```java
// quick and dirty: cache em memória sem TTL. Se o processo reiniciar
// pouco, tudo bem; se não, isso vira memory leak. Aceitável por agora.
private static final Map<String, Object> cache = new HashMap<>();
```
→ `is_ubw=True`, `confidence=certo`
(contexto: léxico marca como Categoria B — urgência/temporário)

**`commit_message` — negativo (negação)**
```
refactor(payments): remove duct tape fix from retry logic

This was never a real fix, just papering over a bug in the queue
consumer. Root cause fixed in #1204, so we can finally delete this.
```
→ `is_ubw=False` — a mensagem é sobre **remover** o workaround, não introduzi-lo ou
mantê-lo (condição 2 falha: não há resignação atual, há resolução)

### 6.3 Categoria C (maior risco — critério mais rigoroso, Seção 3.2)

**`code_comment` — positivo**
```python
# not ideal but it works. Este timeout de 30s foi definido por
# tentativa e erro em 2019 e ninguém sabe explicar por que não é 15s
# ou 60s. Não mexer sem rodar a suíte de carga inteira.
TIMEOUT_SECONDS = 30
```
→ `is_ubw=True`, `confidence=certo`
(contexto: léxico marca como Categoria C — incerteza/resignação)

**`code_comment` — positivo (magic number ⚠, caso de alto risco corretamente positivo)**
```c
/* magic number, mas funciona: 0x4F2A é o offset do header que descobrimos
 * empiricamente lendo o firmware. Não temos a spec oficial do fabricante. */
#define HEADER_OFFSET 0x4F2A
```
→ `is_ubw=True`, `confidence=certo`
(contexto: léxico marca como Categoria C — a admissão de incerteza "descobrimos
empiricamente, não temos a spec" + resignação "mas funciona" satisfazem as condições)

**`code_comment` — negativo (magic number ⚠, caso de alto risco corretamente negativo)**
```python
MAX_RETRIES = 3  # extraído para uma constante para evitar magic numbers
# espalhados pelo código (ver style guide, seção 4.2).
```
→ `is_ubw=False` — este é o **oposto** de UBW: o autor está *evitando* um magic
number, uma boa prática, não admitindo ter aceitado um. Rejeitar sempre que "magic
number" aparecer em contexto de *prevenção*, não de *aceitação resignada*.

**`code_comment` — negativo (don't touch ⚠, diretriz de tooling, não resignação)**
```javascript
// AUTO-GENERATED FILE. Don't touch — changes will be overwritten by
// `npm run codegen`.
```
→ `is_ubw=False` — "don't touch" aqui é uma instrução operacional sobre geração de
código, sem nenhuma admissão de que a solução é ruim ou incerta. Falha a condição 2.

**`code_comment` — positivo (don't touch ⚠, corretamente positivo)**
```python
# don't touch this function. It's held together by three different
# hotfixes from 2021-2022 and nobody currently on the team fully
# understands the interaction between them. Hope everything will work.
def legacy_discount_calculator(cart):
    ...
```
→ `is_ubw=True`, `confidence=certo`
(contexto: léxico marca como Categoria C — combina medo de regressão + incerteza sobre
o sistema, o núcleo dessa categoria)

**`issue_body` — negativo (uso não-técnico / genérico)**
```
Título: Revisar processo de onboarding

O processo atual de onboarding não é ideal, mas funciona — vamos deixar
como está até o próximo trimestre e revisar junto com o RH.
```
→ `is_ubw=False` — "não ideal, mas funciona" se refere a um **processo organizacional**,
não a código/design de software. Falha a condição 3 (sem referência a código real).

---

## 7. Casos limítrofes em `is_ubw`

**Se `is_ubw` está em dúvida**, aplique o teste das 5 condições da Seção 4 uma a uma,
por escrito, no campo de observação (`observacao`) da planilha de anotação:

1. Auto-admissão — é a própria pessoa/equipe decidindo, não terceiros?
2. Trade-off explícito — contrasta qualidade ruim com “mas funciona”?
3. Referência concreta a código real — há um deítico (essa função, este método)?
4. Sem negação — não é uma forma negada (“não é um hack”)?
5. Não é ruído lexical — não está dentro de string de teste, fixture, citação?

Se alguma condição continuar ambígua após esse checklist, marque `confidence = incerto`.
Não pule diretamente para `is_ubw = False` por padrão.

**Expressões de alto risco:** `magic number`, `don't touch`, `hope everything will work`

Essas aparecem tanto em contextos positivos genuínos quanto em contextos descartáveis. Aplique
sempre o teste das 5 condições — não confie só na palavra isolada.

**Itens com arquivo/issue/PR removidos:** anote com base no `body_text` capturado no CSV
(que é a fonte de verdade da coleta). Não é necessário acessar o artefato ao vivo no GitHub.

**Contexto de categorias (referência apenas):** a coluna `category_ubw` mostra qual
categoria do léxico disparou a coleta. Isso ajuda você a entender o tipo de traço que a
expressão original tenta capturar — veja Seção 5 para referência — mas **você não confirma
nem classifica categoria**. Use apenas para contexto.

---

## 8. Erros comuns a evitar

- **Não classifique pela palavra isolada.** "hack" ou "workaround" aparecem
  frequentemente em contextos neutros ou até elogiosos ("clever hack that improves
  performance 10x" sem nenhuma resignação sobre qualidade — isso não é UBW).
- **Não confunda "descrever um problema" com "admitir uma solução ruim".** Uma issue
  que *pede* para alguém consertar um "dirty hack" existente não é, por si, uma
  instância de UBW do autor da issue (ele está reportando, não resignando-se) — a
  menos que o próprio corpo da issue também assuma responsabilidade por ter introduzido
  o hack e explique por que o manteve.
- **Não penalize tom informal ou humor.** Ironia e humor não anulam uma admissão
  genuína ("lol this is held together by tape but don't you dare refactor it" ainda é
  `is_ubw=True`, Categoria B/C conforme o traço dominante).
- **Contexto de ±3 linhas pode não bastar** para `code_comment` (Tabela 3.5). Se o
  `body_text` capturado for insuficiente para aplicar as 5 condições da Seção 4, marque
  `confidence = incerto` em vez de adivinhar.
