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
