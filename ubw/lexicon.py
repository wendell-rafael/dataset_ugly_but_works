"""Léxico UBW (Seção 3.2 do plano) e utilitários de categorização.

ATENÇÃO METODOLÓGICA: após o marco do Mês 2 (fim do piloto exploratório,
Seção 3.1), o léxico abaixo é considerado FECHADO. Qualquer alteração deve
ser registrada explicitamente (data, motivo, quem aprovou) em CHANGELOG do
projeto — não silenciosamente neste arquivo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Léxico por categoria semântica (Seção 3.2)
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

# Histórico de promoção/remoção de expressões (Seção 3.1: alterações
# pós-piloto exigem registro explícito, nunca remoção silenciosa) — ver
# LEXICO.md para o racional completo de cada mudança.
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

# Nenhuma expressão ativa é de alto risco atualmente (as duas que eram
# foram removidas — ver REMOVED_EXPRESSIONS). Mantido como conjunto vazio
# para não quebrar código que itera sobre HIGH_RISK_EXPRESSIONS.
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


# Expressões de uma palavra só podem casar dentro de um segmento de nome de
# arquivo/pasta ou stack trace (ex: "stopgap" em "/Tools/stopGap/gClient.py");
# frases com espaço não têm esse problema. Para as expressões abaixo, a
# coleta descarta o registro quando TODAS as ocorrências estão em contexto
# de path — ver match_is_path_only().
PATH_SENSITIVE_EXPRESSIONS: set[str] = {
    expr for exprs in UBW_LEXICON.values() for expr in exprs if " " not in expr
}

_PATH_CONTEXT_MARKERS = ('File "', '.py"', '.js"', "line ", "/src/", "/lib/", "/tools/")
_PATH_CONTEXT_WINDOW_CHARS = 40


def looks_like_path_context(window: str, phrase: str) -> bool:
    """Heurística: a ocorrência de `phrase` dentro de `window` está em um
    caminho de arquivo ou stack trace (ex: "stopgap" em
    "/Tools/stopGap/gClient.py"), não em prosa?
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
    """Confere que a expressão está literalmente presente no texto (módulo
    pontuação/whitespace) — a Search API do GitHub faz stemming e retorna
    falsos positivos ("temporary fix" casa com "temporarily fix"), então um
    registro só é aceito se a frase estiver de fato no corpo do artefato.

    Checa linha por linha (não o texto inteiro normalizado de uma vez): uma
    frase só é aceita se as palavras aparecerem todas na MESMA linha
    original, senão duas palavras de itens de lista/linhas diferentes podem
    se juntar numa frase que nunca existiu no texto (ex: "- pexsi_temp\\n-
    fix md" virando "temp fix" ao colapsar toda pontuação/quebra de linha
    em espaço único).
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


# Tokens de comentário por linguagem, usados para filtrar string literals.
# Heurística de prefixo/delimitador por extensão, não um parser de AST — não
# distingue com 100% de precisão uma string multiline de um docstring, mas é
# suficiente como pré-filtro (casos residuais vão pra validação manual).
CODE_EXTENSIONS: list[str] = [
    ".py", ".java", ".js", ".ts", ".tsx", ".jsx", ".c", ".cpp", ".cc", ".h",
    ".hpp", ".go", ".rb",
]

# Código vendorizado/de terceiros é excluído da coleta de code_comment: uma
# troca de versão de lib vendorizada gera dezenas de eventos de "remoção"
# simultâneos que não são decisão de ninguém do time do repositório,
# contaminando a análise de sobrevivência. Heurística por padrão de path —
# sem SBOM disponível, é best-effort: pastas convencionais de vendoring +
# diretórios de biblioteca com sufixo de versão (ex: "rocksdb-8.1.1/").
VENDORED_PATH_MARKERS: list[str] = [
    "vendor/", "node_modules/", "third_party/", "thirdparty/", "external/",
    "extern/", "deps/", "Godeps/", "/src/golang.org/", "/src/github.com/",
    "site-packages/", "dist-packages/", ".venv/", "bower_components/",
    "dist/", "build/",
]

# Diretório com nome de pacote + versão embutida (ex: "rocksdb-8.1.1/",
# "openssl-3.0.2/"), padrão comum de código de terceiros copiado/vendorizado
# diretamente no repositório em vez de gerenciado por um package manager.
_VENDORED_VERSION_DIR_RE = re.compile(
    r"(^|/)[A-Za-z][A-Za-z0-9_.]*-\d+\.\d+(\.\d+)?([./]|$)"
)

# Bibliotecas JS amplamente vendorizadas sob nomes de pasta que não seguem
# nenhuma convenção reconhecível pelos marcadores acima — checagem por nome
# de arquivo é mais robusta aqui: é praticamente impossível um projeto ter
# organicamente seu próprio código-fonte num arquivo chamado "jquery.js".
VENDORED_FILENAMES: set[str] = {
    "jquery.js", "jquery.min.js", "jquery-ui.js", "jquery-ui.min.js",
    "bootstrap.js", "bootstrap.min.js", "bootstrap.bundle.js",
    "lodash.js", "lodash.min.js", "underscore.js", "underscore.min.js",
    "moment.js", "moment.min.js", "d3.js", "d3.min.js",
    "angular.js", "angular.min.js", "vue.js", "vue.min.js",
    "react.js", "react.min.js", "react-dom.js", "react-dom.min.js",
    "popper.js", "popper.min.js", "modernizr.js", "normalize.css",
    # search_index.js: índice de busca gerado pelo Documenter.jl, uma cópia
    # por versão de doc commitada — achado real na rodada de 3.000 repos
    # (2026-07-14): 65 registros de um único repo eram cópias desse arquivo.
    "search_index.js",
}

# Sufixo de arquivo minificado/compilado — não tem nome fixo (cada projeto
# nomeia o próprio bundle), então checagem é por sufixo, não por nome exato.
_MINIFIED_SUFFIXES = (".min.js", ".min.css")


def is_vendored_path(path: str) -> bool:
    """Heurística: o path pertence a uma árvore de código vendorizado/de
    terceiros ou é saída de build/minificação, e deve ser excluído da
    coleta de code_comment.

    Best-effort — pode ter falsos negativos (vendoring sem convenção de
    nome reconhecível) e, mais raramente, falsos positivos (uma pasta do
    próprio projeto que por acaso segue o padrão nome-versão). Casos
    residuais continuam sujeitos à validação manual (Seção 5).
    """
    normalized = path if path.startswith("/") else f"/{path}"
    if any(marker in normalized for marker in VENDORED_PATH_MARKERS):
        return True
    filename = path.rsplit("/", 1)[-1].lower()
    if filename in VENDORED_FILENAMES:
        return True
    if filename.endswith(_MINIFIED_SUFFIXES):
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
