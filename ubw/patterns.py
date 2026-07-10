"""Padrões estruturais (regex) para MINERAÇÃO exploratória de candidatos a
novas expressões UBW — camada SEPARADA do léxico fechado (ubw/lexicon.py).

Diferença de propósito frente ao léxico:
    - `ubw/lexicon.py`: as 22 frases literais, ancoradas na literatura,
      usadas na coleta oficial do dataset (Seção 3.2 do plano). Fechado
      após o piloto (Seção 3.1); qualquer mudança precisa de aval do
      orientador e fica registrada, não é feita silenciosamente aqui.
    - Este módulo: padrões estruturais (não frases fixas) usados apenas
      para DESCOBRIR candidatos a novas expressões, via `scripts/
      04_pattern_mining.py`. Gera um relatório de frequência para revisão
      humana; não altera o dataset já coletado nem o léxico oficial.

A GitHub Search API não suporta regex/wildcard, então cada padrão tem duas
formas:
    - `git_ere`: regex POSIX ERE frouxo, usado como primeiro filtro via
      `git grep -E` (que não suporta `\\b` de forma portável entre
      versões/plataformas do git);
    - `python_re`: regex Python preciso (com `\\b`), aplicado como segundo
      filtro sobre o texto já recuperado — tanto sobre as linhas do `git
      grep` quanto sobre o `body_text` vindo da Search API.
    - `api_keywords`: termos usados para alargar a query da Search API
      (busca por co-ocorrência de palavras, sem exigir adjacência exata),
      já que a API não aceita o padrão diretamente.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PatternTemplate:
    name: str
    description: str
    git_ere: str
    python_re: str
    api_keywords: tuple[str, ...]
    kind: str = "structural"  # "structural" (regex) ou "literal_candidate" (frase fixa proposta)
    category_hint: Optional[str] = None  # sugestão A/B/C, a confirmar na checagem manual


def _literal_template(phrase: str, category_hint: str) -> PatternTemplate:
    """Constrói um PatternTemplate para uma frase literal candidata (não um
    padrão estrutural). Usado para propor NOVAS expressões ao léxico
    oficial, testando-as com o mesmo pipeline de mineração — nunca as
    adiciona a `ubw.lexicon` diretamente.
    """
    escaped = re.escape(phrase)
    return PatternTemplate(
        name=f"literal::{phrase}",
        description=f'candidata literal (proposta {category_hint}): "{phrase}"',
        git_ere=escaped,
        python_re=rf"\b{escaped}\b",
        api_keywords=tuple(phrase.split()),
        kind="literal_candidate",
        category_hint=category_hint,
    )


# Termos de julgamento de qualidade que "travam" o padrão but_works (ver
# comentário abaixo). Curada a partir da literatura (Maldonado et al., 2017;
# Ren et al., 2019) + achados do piloto. Mistura adjetivos ("kludgy") e
# substantivos na mesma posição sintática ("a kludge but it works") — o que
# importa é o token, não a classe gramatical.
QUALITY_ADJECTIVES: list[str] = [
    "ugly", "janky", "hacky", "messy", "dirty", "crude", "brittle", "fragile",
    "sloppy", "kludgy", "kludge", "hackish", "gross", "nasty", "clunky", "jury-rigged",
]
_ADJ_ALT_ERE = "|".join(QUALITY_ADJECTIVES)
_ADJ_ALT_PY = "|".join(re.escape(a) for a in QUALITY_ADJECTIVES)

# but_works exige um adjetivo de QUALITY_ADJECTIVES antes de "but" — a
# versão sem essa exigência (só adjacência de "but"/"however" com "works")
# gerou 61 candidatos com 0/12 TP no piloto (ruído de compatibilidade tipo
# "funciona no Chrome mas não no Firefox"); com o adjetivo, caiu pra 2
# candidatos, ambos TP.
PATTERN_TEMPLATES: list[PatternTemplate] = [
    PatternTemplate(
        name="but_works",
        description='"<adjetivo de qualidade> ... but ... works" (ex: "ugly but it works")',
        git_ere=rf"({_ADJ_ALT_ERE}).{{0,25}}but.{{0,40}}works",
        python_re=rf"\b(?:{_ADJ_ALT_PY})\b[^.!?\n]{{0,25}}\bbut\b[^.!?\n]{{0,40}}\bworks?\b",
        api_keywords=("but", "works"),
    ),
    PatternTemplate(
        name="concessive_works",
        description='"although/though/despite ... works" (conector concessivo + works)',
        git_ere=r"(although|though|despite|in spite of).{0,60}works",
        python_re=r"\b(?:although|though|even though|despite|in spite of)\b[^.!?\n]{0,60}\bworks?\b",
        api_keywords=("despite", "works"),
    ),
    PatternTemplate(
        name="but_passes_tests",
        description='"but ... passes the tests/CI" — padrão ausente no léxico atual (Seção 3.2)',
        git_ere=r"but.{0,25}pass(es|ed|ing)?.{0,20}(tests|ci|suite|build)",
        python_re=r"\bbut\b[^.!?\n]{0,25}\b(?:passes?|passed|passing)\b[^.!?\n]{0,20}\b(?:tests?|ci|the\s+suite|the\s+build)\b",
        api_keywords=("but", "passes", "tests"),
    ),
    PatternTemplate(
        name="concessive_passes_tests",
        description='"although/despite ... passes the tests/CI"',
        git_ere=r"(although|though|despite).{0,50}pass(es|ed|ing)?.{0,20}(tests|ci|suite|build)",
        python_re=r"\b(?:although|though|despite)\b[^.!?\n]{0,50}\b(?:passes?|passed|passing)\b[^.!?\n]{0,20}\b(?:tests?|ci|the\s+suite|the\s+build)\b",
        api_keywords=("despite", "passes", "tests"),
    ),
]

# Frases literais candidatas — não fazem parte de `ubw.lexicon.UBW_LEXICON`.
# As já promovidas ao léxico oficial (ver PROMOTED_EXPRESSIONS em
# ubw/lexicon.py) continuam aqui de propósito, pra permitir remineração;
# as demais são lista de observação sem evidência suficiente ainda.
LITERAL_CANDIDATES: list[tuple[str, str]] = [
    ("ugly hack", "A"),
    ("kludge", "A"),
    ("temporary fix", "B"),
    ("temp fix", "B"),
    ("stopgap", "B"),
    ("stopgap fix", "B"),
    ("workaround for now", "B"),
    ("not the best solution but", "C"),
    ("i know this is bad but", "C"),
    ("not proud of this but", "C"),
]

PATTERN_TEMPLATES.extend(_literal_template(phrase, cat) for phrase, cat in LITERAL_CANDIDATES)


CONTEXT_WINDOW_CHARS = 30


def find_matches(text: str, template: PatternTemplate) -> list[str]:
    """Retorna janelas de contexto (não só o trecho casado) ao redor de
    cada ocorrência de `python_re` em `text`.

    Inclui `CONTEXT_WINDOW_CHARS` antes do início do match: os regex de
    `but_works` etc. começam exatamente em "but" ou "works", então o
    adjetivo que precede "but" (ex: "ugly" em "ugly but it works") fica
    FORA do span casado — sem essa janela extra, extract_slots() nunca o
    veria.
    """
    windows = []
    for m in re.finditer(template.python_re, text, flags=re.IGNORECASE):
        start = max(0, m.start() - CONTEXT_WINDOW_CHARS)
        end = min(len(text), m.end() + CONTEXT_WINDOW_CHARS)
        windows.append(text[start:end].strip())
    return windows


# Reexportada de ubw/lexicon.py para manter a interface de
# scripts/04_pattern_mining.py.
from ubw.lexicon import looks_like_path_context  # noqa: E402,F401


def extract_slots(context_window: str) -> dict:
    """Extrai os "slots" de interesse de uma janela de contexto, para a
    mineração de frequência: qual palavra/expressão aparece antes de "but"
    (o adjetivo/crítica, ex: "ugly" em "ugly but it works"), depois de
    "but" (a justificativa) e antes de "works" (reforço do primeiro slot
    quando "but" não está imediatamente antes). Heurística de janela de
    palavras, não um parser sintático — suficiente para gerar candidatos a
    revisão humana, não para classificação automática.
    """
    def _word_window_before(pattern: str) -> Optional[str]:
        m = re.search(rf"([\w'-]+(?:\s+[\w'-]+){{0,2}})\s+{pattern}", context_window, flags=re.IGNORECASE)
        return m.group(1).strip().lower() if m else None

    pre_but = _word_window_before(r"but\b")
    pre_works = _word_window_before(r"works?\b")

    post_but = None
    m_post = re.search(r"\bbut\b\s+(.{1,40})", context_window, flags=re.IGNORECASE)
    if m_post:
        post_but = m_post.group(1).strip().lower()

    return {"pre_but": pre_but, "pre_works": pre_works, "post_but": post_but}
