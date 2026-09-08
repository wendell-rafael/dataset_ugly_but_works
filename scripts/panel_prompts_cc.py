#!/usr/bin/env python3
"""Prompt do painel de juízes para o escopo restrito a comentários de código.

Substitui as quatro estratégias de `panel_prompts.py` por **uma só**:
few-shot com pool fixo, em inglês, específico de `code_comment`. As outras três
não voltam — o dev200 já mostrou que zero-shot e few-shot recuperado ficam
abaixo (κ 0,47–0,53 contra 0,56 do fixo) e cada estratégia extra multiplica o
custo da rodada sem hipótese nova para testar.

## O que mudou em relação ao v1, e por quê

**v1 (português, multi-artefato, κ máximo 0,537).** Definia a classe negativa
como ruído lexical: "string de teste, nome de variável, citação, negação". Isso
é a condição 5 das cinco do `ANNOTATION_GUIDELINE.md`, e deixava as outras
quatro implícitas.

**v2 (checklist das cinco condições) foi REPROVADO** — κ ≈ 0,00-0,03, o modelo
passou a rejeitar quase tudo. A lição não é "definição mais estrita é pior", é
que **conjunção explícita de cinco condições faz o modelo procurar motivo para
rejeitar**. O prompt abaixo evita isso: não é checklist, são duas perguntas, e a
classe negativa é descrita por *padrão observado* em vez de condição violada.

**Esta versão sai da anotação real, não da literatura.** As 16 observações dos
negativos unânimes dos 269 itens (`validation/sample_code_comment/analise/`)
mostram que os anotadores aplicaram um teste de **referente**, não a definição
do guia. A frase recorrente nos positivos é literalmente "classifica o código
logo abaixo"; nos negativos, "a expressão se refere ao output", "se refere às
atualizações", "não a implementa", "faz parte dos nomes da classe". Os quatro
padrões negativos da Seção NOT-UBW abaixo são a taxonomia desses 16 casos.

**Escopo estreito habilita precisão que o v1 não podia ter.** Cobrindo issue, PR
e commit ao mesmo tempo, o prompt precisava falar de "trecho" em abstrato. Só
com `code_comment` dá para dizer *o código adjacente ao comentário*, que é
exatamente a regra que os humanos usaram.

**A unidade de julgamento é a janela extraída, não o arquivo.** Em 571 dos
26.036 comentários (2,19%) a expressão que disparou a coleta não aparece no
`body_text` — a janela de ±3 linhas é truncada em 2.000 caracteres depois de
concatenada, e linha longa (arquivo minificado) estoura o orçamento antes de
chegar à linha do match. Ver `get_context_window` em
`02_collect_multiartifact.py`.

Decisão de 07/09/2026: **esses casos são negativos**, não itens a recoletar. É o
que os anotadores já registraram ("não há trecho que indique problema no
código") e mantém gabarito e prompt sob a mesma regra. Consequência para o
texto: a precisão medida é do **pipeline** (léxico + janela de ±3 linhas), não
do léxico isolado, e isso precisa ser declarado.

Por isso a classe UNCERTAIN abaixo é estreita e "ausência de evidência" cai em
NOT-UBW. Se o prompt mandasse responder `uncertain` para trecho truncado, o
juiz discordaria do gabarito em 2,2% do corpus por desenho.

**Inglês.** Os corpora de treino dos juízes são majoritariamente ingleses e o
`body_text` classificado é inglês; instrução em português obrigava o modelo a
cruzar idiomas entre instrução e dado. Não é hipótese testada aqui — é
alinhamento com o dado, e fica declarado como mudança de tratamento junto com as
outras, sem atribuição de efeito isolado.

## Exemplos: origem e vazamento

O pool sai dos itens **unânimes** dos 269 (258 disponíveis: 242 positivos, 16
negativos), com as justificativas escritas pelos anotadores traduzidas para o
inglês. A tradução é minha; o rótulo e o raciocínio são dos anotadores, e
`EXEMPLAR_POOL` registra o `item_id` de cada um para auditoria.

**Todo item usado como exemplo sai do conjunto de avaliação** — ver
`scripts/17_build_cc_eval_set.py`. Sem isso a medida seria otimista por
construção. O custo é pago em negativos, que são o recurso escasso: o pool usa
4 de 22, deixando 18 na avaliação.

Positivos são abundantes (242 unânimes), negativos não. Por isso o pool é 4+4 e
o barrido de k vai até 8: passar disso gasta negativo a uma taxa ruim.
"""

from __future__ import annotations

from typing import Optional, Sequence

# k testados no barrido. Sempre balanceado, metade de cada classe.
K_SWEEP = (2, 4, 6, 8)
DEFAULT_K = 6


SYSTEM_PROMPT = """You are a research assistant in empirical software engineering. \
You screen candidate instances of "Ugly But It Works" (UBW) in source code comments: \
comments where a developer admits the adjacent code is a substandard solution — ugly, a \
hack, a workaround, a stopgap — and indicates they kept it because it works.

You do not replace human annotation. Your job is to flag candidates that a keyword search \
collected but that are not actually UBW, so a human reviews a smaller set. When the snippet \
does not give you enough surrounding code to decide, answer "uncertain" rather than \
guessing."""


DECISION_RULE = """A comment is UBW-TRUE when two things hold:

1. REFERENT — the trigger phrase describes the code in this snippet, not something else.
2. ACCEPTANCE — the author presents that code as adopted and kept, not as rejected, \
already replaced, or merely suggested.

Both hold, and it is UBW-TRUE. The author does not need to say "but it works" explicitly; \
labelling the adjacent code as a hack and leaving it in place is enough.

NOT-UBW means the phrase is there but one of the two fails. These are the patterns that \
came up in human annotation:

- Points elsewhere — the phrase describes the output, the input data being processed, the \
general purpose of a class, or another person's code, rather than the code in the snippet.
- Not adopted — the substandard solution is named as an option that was not taken, as a \
past state that this code replaces, or as something the comment argues against.
- Identifier only — the phrase is part of a class, test, file, or variable name.
- No admission — nothing in the snippet states that the present code is substandard. This \
covers the case where the trigger phrase does not appear in the snippet at all: judge only \
what you were given, and a snippet with no admission in it is NOT-UBW.

UNCERTAIN is for a narrow case: the phrase is present and clearly refers to the code shown, \
but the snippet gives no way to tell whether the author kept that code or rejected it. \
Absence of evidence is NOT-UBW, not uncertain."""


_EXEMPLAR_BLOCK = """--- Example {i} ---
Trigger phrase: "{matched_expression}"
Comment:
\"\"\"
{body_text}
\"\"\"
Label: {label}
Why: {rationale}"""


USER_TEMPLATE = """{decision_rule}
{exemplars}
--- Candidate to classify ---
Repository: {repo_full_name}
Trigger phrase: "{matched_expression}"
Comment:
\"\"\"
{body_text}
\"\"\"

Answer with JSON only, no text outside the JSON:
{{"label": "UBW-TRUE" | "NOT-UBW" | "uncertain", "rationale": "<at most 2 sentences>"}}
"""


# Pool de exemplos. `item_id` remete a
# validation/sample_code_comment/analise/gold_code_comment_269.csv; `rationale`
# traduz a observação do anotador indicado em `fonte_obs`.
#
# Os quatro negativos cobrem um padrão cada, de propósito: com 4 exemplos não dá
# para representar a frequência real dos padrões, então cobrir a variedade rende
# mais que repetir o mais comum ("no admission", 6 dos 16).
#
# PREENCHER com scripts/17_build_cc_eval_set.py --escolher-exemplos, que resolve
# os item_id, extrai body_text e trava o pool num manifesto versionado. Deixado
# vazio aqui para o pool não ser escolhido a olho.
EXEMPLAR_POOL: tuple[dict, ...] = ()


def build_prompt(
    candidate: dict,
    exemplars: Optional[Sequence[dict]] = None,
    k: int = DEFAULT_K,
) -> tuple[str, str]:
    """Devolve (system, user) para um candidato de `code_comment`.

    `exemplars` balanceado por classe; `k` corta o pool mantendo o equilíbrio.
    `category_ubw` NÃO entra: é rótulo atribuído automaticamente pelo léxico, e
    a ablação `nocat` no dev200 não mostrou perda ao removê-lo (κ 0,559 contra
    0,543, dentro do ruído). Uma variável a menos para justificar.
    """
    pool = list(exemplars if exemplars is not None else EXEMPLAR_POOL)
    if k and pool:
        pos = [e for e in pool if e["label"] == "UBW-TRUE"][: k // 2]
        neg = [e for e in pool if e["label"] == "NOT-UBW"][: k - k // 2]
        # Intercala para o modelo não ver todos de uma classe em sequência.
        pool = [e for par in zip(pos, neg) for e in par]

    if pool:
        blocos = [
            _EXEMPLAR_BLOCK.format(i=i, **e) for i, e in enumerate(pool, start=1)
        ]
        exemplos = "\n" + "\n\n".join(blocos) + "\n"
    else:
        exemplos = ""

    user = USER_TEMPLATE.format(
        decision_rule=DECISION_RULE,
        exemplars=exemplos,
        repo_full_name=candidate.get("repo_full_name", ""),
        matched_expression=candidate.get("matched_expression", ""),
        body_text=candidate.get("body_text", ""),
    )
    return SYSTEM_PROMPT, user


# Taxas derivadas dos runs reais do dev200 (dois pontos medidos, ajuste exato):
# prosa 5,57 chars/token, corpo de artefato 4,77 chars/token. Ver o cálculo em
# PLANO_EXPERIMENTO_LLM.md, Seção 4.4.
CHARS_POR_TOKEN_PROSA = 5.57
CHARS_POR_TOKEN_CORPO = 4.77


def estimate_tokens(k: int = DEFAULT_K, body_chars: int = 341,
                    exemplar_body_chars: int = 341) -> int:
    """Tokens de entrada estimados por item, para orçamento.

    `body_chars` 341 é a média de `code_comment` no dev200. Estimativa, não
    medida: a taxa de prosa foi calibrada em português e o prompt agora é
    inglês. Tratar como faixa, e remedir na primeira execução real.
    """
    _, user = build_prompt(
        {"repo_full_name": "o/r", "matched_expression": "x", "body_text": ""},
        exemplars=[
            {"matched_expression": "x", "body_text": "",
             "label": "UBW-TRUE" if n % 2 else "NOT-UBW", "rationale": ""}
            for n in range(k)
        ],
        k=k,
    )
    prosa = len(SYSTEM_PROMPT) + len(user)
    corpo = body_chars + k * exemplar_body_chars
    return round(prosa / CHARS_POR_TOKEN_PROSA + corpo / CHARS_POR_TOKEN_CORPO)
