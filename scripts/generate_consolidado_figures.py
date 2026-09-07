#!/usr/bin/env python3
"""Gera os gráficos do corpus consolidado (fatia A + fatia B, pós-limpeza de
bot) para apresentação dos achados iniciais ao orientador.

Roda sobre `data/full_run/ubw_collected_consolidated.csv` (116.192
registros, 25 expressões do léxico, categorias A/B/C). Segue a mesma
identidade visual de `generate_report_figures.py` (cores, fonte, estilo de
eixo) para manter consistência com as figuras de rodadas anteriores.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = ROOT / "figures" / "consolidado"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#888780",
    "axes.labelcolor": "#2C2C2A",
    "text.color": "#2C2C2A",
    "xtick.color": "#2C2C2A",
    "ytick.color": "#2C2C2A",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

COLOR_A = "#378ADD"
COLOR_B = "#1D9E75"
COLOR_C = "#EF9F27"
COLOR_NEUTRAL = "#7F77DD"

CAT_COLOR = {"A": COLOR_A, "B": COLOR_B, "C": COLOR_C}
CAT_LABEL = {"A": "A — estética", "B": "B — workaround", "C": "C — incerteza"}
ARTIFACT_ORDER = ["code_comment", "commit_message", "issue_body", "pr_body"]
ARTIFACT_LABEL = {
    "code_comment": "Comentário\nde código",
    "commit_message": "Mensagem\nde commit",
    "issue_body": "Corpo de\nissue",
    "pr_body": "Corpo de\nPR",
}

df = pd.read_csv(ROOT / "data" / "full_run" / "ubw_collected_consolidated.csv", low_memory=False)
N_TOTAL = len(df)
N_REPOS = df["repo_full_name"].nunique()


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(FIG_DIR / name, dpi=160, bbox_inches="tight")
    plt.close(fig)


# --- 1. Distribuição por categoria semântica (A/B/C) -------------------------
fig, ax = plt.subplots(figsize=(5.5, 3.4))
cats = ["A", "B", "C"]
vals = [int((df["category_ubw"] == c).sum()) for c in cats]
bars = ax.bar([CAT_LABEL[c] for c in cats], vals, color=[CAT_COLOR[c] for c in cats], width=0.55)
for b, v in zip(bars, vals):
    pct = 100 * v / N_TOTAL
    ax.text(b.get_x() + b.get_width() / 2, v + N_TOTAL * 0.015, f"{v:,}\n({pct:.1f}%)".replace(",", "."),
            ha="center", va="bottom", fontweight="medium", fontsize=9.5)
ax.set_ylabel("Registros")
ax.set_ylim(0, max(vals) * 1.22)
ax.set_title(f"Distribuição por categoria semântica (N={N_TOTAL:,})".replace(",", "."), fontsize=11)
save(fig, "01_categoria.png")

# --- 2. Distribuição por tipo de artefato ------------------------------------
fig, ax = plt.subplots(figsize=(5.8, 3.4))
vals = [int((df["artifact_type"] == a).sum()) for a in ARTIFACT_ORDER]
labels_pt = [ARTIFACT_LABEL[a].replace("\n", " ") for a in ARTIFACT_ORDER]
bars = ax.barh(labels_pt[::-1], vals[::-1], color=COLOR_NEUTRAL, height=0.55)
for b, v in zip(bars, vals[::-1]):
    pct = 100 * v / N_TOTAL
    ax.text(v + N_TOTAL * 0.008, b.get_y() + b.get_height() / 2, f"{v:,} ({pct:.1f}%)".replace(",", "."),
            va="center", fontweight="medium", fontsize=9.5)
ax.set_xlabel("Registros")
ax.set_xlim(0, max(vals) * 1.28)
ax.set_title(f"Distribuição por tipo de artefato (N={N_TOTAL:,})".replace(",", "."), fontsize=11)
save(fig, "02_artefato.png")

# --- 3. Categoria x Tipo de artefato (grupos por artefato) -------------------
fig, ax = plt.subplots(figsize=(8, 4.6))
x = np.arange(len(ARTIFACT_ORDER))
width = 0.25
max_val = int(df.groupby(["artifact_type", "category_ubw"]).size().max())
for i, cat in enumerate(["A", "B", "C"]):
    vals = [int(((df["artifact_type"] == a) & (df["category_ubw"] == cat)).sum()) for a in ARTIFACT_ORDER]
    offset = (i - 1) * width
    bars = ax.bar(x + offset, vals, width=width, color=CAT_COLOR[cat], label=CAT_LABEL[cat])
    for b, v in zip(bars, vals):
        if v > 0:
            ax.text(b.get_x() + b.get_width() / 2, v + max_val * 0.02, f"{v:,}".replace(",", "."),
                     ha="center", va="bottom", fontsize=8)
ax.set_xticks(x)
ax.set_xticklabels([ARTIFACT_LABEL[a] for a in ARTIFACT_ORDER])
ax.set_ylabel("Registros")
ax.set_ylim(0, max_val * 1.18)
ax.legend(loc="upper right", fontsize=9, frameon=False)
ax.set_title("Categoria semântica por tipo de artefato", fontsize=11, pad=14)
save(fig, "03_categoria_x_artefato.png")

# --- 4. Ranking completo das 25 expressões do léxico -------------------------
fig, ax = plt.subplots(figsize=(7.5, 8.5))
expr_counts = df["matched_expression"].value_counts()
expr_cat = df.groupby("matched_expression")["category_ubw"].first()
order = expr_counts.index[::-1]  # menor -> maior, de baixo pra cima no barh
vals = expr_counts.loc[order].values
colors = [CAT_COLOR[expr_cat[e]] for e in order]
bars = ax.barh(order, vals, color=colors, height=0.65)
for b, v in zip(bars, vals):
    ax.text(v + max(vals) * 0.012, b.get_y() + b.get_height() / 2, f"{v:,}".replace(",", "."),
            va="center", fontweight="medium", fontsize=8.5)
ax.set_xlabel("Registros")
ax.set_xlim(0, max(vals) * 1.12)
ax.set_title(f"Todas as 25 expressões do léxico (N={N_TOTAL:,})".replace(",", "."), fontsize=11)
handles = [plt.Rectangle((0, 0), 1, 1, color=CAT_COLOR[c]) for c in ["A", "B", "C"]]
ax.legend(handles, [CAT_LABEL[c] for c in ["A", "B", "C"]], loc="lower right", fontsize=9, frameon=False)
save(fig, "04_todas_expressoes.png")

# --- 5. Categoria x Linguagem (top 12, ordenado por % de Categoria A) -------
TOP_N_LANG = 12
top_langs = df["primary_language"].value_counts().head(TOP_N_LANG).index.tolist()
ct = pd.crosstab(df[df["primary_language"].isin(top_langs)]["primary_language"], df["category_ubw"])
ct = ct.loc[top_langs]
ct["total"] = ct.sum(axis=1)
for c in ["A", "B", "C"]:
    ct[f"{c}_pct"] = 100 * ct[c] / ct["total"]
ct = ct.sort_values("A_pct")  # menor -> maior, de baixo pra cima no barh


def plot_categoria_x_linguagem(embed_title: bool):
    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    left = np.zeros(len(ct))
    for cat in ["A", "B", "C"]:
        vals = ct[f"{cat}_pct"].values
        bars = ax.barh(ct.index, vals, left=left, color=CAT_COLOR[cat], label=CAT_LABEL[cat], height=0.62)
        for b, v, l in zip(bars, vals, left):
            if v >= 4:
                ax.text(l + v / 2, b.get_y() + b.get_height() / 2, f"{v:.0f}%",
                        ha="center", va="center", fontsize=8.5, color="white", fontweight="medium")
        left += vals
    ax.set_xlim(0, 100)
    ax.set_xlabel("% dos registros na linguagem")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=9, frameon=False)
    if embed_title:
        ax.set_title(f"Categoria semântica por linguagem principal do repositório (top {TOP_N_LANG})", fontsize=11, pad=14)
    return fig


fig = plot_categoria_x_linguagem(embed_title=True)
save(fig, "05_categoria_x_linguagem.png")

fig = plot_categoria_x_linguagem(embed_title=False)
SLIDES_DIR = ROOT / "figures" / "slides"
SLIDES_DIR.mkdir(parents=True, exist_ok=True)
fig.tight_layout()
fig.savefig(SLIDES_DIR / "categoria_x_linguagem.png", dpi=160, bbox_inches="tight")
plt.close(fig)

print(f"Corpus: {N_TOTAL:,} registros em {N_REPOS:,} repositórios com ocorrência".replace(",", "."))
print("Figuras geradas em", FIG_DIR, "e", SLIDES_DIR / "categoria_x_linguagem.png")
for f in sorted(FIG_DIR.glob("*.png")):
    print(" -", f.name)
