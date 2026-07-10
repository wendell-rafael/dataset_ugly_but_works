# Guideline de Anotação — Dataset UBW (Ugly But It Works)

**Protocolo formal para anotadores humanos — Seção 5.4 do plano de experimento**

---

## 1. Objetivo

Este documento define como decidir, de forma consistente entre anotadores, se um trecho
coletado automaticamente (via léxico, Seção 3.2) é de fato uma instância de **UBW —
resignação funcional**: um(a) desenvolvedor(a) admitindo, no próprio texto, que manteve
uma solução tecnicamente subótima porque ela cumpre a função.

Cada item anotado recebe **três rótulos independentes**:

| Rótulo | Domínio | Descrição |
|---|---|---|
| `is_ubw` | booleano | O item é genuinamente uma instância de UBW? |
| `category_confirmed` | `A`, `B`, `C` ou `"não classificável"` | Categoria semântica confirmada pelo(a) anotador(a), lendo o contexto completo (não apenas a expressão isolada) |
| `confidence` | `certo`, `provável`, `incerto` | Grau de confiança na própria decisão |

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

1. **Leitura deste guideline**, incluindo todos os exemplos da Seção 6.
2. **Calibração:** 50 itens por tipo de artefato (`code_comment`, `commit_message`,
   `issue_body`, `pr_body`) anotados **de forma independente** por todos os anotadores,
   seguidos de uma sessão de discussão conjunta sobre os casos em que houve divergência.
   Awon (2024) obteve κ = 0,926 com esse protocolo; Maldonado & Shihab (2015) reportam
   redução de até 30% nas divergências residuais após uma etapa de calibração.
3. **Anotação plena** da amostra estratificada (Seção 5.2), de forma independente,
   sem consultar os outros anotadores. Divergências são resolvidas **depois**, por
   consenso ou por um terceiro anotador (desempate — ver Seção 7).
4. Cálculo de concordância (κ de Cohen e AC1 de Gwet — Seção 5.5, script
   `03_metrics_llm_triage.py metrics`).

**Regra dura:** nunca altere seu próprio rótulo depois de ver o rótulo de outro
anotador, exceto na sessão de discussão explícita da etapa de calibração. Fazer isso
durante a anotação plena invalida a medição de concordância.

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
3. **Referência concreta a código/design real neste repositório.** Deve haver um
   deítico (este método, esta função, aqui, essa linha, esse PR) ligando a afirmação a
   uma instância real de código — não uma reflexão genérica sobre a profissão.
4. **Sem negação.** "Isto NÃO é um hack sujo" não é UBW — é o oposto.
5. **Não é ruído de correspondência lexical.** A expressão não está dentro de uma
   string literal de teste, fixture, docstring de terceiros, citação, nome de
   variável/função, ou comentário irônico sem relação com o código real.

Se qualquer uma dessas condições falhar → `is_ubw = False`.

---

## 5. Definições operacionais das categorias (A, B, C)

> Referência lexical completa: Seção 3.2 do plano. Aqui, o critério é o **traço
> dominante do argumento do autor**, não apenas qual palavra do léxico disparou a
> coleta — ver regras de desempate na Seção 7 quando os dois divergem.

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
→ `is_ubw=True`, `category_confirmed=A`, `confidence=certo`

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
→ `is_ubw=True`, `category_confirmed=A` (mistura traços de A e B — ver Seção 7 para o
desempate: aqui "dirty hack" é o núcleo da frase-título, e "will revisit" é um detalhe
secundário no corpo → mantém A)

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
→ `is_ubw=True`, `category_confirmed=B`, `confidence=certo`

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
→ `is_ubw=True`, `category_confirmed=B`

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
→ `is_ubw=True`, `category_confirmed=C`, `confidence=certo`

**`code_comment` — positivo (magic number ⚠, caso de alto risco corretamente positivo)**
```c
/* magic number, mas funciona: 0x4F2A é o offset do header que descobrimos
 * empiricamente lendo o firmware. Não temos a spec oficial do fabricante. */
#define HEADER_OFFSET 0x4F2A
```
→ `is_ubw=True`, `category_confirmed=C` — a admissão de incerteza ("descobrimos
empiricamente", "não temos a spec") + resignação ("mas funciona") satisfazem as
condições da Seção 4.

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
→ `is_ubw=True`, `category_confirmed=C` — combina medo de regressão + incerteza sobre
o sistema, o núcleo da Categoria C.

**`issue_body` — negativo (uso não-técnico / genérico)**
```
Título: Revisar processo de onboarding

O processo atual de onboarding não é ideal, mas funciona — vamos deixar
como está até o próximo trimestre e revisar junto com o RH.
```
→ `is_ubw=False` — "não ideal, mas funciona" se refere a um **processo organizacional**,
não a código/design de software. Falha a condição 3 (sem referência a código real).

---

## 7. Regras de desempate para casos limítrofes

Aplique nesta ordem. Pare na primeira regra que resolver o caso.

1. **Categoria default = categoria léxica.** Se o trecho não deixar claro um traço
   dominante diferente do previsto pela expressão que disparou a coleta
   (`matched_expression` → `category_ubw` no schema), mantenha a categoria do léxico.
   O anotador só sobrepõe essa categoria quando o *contexto* evidencia claramente outro
   traço dominante (ex.: uma expressão da Categoria A usada dentro de uma frase cujo
   argumento central é sobre prazo/urgência).
2. **Quando dois traços aparecem com peso comparável**, use a seguinte precedência,
   do mais para o menos verificável objetivamente:
   **B (urgência/temporário) > A (estética explícita) > C (incerteza/resignação vaga).**
   Justificativa: marcadores de urgência (“por enquanto”, “depois eu arrumo”, “TODO”)
   são os mais facilmente identificáveis no texto; julgamentos estéticos exigem menos
   inferência que estados de incerteza vagos, que são os mais subjetivos.
3. **Se `is_ubw` está em dúvida** (não a categoria, mas se é UBW ou não), aplique o
   teste das 5 condições da Seção 4 uma a uma, por escrito, no campo de observação da
   planilha de anotação. Se alguma condição continuar ambígua após esse teste, marque
   `confidence = incerto` e **não** `is_ubw = False` por padrão — deixe para a
   discussão de calibração ou para o terceiro anotador decidir.
4. **Terceiro anotador (desempate formal):** acionado quando os dois anotadores
   primários divergem em `is_ubw` (discordância binária) OU quando ambos marcam
   `is_ubw = True` mas divergem em `category_confirmed`. O terceiro anotador não vê os
   rótulos anteriores antes de decidir, e sua decisão é final para aquele item —
   registre isso separadamente do cálculo de κ/AC1 do par de anotadores primários
   (o desempate não entra na métrica de concordância, apenas resolve o rótulo final do
   item no dataset).
5. **`category_confirmed = "não classificável"`** é reservado para os poucos casos em
   que `is_ubw = True` é claro, mas o trecho genuinamente não expressa nenhum dos três
   traços dominantes descritos na Seção 5 com clareza suficiente mesmo após discussão.
   Use com parcimônia — um volume alto desse rótulo é sinal de que a taxonomia precisa
   de revisão (reporte ao orientador, não altere o léxico unilateralmente).
6. **Itens com o arquivo/issue/PR removidos ou inacessíveis no momento da anotação**
   (ex.: PR de um fork deletado): anote com base no `body_text` capturado no CSV, que é
   a fonte de verdade da coleta — não é necessário (nem sempre possível) acessar o
   artefato ao vivo no GitHub.

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

---

## 9. Referência rápida (cheat sheet)

```
is_ubw = True  se e somente se:
  [ ] autor fala da própria decisão (não de terceiros, não abstrato)
  [ ] há trade-off explícito: "ruim/feio/provisório" + "mas funciona/fica assim"
  [ ] referência concreta a código real deste repositório
  [ ] sem negação
  [ ] não é string literal / fixture / citação / nome de identificador

category_confirmed:
  A -> traço dominante é estética do código
  B -> traço dominante é urgência/temporariedade
  C -> traço dominante é incerteza sobre o sistema / medo de regressão
  desempate de traço comparável -> B > A > C
  categoria default quando ambíguo -> categoria léxica de matched_expression

confidence:
  certo     -> nenhuma condição exigiu inferência além do texto explícito
  provável  -> pelo menos uma condição exigiu inferência razoável do contexto
  incerto   -> aplicar regra de desempate #3 (Seção 7) e/ou terceiro anotador
```
