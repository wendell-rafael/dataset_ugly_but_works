#!/usr/bin/env python3
"""Estratégias de prompt do painel de juízes (PLANO_EXPERIMENTO_LLM.md, Seção 3.2).

Três variantes, todas construídas sobre o MESMO prompt v1 validado em
`03_metrics_llm_triage.py` — a única coisa que muda entre elas é a presença (e a
origem) de exemplos rotulados por humanos:

    zero_shot_nodef    nem definição nem exemplos: só os nomes dos três rótulos,
                       os campos do candidato e o formato de saída. O contraste
                       com `zero_shot` isola quanto a definição ancorada na
                       literatura carrega sozinha.
    zero_shot          o prompt v1 puro, sem exemplos. É a linha de base.
    fewshot_fixed      um conjunto fixo de exemplos, balanceado entre positivos
                       e negativos, sorteado uma única vez do conjunto de
                       desenvolvimento e reutilizado em todos os itens.
    fewshot_retrieved  para cada item a classificar, os k exemplos mais
                       parecidos do conjunto de desenvolvimento, por
                       similaridade de cosseno sobre TF-IDF. Mesmo desenho da
                       etapa de classificação do IMPACT (Li et al., TOSEM 2026).

O prompt v1 é importado do script 03 em vez de copiado: um só texto canônico,
e qualquer ajuste nele vale automaticamente para as três estratégias.

Vazamento: quando o item avaliado pertence ao próprio pool de exemplos (o caso
de rodar o conjunto de desenvolvimento contra ele mesmo), ele é removido da
lista de candidatos a exemplo antes da seleção — leave-one-out. Sem isso a
medida de few-shot no desenvolvimento seria otimista por construção.

As justificativas humanas (`observacao`) entram apenas como CONTEÚDO de exemplo,
nunca como variável de entrada do item classificado: os 90.873 itens não
rotulados do corpus não as possuem (Seção 3.2 do plano).
"""
from __future__ import annotations

import importlib.util
import random
import re
import threading
from pathlib import Path
from typing import Optional, Sequence

_SCRIPTS_DIR = Path(__file__).resolve().parent


def _load_triage_module():
    """Importa `03_metrics_llm_triage.py` (nome de módulo começa com dígito, então
    não dá para usar `import` normal)."""
    path = _SCRIPTS_DIR / "03_metrics_llm_triage.py"
    spec = importlib.util.spec_from_file_location("ubw_triage_v1", path)
    if spec is None or spec.loader is None:  # pragma: no cover — só falha se o arquivo sumir
        raise RuntimeError(f"não consegui carregar {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_triage = _load_triage_module()

build_v1_prompt = _triage.build_llm_triage_prompt
parse_llm_json_label = _triage._parse_llm_json_label
VALID_LLM_LABELS = _triage.VALID_LLM_LABELS

STRATEGIES = ("zero_shot_nodef", "zero_shot", "fewshot_fixed", "fewshot_retrieved")

# --- zero_shot_nodef --------------------------------------------------------
# Variante 1 da Seção 4.3 do plano: o mesmo item, os mesmos campos e o mesmo
# formato de saída do v1, mas sem nenhuma definição de UBW — nem o parágrafo do
# system prompt, nem os critérios que o v1 anexa a cada rótulo. Sobra o nome das
# três classes.
#
# `category_ubw` é mantido de propósito, apesar de ser sinal a favor do positivo
# (é a crítica que motivou o v2). Removê-lo aqui mudaria duas coisas de uma vez
# e tornaria impossível atribuir ao texto da definição qualquer diferença de
# desempenho contra o `zero_shot`. O vazamento é questão separada.

SYSTEM_PROMPT_NODEF = """Você é um assistente de pesquisa em engenharia de \
software empírica. Sua tarefa é classificar trechos de texto extraídos de \
repositórios de software."""

USER_PROMPT_TEMPLATE_NODEF = """Classifique o candidato abaixo em EXATAMENTE uma \
das três categorias: "UBW-verdadeiro", "não-UBW" ou "incerto".

Contexto do candidato:
- Repositório: {repo_full_name}
- Tipo de artefato: {artifact_type}
- Categoria léxica atribuída automaticamente: {category_ubw}
- Expressão que disparou a coleta: "{matched_expression}"
- Trecho (com contexto, quando aplicável):
\"\"\"
{body_text}
\"\"\"

Responda ESTRITAMENTE em JSON, sem texto fora do JSON, no formato:
{{"label": "UBW-verdadeiro" | "não-UBW" | "incerto", "rationale": "<justificativa em até 2 frases>"}}
"""

BODY_CHARS = 2000  # mesmo corte do v1, para que a única diferença seja a definição


def window_around_expression(body: object, expression: object,
                             limit: int = BODY_CHARS) -> str:
    """Recorta `limit` caracteres em torno da expressão-gatilho, e não do início.

    Medido no conjunto de desenvolvimento: em 6 dos 200 itens o corte simples
    `body[:2000]` descartava justamente o trecho onde a expressão aparece, e o
    juiz recebia um texto que não continha a expressão que ele deveria julgar.
    (Outros 13 itens não têm a expressão no `body_text` guardado de forma alguma
    — esse é problema da coleta, e esta função não resolve.)

    O efeito no juiz é grande: a taxa de erro nos itens em que a expressão não
    aparece no prompt foi de 31,6%, contra 7,2% nos demais — 32% de todos os
    erros do melhor juiz vinham desses poucos itens.

    Quando a expressão não é encontrada, cai no comportamento antigo (prefixo),
    para que o texto nunca fique vazio.
    """
    text = "" if body is None or (isinstance(body, float) and body != body) else str(body)
    if len(text) <= limit:
        return text

    needle = str(expression or "").lower().strip()
    position = text.lower().find(needle) if needle else -1
    if position < 0:
        return text[:limit]

    # Centraliza a janela na ocorrência, respeitando as bordas do texto.
    half = (limit - len(needle)) // 2
    start = max(0, position - half)
    end = min(len(text), start + limit)
    start = max(0, end - limit)  # reexpande à esquerda se bateu no fim
    snippet = text[start:end]
    return ("…" + snippet if start > 0 else snippet) + ("…" if end < len(text) else "")


def build_nodef_prompt(candidate: dict) -> tuple[str, str]:
    return SYSTEM_PROMPT_NODEF, USER_PROMPT_TEMPLATE_NODEF.format(
        repo_full_name=candidate.get("repo_full_name", ""),
        artifact_type=candidate.get("artifact_type", ""),
        category_ubw=candidate.get("category_ubw", ""),
        matched_expression=candidate.get("matched_expression", ""),
        body_text=(candidate.get("body_text") or "")[:BODY_CHARS],
    )

# Marcador do template v1 onde o bloco de exemplos é inserido. Fica logo antes
# do candidato, que é a posição recomendada em few-shot: instrução, exemplos,
# item a resolver.
_ANCHOR = "Contexto do candidato:"

EXEMPLAR_BODY_CHARS = 600  # trecho do exemplo, menor que o do item (2000)
DEFAULT_FIXED_K = 6  # 3 positivos + 3 negativos
DEFAULT_RETRIEVED_K = 3
RATIONALE_BONUS = 0.25  # peso extra na similaridade de exemplares com justificativa humana

_LABEL_TEXT = {True: "UBW-verdadeiro", False: "não-UBW"}


def _squeeze(text: object, limit: int) -> str:
    """Normaliza espaços e corta. Trata NaN do pandas como vazio — sem isso um
    campo ausente viraria a string "nan" dentro do prompt."""
    if text is None or (isinstance(text, float) and text != text):
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()[:limit]


def render_exemplar(exemplar: dict, index: int) -> str:
    """Formata um item rotulado por humanos como exemplo de prompt."""
    label = _LABEL_TEXT[bool(exemplar["is_ubw_gold"])]
    parts = [
        f"[EXEMPLO {index} — rótulo humano: {label}]",
        f"tipo de artefato: {exemplar.get('artifact_type', '')} | "
        f'expressão: "{exemplar.get("matched_expression", "")}"',
        '"""',
        _squeeze(exemplar.get("body_text"), EXEMPLAR_BODY_CHARS),
        '"""',
    ]
    rationale = _squeeze(exemplar.get("rationale_human"), 300)
    if rationale:
        parts.append(f"justificativa do anotador: {rationale}")
    return "\n".join(parts)


def _exemplar_block(exemplars: Sequence[dict]) -> str:
    header = (
        "Exemplos já rotulados por anotadores humanos, com o mesmo critério que "
        "você deve aplicar:\n\n"
    )
    rendered = "\n\n".join(render_exemplar(ex, i) for i, ex in enumerate(exemplars, start=1))
    return header + rendered + "\n\n"


_CATEGORY_LINE = re.compile(r"^- Categoria léxica atribuída automaticamente:.*\n", re.MULTILINE)


def strip_category(user_prompt: str) -> str:
    """Remove a linha que informa a categoria léxica já atribuída pelo pipeline.

    Braço de ablação da Seção 4.3.2 do plano. O campo `category_ubw` é produto da
    própria categorização automática que estamos auditando, então informá-lo ao
    juiz funciona como pista de que "o sistema já achou que é UBW" — viés a favor
    do positivo, num conjunto que já tem 86,5% de positivos. Rodar as mesmas
    estratégias com e sem essa linha mede o tamanho do viés em vez de só declará-lo
    como ameaça.
    """
    stripped = _CATEGORY_LINE.sub("", user_prompt, count=1)
    if stripped == user_prompt:  # pragma: no cover — só se o template mudar
        raise RuntimeError("linha de categoria léxica não encontrada no prompt; "
                           "o template mudou e a ablação estaria medindo nada")
    return stripped


def build_prompt(candidate: dict, strategy: str,
                 exemplars: Optional[Sequence[dict]] = None,
                 drop_category: bool = False,
                 center_window: bool = False) -> tuple[str, str]:
    """Retorna (system_prompt, user_prompt) para uma das quatro estratégias.

    `drop_category=True` ativa o braço de ablação: o prompt sai idêntico, menos a
    linha da categoria léxica (ver `strip_category`).

    `center_window=True` recorta o corpo em torno da expressão-gatilho em vez de
    pegar o prefixo (ver `window_around_expression`). Fica como opção, e não como
    padrão, porque muda o texto enviado ao modelo: as execuções já feitas usaram o
    prefixo, e trocar o padrão as tornaria não-comparáveis em silêncio.
    """
    if strategy not in STRATEGIES:
        raise ValueError(f"estratégia desconhecida: {strategy!r} (use uma de {STRATEGIES})")

    if center_window:
        candidate = dict(candidate)
        candidate["body_text"] = window_around_expression(
            candidate.get("body_text"), candidate.get("matched_expression"))

    if strategy == "zero_shot_nodef":
        system_prompt, user_prompt = build_nodef_prompt(candidate)
        return system_prompt, strip_category(user_prompt) if drop_category else user_prompt

    system_prompt, user_prompt = build_v1_prompt(candidate, prompt_version="v1")
    if drop_category:
        user_prompt = strip_category(user_prompt)
    if strategy == "zero_shot":
        return system_prompt, user_prompt

    if not exemplars:
        raise ValueError(f"estratégia {strategy!r} exige exemplos, e nenhum foi passado")
    if _ANCHOR not in user_prompt:  # pragma: no cover — só quebra se o v1 mudar
        raise RuntimeError(
            f"âncora {_ANCHOR!r} não encontrada no prompt v1; o template mudou e o "
            "bloco de exemplos ficaria fora de lugar"
        )
    return system_prompt, user_prompt.replace(_ANCHOR, _exemplar_block(exemplars) + _ANCHOR, 1)


# ---------------------------------------------------------------------------
# Seleção de exemplos
# ---------------------------------------------------------------------------


class ExemplarPool:
    """Pool de itens rotulados por humanos usado pelas duas variantes few-shot.

    Guarda os itens do conjunto de desenvolvimento e sabe responder duas
    perguntas: "quais são os exemplos fixos" e "quais são os k mais parecidos com
    este item aqui". Nos dois casos, o próprio item alvo é excluído quando ele
    pertence ao pool.
    """

    def __init__(self, items: Sequence[dict], seed: int = 42,
                 fixed_k: int = DEFAULT_FIXED_K):
        self.items = [dict(it) for it in items]
        self.by_id = {it["item_id"]: it for it in self.items}
        self.seed = seed
        self.fixed_k = fixed_k
        self._fixed = self._pick_fixed()
        self._vectorizer = None
        self._matrix = None
        self._index_lock = threading.Lock()

    # -- fixos ------------------------------------------------------------
    def _pick_fixed(self) -> list[dict]:
        """Sorteia `fixed_k` exemplos com metade de cada classe. Balanceado de
        propósito: o conjunto tem 86,5% de positivos, e um sorteio simples
        traria quase só positivos, ensinando o modelo a dizer sim."""
        rng = random.Random(self.seed)
        pos = [it for it in self.items if bool(it["is_ubw_gold"])]
        neg = [it for it in self.items if not bool(it["is_ubw_gold"])]
        half = self.fixed_k // 2
        # Prefere exemplos com justificativa humana escrita: eles carregam o
        # critério, não só o rótulo.
        pos.sort(key=lambda it: (not _squeeze(it.get("rationale_human"), 10), rng.random()))
        neg.sort(key=lambda it: (not _squeeze(it.get("rationale_human"), 10), rng.random()))
        chosen = pos[:half] + neg[: self.fixed_k - half]
        rng.shuffle(chosen)  # não deixar todos os negativos no fim do prompt
        return chosen

    def fixed(self, exclude_item_id: Optional[str] = None) -> list[dict]:
        chosen = [it for it in self._fixed if it["item_id"] != exclude_item_id]
        if len(chosen) == len(self._fixed):
            return chosen
        # O item alvo era um dos exemplos fixos: repõe com outro da mesma classe
        # para não mudar o tamanho do prompt entre itens.
        dropped = next(it for it in self._fixed if it["item_id"] == exclude_item_id)
        used = {it["item_id"] for it in self._fixed}
        for candidate in self.items:
            if (candidate["item_id"] not in used
                    and bool(candidate["is_ubw_gold"]) == bool(dropped["is_ubw_gold"])):
                chosen.append(candidate)
                break
        return chosen

    # -- recuperados por similaridade -------------------------------------
    def _ensure_index(self) -> None:
        """Constrói o índice TF-IDF na primeira chamada, uma única vez.

        Sob lock, e publicando vetorizador e matriz juntos no fim. O script 07
        chama isto de várias threads (`--workers`): sem o lock, uma thread podia
        sobrescrever `self._vectorizer` com uma instância ainda não treinada
        enquanto outra já tinha publicado `self._matrix`, e a terceira estourava
        `NotFittedError` no `transform`. A construção leva milissegundos para 200
        itens, então serializar não custa nada.
        """
        if self._matrix is not None:
            return
        with self._index_lock:
            if self._matrix is not None:  # outra thread construiu enquanto esperávamos
                return
            from sklearn.feature_extraction.text import TfidfVectorizer

            # TF-IDF de palavra com bigramas. Escolha deliberada sobre embeddings
            # densos: o sinal aqui é largamente lexical (as próprias expressões do
            # léxico e o vocabulário ao redor delas), o pool tem 200 itens, e roda
            # em CPU em milissegundos sem baixar modelo nenhum.
            vectorizer = TfidfVectorizer(
                lowercase=True, ngram_range=(1, 2), min_df=1, sublinear_tf=True,
                max_features=50_000,
            )
            corpus = [_squeeze(it.get("body_text"), 4000) for it in self.items]
            matrix = vectorizer.fit_transform(corpus)
            self._vectorizer, self._matrix = vectorizer, matrix

    def retrieved(self, candidate: dict, k: int = DEFAULT_RETRIEVED_K) -> list[dict]:
        """Os k exemplos mais parecidos, com cota de classe e bônus por justificativa.

        A recuperação por similaridade pura degenera neste corpus. Medido sobre os
        200 itens de desenvolvimento com k=3: em 33% dos casos os três exemplos
        eram da MESMA expressão do item, em 70% eram todos positivos e em 50%
        nenhum trazia justificativa humana. Um item com "temp fix" recuperava três
        commits "temp fix" positivos e vazios, o que ensina "esta expressão é
        sempre sim" em vez do critério — e ainda reforça o desbalanceamento de
        classe que o resto do desenho tenta neutralizar.

        Duas correções, ambas dentro do desenho de recuperação por similaridade:

        1. Cota de classe: pelo menos um positivo e um negativo entre os k (quando
           k >= 2 e o pool tem as duas classes). As vagas restantes vão para os
           mais parecidos, sem restrição.
        2. Bônus por justificativa: a similaridade de um exemplar que tem
           justificativa humana escrita é multiplicada por (1 + RATIONALE_BONUS).
           É bônus, não filtro: só 24% do pool tem justificativa, e priorizá-las
           estritamente descartaria a similaridade, que é o ponto da estratégia.
        """
        from sklearn.metrics.pairwise import cosine_similarity

        self._ensure_index()
        query = self._vectorizer.transform([_squeeze(candidate.get("body_text"), 4000)])
        sims = cosine_similarity(query, self._matrix)[0]
        target_id = candidate.get("item_id")

        scored = [
            (sims[i] * (1.0 + RATIONALE_BONUS
                        if _squeeze(item.get("rationale_human"), 10) else 1.0), item)
            for i, item in enumerate(self.items)
            if item["item_id"] != target_id  # leave-one-out
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)

        chosen: list[dict] = []
        if k >= 2:
            for want_positive in (True, False):
                best = next((it for _, it in scored
                             if bool(it["is_ubw_gold"]) is want_positive), None)
                if best is not None:
                    chosen.append(best)
        taken = {it["item_id"] for it in chosen}
        for _, item in scored:
            if len(chosen) >= k:
                break
            if item["item_id"] not in taken:
                chosen.append(item)
                taken.add(item["item_id"])

        # Ordena do menos para o mais parecido: o vizinho mais próximo deve ser o
        # último exemplo lido antes do item a julgar.
        by_score = {it["item_id"]: sc for sc, it in scored}
        chosen.sort(key=lambda it: by_score[it["item_id"]])
        return chosen[:k]

    def exemplars_for(self, candidate: dict, strategy: str, k: int) -> list[dict]:
        if strategy == "fewshot_fixed":
            return self.fixed(exclude_item_id=candidate.get("item_id"))
        if strategy == "fewshot_retrieved":
            return self.retrieved(candidate, k=k)
        return []
