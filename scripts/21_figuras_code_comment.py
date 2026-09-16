#!/usr/bin/env python3
"""Figuras do escopo `code_comment` para apresentação.

Duas figuras, ambas de magnitude por identidade, logo barra horizontal ordenada:
ocorrências por expressão do léxico e por linguagem principal do repositório.

Decisões de forma, para não terem que ser redecididas:

- Série única, então uma cor só e nenhuma legenda. O título nomeia a série.
- Rótulo direto em cada barra, e nenhum eixo de valor. Num ranking de barras o
  rótulo direto substitui a escala: o leitor lê o número, não o compara com uma
  grade.
- A cauda vira uma barra agregada com a contagem no rótulo. Sem isso, as
  expressões raras viram traços invisíveis ao lado de `this is a hack`, e a
  raridade delas, que é um achado, fica ilegível.
- Grade e eixos recessivos; sem moldura.

Uso:
    python 21_figuras_code_comment.py
    python 21_figuras_code_comment.py --top-expressoes 12 --top-linguagens 10
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ubw.figuras_cc")

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CORPUS = ROOT / "data" / "full_run" / "ubw_collected_consolidated.csv"
DEFAULT_OUT = ROOT / "figures" / "code_comment"

# Paleta validada (slot categórico 1 sobre a superfície clara). Série única, uma
# cor só: a identidade das barras vem do rótulo do eixo, não da cor.
SURFACE = "#fcfcfb"
SERIES = "#2a78d6"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#dedcd6"


def barra_horizontal(rotulos: list[str], valores: list[int], titulo: str,
                     subtitulo: str, destino: Path, sufixo_rotulo: str = "") -> Path:
    altura = 0.42 * len(rotulos) + 1.6
    fig, ax = plt.subplots(figsize=(8.2, altura), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)

    posicoes = range(len(rotulos))
    ax.barh(list(posicoes), valores, color=SERIES, height=0.68, zorder=3)
    ax.set_yticks(list(posicoes))
    ax.set_yticklabels(rotulos, fontsize=10.5, color=TEXT_PRIMARY)
    ax.invert_yaxis()

    limite = max(valores) * 1.16
    ax.set_xlim(0, limite)
    ax.set_xticks([])
    for lado in ("top", "right", "bottom", "left"):
        ax.spines[lado].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.xaxis.grid(False)

    for y, valor in zip(posicoes, valores):
        ax.text(valor + limite * 0.012, y, f"{valor:,}".replace(",", ".") + sufixo_rotulo,
                va="center", ha="left", fontsize=10, color=TEXT_SECONDARY)

    ax.set_title(titulo, fontsize=13.5, color=TEXT_PRIMARY, loc="left", pad=18, weight="bold")
    ax.text(0, 1.015, subtitulo, transform=ax.transAxes, fontsize=9.5,
            color=TEXT_SECONDARY, ha="left", va="bottom")

    fig.tight_layout()
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destino, dpi=220, facecolor=SURFACE)
    plt.close(fig)
    logger.info("figura em %s", destino)
    return destino


def _com_cauda(contagem: pd.Series, top: int, rotulo_cauda: str) -> tuple[list[str], list[int]]:
    """Top N mais uma barra agregando o resto, com o número de itens no rótulo."""
    cabeca = contagem.head(top)
    cauda = contagem.iloc[top:]
    rotulos = list(cabeca.index)
    valores = [int(v) for v in cabeca.to_numpy()]
    if len(cauda):
        rotulos.append(rotulo_cauda.format(n=len(cauda)))
        valores.append(int(cauda.sum()))
    return rotulos, valores


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--top-expressoes", type=int, default=12)
    parser.add_argument("--top-linguagens", type=int, default=10)
    args = parser.parse_args()

    df = pd.read_csv(args.corpus, low_memory=False)
    cc = df[df["artifact_type"] == "code_comment"]
    total, repos = len(cc), cc["repo_full_name"].nunique()
    out_dir = Path(args.out_dir)

    expressoes = cc["matched_expression"].value_counts()
    rotulos, valores = _com_cauda(expressoes, args.top_expressoes,
                                  "outras {n} expressões")
    barra_horizontal(
        rotulos, valores,
        "Ocorrências por expressão do léxico",
        f"{total:,} comentários em {repos:,} repositórios · "
        f"{expressoes.size} das 25 expressões ocorrem".replace(",", "."),
        out_dir / "expressoes.png",
    )

    linguagens = cc["primary_language"].value_counts()
    rotulos, valores = _com_cauda(linguagens, args.top_linguagens,
                                  "outras {n} linguagens")
    barra_horizontal(
        rotulos, valores,
        "Ocorrências por linguagem principal do repositório",
        f"{total:,} comentários em {repos:,} repositórios · "
        f"{linguagens.size} linguagens".replace(",", "."),
        out_dir / "linguagens.png",
    )


if __name__ == "__main__":
    main()
