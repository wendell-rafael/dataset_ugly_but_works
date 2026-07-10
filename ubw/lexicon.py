"""Léxico UBW (Seção 3.2 do plano) e utilitários de categorização.

ATENÇÃO METODOLÓGICA: após o marco do Mês 2 (fim do piloto exploratório,
Seção 3.1), o léxico abaixo é considerado FECHADO. Qualquer alteração deve
ser registrada explicitamente (data, motivo, quem aprovou) em CHANGELOG do
projeto — não silenciosamente neste arquivo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Léxico por categoria semântica (Seção 3.2)
# ---------------------------------------------------------------------------

UBW_LEXICON: dict[str, list[str]] = {
    "A": [  # Julgamento estético e hacks explícitos — menor risco de FP
        "ugly but it works",
        "ugly but works",
        "dirty hack",
        "ugly hack",
        "this is a hack",
        "hacky but works",
        "horrible but works",
        "terrible but works",
        "messy but works",
    ],
    "B": [  # Workarounds e urgência — risco intermediário
        "ugly workaround",
        "dirty workaround",
        "quick and dirty",
        "crude but it works",
        "not pretty but it works",
        "band-aid fix",
        "duct tape fix",
        "temporary fix",
        "temp fix",
        "stopgap",
        "workaround for now",
    ],
    "C": [  # Resignação funcional e incerteza — maior risco de FP
        "not ideal but it works",
        "not elegant but works",
        "ugly solution but",
        "ugly code but",
        "hope everything will work",
    ],
}

# ---------------------------------------------------------------------------
# CHANGELOG do léxico (Seção 3.1: alterações pós-piloto exigem registro
# explícito de data, motivo e aval — nunca remoção silenciosa).
#
# 2026-07-01 — Removidas "magic number" e "don't touch" da Categoria C.
#   Motivo: ambas eram marcadas ⚠ (alto risco de falso positivo) desde a
#   versão original do léxico. No piloto de 140 repositórios, "magic
#   number" gerou 54 candidatos (acima do mínimo de 20 exigido pela Seção
#   3.1 para decidir sobre expressões de risco) e "don't touch" gerou 12.
#   Checagem manual: 0/10 e 0/12 respectivamente eram verdadeiros
#   positivos — "magic number" aparecia como jargão técnico legítimo
#   (bytes mágicos de arquivo, IDs de protocolo, o algoritmo fast inverse
#   square root) ou em commits que removiam um magic number (sentido
#   oposto a UBW); "don't touch" aparecia como comentário funcional ou
#   diretiva de tooling ("auto-gerado, não tocar"), nunca como admissão de
#   medo/incerteza. Juntas, respondiam por 66% dos 100 registros coletados
#   na rodada 2 — removê-las reduz o dataset para ~34 registros, mas com
#   precisão amostral muito mais alta. Decisão do orientador (Prof. João
#   Arthur Brunet Monteiro), relatada em 2026-07-01, com base no relatório
#   RESULTADOS_PILOTO.md (Seção 7).
#
# 2026-07-03 — Promovidas 5 expressões descobertas pela mineração de padrões
#   estruturais (scripts/04_pattern_mining.py, ubw/patterns.py), rodada de
#   50 repositórios (seed=7) com checagem manual de TODOS os candidatos:
#     - "ugly hack"          (A): 8 candidatos, ~7-8 verdadeiros positivos;
#     - "temporary fix"      (B): 23 candidatos, todos aparentam ser
#       admissões genuínas de workaround/urgência — único candidato que já
#       ultrapassou sozinho o mínimo de 20 exigido pela Seção 3.1;
#     - "temp fix"           (B): 6 candidatos, 6 verdadeiros positivos;
#     - "stopgap"            (B): 4 candidatos, 4 verdadeiros positivos
#       APÓS o filtro de contexto de path (v1 tinha 3/5 falso positivo por
#       o token aparecer em nomes de arquivo/pasta) — por ser palavra única,
#       está em PATH_SENSITIVE_EXPRESSIONS e a coleta aplica
#       match_is_path_only() antes de aceitar o registro;
#     - "workaround for now" (B): 1 candidato, verdadeiro positivo; amostra
#       pequena, mas a frase é uma admissão explícita por construção
#       (risco de FP baixíssimo), promovida com essa ressalva registrada.
#   Zero hits na mineração (NÃO promovidas, ficam na lista de observação de
#   ubw/patterns.py): "kludge", "stopgap fix" (subsumida por "stopgap"),
#   "not the best solution but", "i know this is bad but", "not proud of
#   this but". "janky" (descoberta orgânica via padrão but_works, n=2)
#   também fica em observação por amostra insuficiente. Decisão de
#   consolidação final do pipeline, 2026-07-03, com base no relatório da
#   mineração (data/pattern_mining_candidates.csv) — a validar com o
#   orientador junto do restante da consolidação.
# ---------------------------------------------------------------------------
PROMOTED_EXPRESSIONS: dict[str, str] = {
    "ugly hack": "mineração 2026-07-03: 8 candidatos, ~7-8 TP (Categoria A)",
    "temporary fix": "mineração 2026-07-03: 23 candidatos, todos TP aparentes (Categoria B)",
    "temp fix": "mineração 2026-07-03: 6 candidatos, 6 TP (Categoria B)",
    "stopgap": "mineração 2026-07-03: 4/4 TP após filtro de path; palavra única, requer PATH_SENSITIVE (Categoria B)",
    "workaround for now": "mineração 2026-07-03: 1/1 TP; amostra pequena, FP improvável por construção (Categoria B)",
}

REMOVED_EXPRESSIONS: dict[str, str] = {
    "magic number": "0/10 verdadeiro positivo em amostra manual (54 candidatos); jargão técnico legítimo ou commits de remoção",
    "don't touch": "0/12 verdadeiro positivo em amostra manual; comentário funcional ou diretiva de tooling, nunca resignação",
}

# Expressões marcadas com ⚠ no plano (Seção 3.2): alto risco de falso
# positivo. Nenhuma expressão ativa está marcada atualmente — as duas que
# eram ⚠ ("magic number", "don't touch") foram removidas em 2026-07-01
# (ver CHANGELOG acima). Mantido como conjunto vazio, não removido, para
# não quebrar código que itera sobre HIGH_RISK_EXPRESSIONS.
HIGH_RISK_EXPRESSIONS: set[str] = set()


def all_expressions() -> list[str]:
    """Retorna todas as expressões do léxico, em uma lista plana."""
    return [expr for exprs in UBW_LEXICON.values() for expr in exprs]


def expression_to_category(expression: str) -> str | None:
    """Mapeia uma expressão para sua categoria (A, B ou C).

    A comparação é case-insensitive e ignora espaços nas bordas, pois é
    assim que as buscas (GitHub Search API, git grep) são realizadas.
    """
    normalized = expression.strip().lower()
    for category, expressions in UBW_LEXICON.items():
        for expr in expressions:
            if expr.lower() == normalized:
                return category
    return None


def is_high_risk(expression: str) -> bool:
    return expression.strip().lower() in {e.lower() for e in HIGH_RISK_EXPRESSIONS}


# ---------------------------------------------------------------------------
# Expressões sensíveis a contexto de path.
#
# Expressões de UMA palavra podem casar dentro de um segmento de nome de
# arquivo/pasta ou stack trace (achado da mineração de 2026-07-02:
# "stopgap" batia em "/Tools/stopGap/gClient.py" — 3 de 5 candidatos eram
# esse falso positivo). Frases com espaço não têm esse problema (espaços
# não ocorrem dentro de um segmento de path convencional). Para as
# expressões abaixo, a coleta deve descartar o registro quando TODAS as
# ocorrências no texto estiverem em contexto de path (match_is_path_only).
# ---------------------------------------------------------------------------

PATH_SENSITIVE_EXPRESSIONS: set[str] = {
    expr for exprs in UBW_LEXICON.values() for expr in exprs if " " not in expr
}

_PATH_CONTEXT_MARKERS = ('File "', '.py"', '.js"', "line ", "/src/", "/lib/", "/tools/")
_PATH_CONTEXT_WINDOW_CHARS = 40


def looks_like_path_context(window: str, phrase: str) -> bool:
    """Heurística: a ocorrência de `phrase` dentro de `window` está em um
    caminho de arquivo ou stack trace (ex: "stopgap" em
    "/Tools/stopGap/gClient.py"), não em prosa?

    Originalmente em ubw/patterns.py (mineração exploratória); movida para
    cá em 2026-07-03, quando "stopgap" foi promovida ao léxico oficial e o
    filtro passou a ser necessário também na coleta oficial.
    """
    idx = window.lower().find(phrase.lower())
    if idx == -1:
        return False
    before = window[max(0, idx - 1):idx]
    after = window[idx + len(phrase):idx + len(phrase) + 1]
    if before in ("/", "\\") or after in ("/", "\\"):
        return True
    return any(marker.lower() in window.lower() for marker in _PATH_CONTEXT_MARKERS)


# Token termina em extensão de arquivo, opcionalmente seguida de ":linha"
# ou ":linha:coluna" (formato de stack trace/log) e pontuação de fechamento.
_FILE_EXTENSION_RE = re.compile(r"\.\w{1,4}(:\d+){0,2}[):,;.\"']*$")


def _token_around(text: str, idx: int, length: int) -> str:
    """Token delimitado por whitespace que contém text[idx:idx+length]."""
    start = idx
    while start > 0 and not text[start - 1].isspace():
        start -= 1
    end = idx + length
    while end < len(text) and not text[end].isspace():
        end += 1
    return text[start:end]


def match_is_path_only(text: str, expression: str) -> bool:
    """True se a expressão ocorre em `text` e TODAS as ocorrências estão em
    contexto de path (segmento de nome de arquivo/pasta, ex: "stopgap" em
    "/Tools/stopGap/gClient.py" ou "stopgap.py") — ou seja, o registro é um
    falso positivo e deve ser descartado.

    O julgamento é por ocorrência, olhando o token (delimitado por
    whitespace) que a contém: se o token tem separador de path ou termina
    em extensão de arquivo, é path; senão é prosa e o registro é mantido.
    Deliberadamente NÃO usa a heurística de marcadores de janela de
    looks_like_path_context (usada na mineração sobre linhas curtas de
    comentário): em corpos longos de issue com stack traces, marcadores
    como 'line ' apareceriam perto de menções genuínas em prosa e
    derrubariam registros válidos.

    Se a expressão não for encontrada literalmente (ex: match "frouxo" da
    Search API com tokenização diferente), retorna False: na dúvida, o
    registro é mantido e vai para validação manual (Seção 5), nunca
    descartado às cegas.
    """
    lowered = text.lower()
    needle = expression.lower()
    found_any = False
    start = 0
    while True:
        idx = lowered.find(needle, start)
        if idx == -1:
            break
        found_any = True
        token = _token_around(text, idx, len(needle))
        is_path = "/" in token or "\\" in token or bool(_FILE_EXTENSION_RE.search(token))
        if not is_path:
            return False  # pelo menos uma ocorrência em prosa: mantém
        start = idx + len(needle)
    return found_any


def _normalize_line_for_phrase_match(line: str) -> str:
    """Colapsa pontuação de uma única linha em espaço único. Tolera
    markdown/pontuação entre as palavras da frase, mas NÃO tolera stemming
    ("temporarily fix" não vira "temporary fix").
    """
    return " " + re.sub(r"[^a-z0-9]+", " ", line.lower()).strip() + " "


def expression_in_text(expression: str, text: str) -> bool:
    """Verificação local de que a expressão do léxico está literalmente
    presente no texto (módulo pontuação/whitespace), sem casar através de
    uma quebra de linha.

    Motivação (rodada final, 2026-07-03): a busca por frase entre aspas da
    GitHub Search API aplica stemming/lematização -- "temporary fix" casou
    com "temporarily fix", "quick and dirty" com "quick/dirty" -- e, em PRs
    de dependabot com changelog truncado, a frase indexada nem sequer esta
    no body retornado. Como o lexico e fechado e literal (Secao 3.2), um
    registro so e aceito se a frase estiver de fato no corpo do artefato.
    Matches frouxos descartados aqui ficam registrados no log e sao fonte
    de candidatos para rodadas futuras de mineracao (ubw/patterns.py).

    BUG corrigido em 2026-07-06: a implementacao original normalizava o
    texto INTEIRO de uma vez, colapsando quebra de linha junto com
    qualquer outra pontuacao em um espaco -- isso apagava a fronteira
    entre itens de lista/linhas diferentes, deixando duas palavras de
    bullets DISTINTOS de um commit squash se juntarem numa frase
    multi-palavra que nunca existiu no texto original. Achado real na
    rodada de 784 repos: "- set default pexsi_temp\n- fix md..." virava
    "...pexsi temp fix..." depois de normalizar (o "_" e o "\n" sumiam
    juntos), casando falsamente com "temp fix" em dezenas de registros.
    Corrigido checando a frase linha por linha -- cada linha e normalizada
    de forma independente, entao a frase so e aceita se as palavras
    aparecerem todas na MESMA linha original. Uma primeira tentativa de
    correcao usando um marcador de fronteira (em vez de checar por linha)
    tinha uma regressao sutil: um marcador vazio "colava" a ultima palavra
    de uma linha com a primeira palavra da linha seguinte, quebrando ate
    expressoes de uma palavra so que ficassem logo no inicio de uma linha.
    """
    normalized_expression = _normalize_line_for_phrase_match(expression)
    return any(
        normalized_expression in _normalize_line_for_phrase_match(line)
        for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    )


@dataclass(frozen=True)
class LexiconEntry:
    expression: str
    category: str
    high_risk: bool


def iter_lexicon() -> list[LexiconEntry]:
    """Itera o léxico como uma lista de entradas (expressão, categoria, risco)."""
    entries = []
    for category, expressions in UBW_LEXICON.items():
        for expr in expressions:
            entries.append(LexiconEntry(expr, category, is_high_risk(expr)))
    return entries


# ---------------------------------------------------------------------------
# Tokens de comentário por linguagem (usados para filtrar string literals /
# dados embutidos / fixtures de teste — Seção 3.3, "Comentários de código").
#
# Heurística baseada em prefixo/par de delimitadores por extensão de
# arquivo. Não é um parser de AST: não distingue, por exemplo, uma string
# multiline Python de um docstring com 100% de precisão. É a mesma limitação
# reconhecida no plano ("operacionalização conservadora") e deve ser tratada
# como um pré-filtro, refinado depois na validação manual (Seção 5).
# ---------------------------------------------------------------------------

# Extensões cobertas pela coleta de comentários de código (Seção 3.3).
CODE_EXTENSIONS: list[str] = [
    ".py", ".java", ".js", ".ts", ".tsx", ".jsx", ".c", ".cpp", ".cc", ".h",
    ".hpp", ".go", ".rb",
]

# ---------------------------------------------------------------------------
# Exclusão de código vendorizado/de terceiros.
#
# Achado do piloto de 20 repositórios (2026-06-30): 73% dos matches de
# code_comment em 0chain/0chain vinham de rocksdb-8.1.1/ vendorizado dentro
# do próprio repositório. A troca de versão da lib gerou dezenas de eventos
# de "remoção" simultâneos que não são decisão de ninguém do time do
# repositório — contaminam diretamente a análise de sobrevivência (Seção 4)
# e a contagem de prevalência (RQ1). Comentários dentro desses paths não
# representam SATD do(a) desenvolvedor(a) do repositório, então são
# excluídos na fonte, antes mesmo de virar candidato.
#
# Heurística por padrão de path — não há um SBOM disponível, então isto é
# best-effort: nomes de pasta convencionais de vendoring + diretórios de
# biblioteca com sufixo de versão (ex: "rocksdb-8.1.1/").
# ---------------------------------------------------------------------------

VENDORED_PATH_MARKERS: list[str] = [
    "vendor/", "node_modules/", "third_party/", "thirdparty/", "external/",
    "extern/", "deps/", "Godeps/", "/src/golang.org/", "/src/github.com/",
    "site-packages/", "dist-packages/", ".venv/", "bower_components/",
]

# Diretório com nome de pacote + versão embutida (ex: "rocksdb-8.1.1/",
# "openssl-3.0.2/"), padrão comum de código de terceiros copiado/vendorizado
# diretamente no repositório em vez de gerenciado por um package manager.
_VENDORED_VERSION_DIR_RE = re.compile(
    r"(^|/)[A-Za-z][A-Za-z0-9_.]*-\d+\.\d+(\.\d+)?([./]|$)"
)

# Nomes de arquivo de bibliotecas JS amplamente vendorizadas (copiadas
# direto no repositório, sem gerenciador de pacote) — achado da mineração
# de padrões de 2026-07-08: o comentário real "kludgy but it works" do
# próprio código-fonte do jQuery apareceu em 15 repositórios totalmente
# não relacionados, porque cada um vendoriza jquery.js sob um nome de
# pasta diferente (wwwroot/lib/jquery/, wwwroot/libs/jquery/, scripts/
# _elements/MDB-Free_4.13.0/js/, public/js/...) — nenhum bate nos
# marcadores de pasta acima. Checagem por nome de arquivo é mais robusta
# pra esse caso específico: é praticamente impossível um projeto ter,
# organicamente, seu próprio código-fonte original num arquivo chamado
# literalmente "jquery.js".
VENDORED_FILENAMES: set[str] = {
    "jquery.js", "jquery.min.js", "jquery-ui.js", "jquery-ui.min.js",
    "bootstrap.js", "bootstrap.min.js", "bootstrap.bundle.js",
    "lodash.js", "lodash.min.js", "underscore.js", "underscore.min.js",
    "moment.js", "moment.min.js", "d3.js", "d3.min.js",
    "angular.js", "angular.min.js", "vue.js", "vue.min.js",
    "react.js", "react.min.js", "react-dom.js", "react-dom.min.js",
    "popper.js", "popper.min.js", "modernizr.js", "normalize.css",
}


def is_vendored_path(path: str) -> bool:
    """Heurística: o path pertence a uma árvore de código vendorizado/de
    terceiros, e deve ser excluído da coleta de code_comment.

    Best-effort — pode ter falsos negativos (vendoring sem convenção de
    nome reconhecível) e, mais raramente, falsos positivos (uma pasta do
    próprio projeto que por acaso segue o padrão nome-versão). Casos
    residuais continuam sujeitos à validação manual (Seção 5).
    """
    normalized = path if path.startswith("/") else f"/{path}"
    if any(marker in normalized for marker in VENDORED_PATH_MARKERS):
        return True
    if path.rsplit("/", 1)[-1].lower() in VENDORED_FILENAMES:
        return True
    return bool(_VENDORED_VERSION_DIR_RE.search(path))

# Marcadores de comentário de linha por extensão.
LINE_COMMENT_TOKENS: dict[str, list[str]] = {
    ".py": ["#"],
    ".rb": ["#"],
    ".java": ["//"],
    ".js": ["//"],
    ".ts": ["//"],
    ".tsx": ["//"],
    ".jsx": ["//"],
    ".c": ["//"],
    ".cpp": ["//"],
    ".cc": ["//"],
    ".h": ["//"],
    ".hpp": ["//"],
    ".go": ["//"],
}

# Marcadores de comentário de bloco (abre, fecha) por extensão.
BLOCK_COMMENT_TOKENS: dict[str, list[tuple[str, str]]] = {
    ".py": [('"""', '"""'), ("'''", "'''")],
    ".java": [("/*", "*/")],
    ".js": [("/*", "*/")],
    ".ts": [("/*", "*/")],
    ".tsx": [("/*", "*/")],
    ".jsx": [("/*", "*/")],
    ".c": [("/*", "*/")],
    ".cpp": [("/*", "*/")],
    ".cc": [("/*", "*/")],
    ".h": [("/*", "*/")],
    ".hpp": [("/*", "*/")],
    ".go": [("/*", "*/")],
}


def looks_like_comment(line: str, extension: str) -> bool:
    """Heurística: a linha contém um marcador de comentário antes de
    qualquer aspas de string na mesma linha?

    Usada como pré-filtro para excluir matches em string literals. É
    deliberadamente conservadora (prefere falso negativo a falso positivo
    grosseiro), pois candidatos que sobrarem passam por validação manual.
    """
    stripped = line.lstrip()
    line_tokens = LINE_COMMENT_TOKENS.get(extension, [])
    for tok in line_tokens:
        idx = stripped.find(tok)
        if idx == -1:
            continue
        # Verifica se o token de comentário não está, ele mesmo, dentro de
        # uma string que precede a marca (heurística simples de contagem de
        # aspas não-escapadas antes do token).
        prefix = stripped[:idx]
        if prefix.count('"') % 2 == 0 and prefix.count("'") % 2 == 0:
            return True
    block_tokens = BLOCK_COMMENT_TOKENS.get(extension, [])
    for open_tok, _close_tok in block_tokens:
        if open_tok in stripped:
            return True
    return False
