#!/usr/bin/env python3
"""Gera os gráficos de caracterização do corpus pro material de metodologia +
validação (reunião pós-decisão de 2026-08-11): sem quebra por categoria A/B/C
(abandonada) e sem issue_body (fora do escopo — mais distante de código do
que comentário/commit/PR). Roda sobre o corpus consolidado mais recente
(`data/full_run/ubw_collected_consolidated.csv`, rodadas A+B, 116.192
registros brutos antes deste filtro).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = ROOT / "figures" / "overview_v2"
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

COLOR_MAIN = "#378ADD"
COLOR_ALT = "#1D9E75"

ARTIFACT_ORDER = ["code_comment", "commit_message", "pr_body"]
ARTIFACT_LABEL = {
    "code_comment": "Comentário de código",
    "commit_message": "Mensagem de commit",
    "pr_body": "Corpo de PR",
}

raw = pd.read_csv(ROOT / "data" / "full_run" / "ubw_collected_consolidated.csv", low_memory=False)
N_RAW = len(raw)
df = raw[raw["artifact_type"] != "issue_body"].copy()
N_TOTAL = len(df)
N_REPOS = df["repo_full_name"].nunique()
N_ISSUE_DROPPED = N_RAW - N_TOTAL


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(FIG_DIR / name, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fmt(n) -> str:
    return f"{n:,}".replace(",", ".")


# --- 1. Distribuição por tipo de artefato ------------------------------------
fig, ax = plt.subplots(figsize=(6.2, 3.2))
vals = [int((df["artifact_type"] == a).sum()) for a in ARTIFACT_ORDER]
labels_pt = [ARTIFACT_LABEL[a] for a in ARTIFACT_ORDER]
bars = ax.barh(labels_pt[::-1], vals[::-1], color=COLOR_MAIN, height=0.5)
for b, v in zip(bars, vals[::-1]):
    pct = 100 * v / N_TOTAL
    ax.text(v + N_TOTAL * 0.008, b.get_y() + b.get_height() / 2, f"{fmt(v)} ({pct:.1f}%)",
            va="center", fontweight="medium", fontsize=9.5)
ax.set_xlabel("Registros")
ax.set_xlim(0, max(vals) * 1.28)
ax.set_title(f"Distribuição por tipo de artefato (N={fmt(N_TOTAL)})", fontsize=11)
save(fig, "01_artefato.png")

# --- 2. Distribuição por linguagem (top 15) ----------------------------------
TOP_N_LANG = 15
lang_counts = df["primary_language"].value_counts().head(TOP_N_LANG)
fig, ax = plt.subplots(figsize=(7, 6))
order = lang_counts.index[::-1]
vals = lang_counts.loc[order].values
bars = ax.barh(order, vals, color=COLOR_ALT, height=0.62)
for b, v in zip(bars, vals):
    pct = 100 * v / N_TOTAL
    ax.text(v + max(vals) * 0.012, b.get_y() + b.get_height() / 2, f"{fmt(v)} ({pct:.1f}%)",
            va="center", fontweight="medium", fontsize=8.5)
ax.set_xlabel("Registros")
ax.set_xlim(0, max(vals) * 1.24)
n_lang_total = df["primary_language"].nunique()
ax.set_title(f"Distribuição por linguagem principal — top {TOP_N_LANG} de {n_lang_total} (N={fmt(N_TOTAL)})", fontsize=11)
save(fig, "02_linguagem.png")

# --- 3. Ranking completo das 25 expressões do léxico -------------------------
fig, ax = plt.subplots(figsize=(7.5, 8.5))
expr_counts = df["matched_expression"].value_counts()
order = expr_counts.index[::-1]
vals = expr_counts.loc[order].values
bars = ax.barh(order, vals, color=COLOR_MAIN, height=0.65)
for b, v in zip(bars, vals):
    ax.text(v + max(vals) * 0.012, b.get_y() + b.get_height() / 2, fmt(v),
            va="center", fontweight="medium", fontsize=8.5)
ax.set_xlabel("Registros")
ax.set_xlim(0, max(vals) * 1.12)
ax.set_title(f"Todas as {len(expr_counts)} expressões do léxico (N={fmt(N_TOTAL)})", fontsize=11)
save(fig, "03_expressoes.png")

# --- 4. Artefato x Linguagem (top 10 linguagens, % empilhado) ---------------
TOP_N_LANG_STACK = 10
top_langs = df["primary_language"].value_counts().head(TOP_N_LANG_STACK).index.tolist()
ct = pd.crosstab(df[df["primary_language"].isin(top_langs)]["primary_language"], df["artifact_type"])
ct = ct.loc[top_langs]
ct["total"] = ct.sum(axis=1)
for a in ARTIFACT_ORDER:
    if a not in ct.columns:
        ct[a] = 0
    ct[f"{a}_pct"] = 100 * ct[a] / ct["total"]
ct = ct.sort_values("total")

fig, ax = plt.subplots(figsize=(8.2, 5.4))
left = np.zeros(len(ct))
ART_COLOR = {"code_comment": "#378ADD", "commit_message": "#1D9E75", "pr_body": "#EF9F27"}
for a in ARTIFACT_ORDER:
    vals = ct[f"{a}_pct"].values
    bars = ax.barh(ct.index, vals, left=left, color=ART_COLOR[a], label=ARTIFACT_LABEL[a], height=0.6)
    for b, v, l in zip(bars, vals, left):
        if v >= 4:
            ax.text(l + v / 2, b.get_y() + b.get_height() / 2, f"{v:.0f}%",
                    ha="center", va="center", fontsize=8.5, color="white", fontweight="medium")
    left += vals
ax.set_xlim(0, 100)
ax.set_xlabel("% dos registros na linguagem")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=9, frameon=False)
ax.set_title(f"Tipo de artefato por linguagem principal — top {TOP_N_LANG_STACK}", fontsize=11, pad=14)
save(fig, "04_artefato_x_linguagem.png")

# --- 5. Repositórios com mais ocorrências (top 15) ---------------------------
repo_counts = df["repo_full_name"].value_counts().head(15)
fig, ax = plt.subplots(figsize=(7, 6))
order = repo_counts.index[::-1]
vals = repo_counts.loc[order].values
bars = ax.barh(order, vals, color=COLOR_ALT, height=0.6)
for b, v in zip(bars, vals):
    ax.text(v + max(vals) * 0.012, b.get_y() + b.get_height() / 2, fmt(v),
            va="center", fontweight="medium", fontsize=8.5)
ax.set_xlabel("Registros")
ax.set_xlim(0, max(vals) * 1.15)
ax.set_title(f"Repositórios com mais ocorrências (top 15 de {fmt(N_REPOS)})", fontsize=11)
save(fig, "05_top_repos.png")

print(f"Corpus (sem issue_body): {fmt(N_TOTAL)} registros em {fmt(N_REPOS)} repositórios, "
      f"{n_lang_total} linguagens distintas.")
print(f"issue_body descartado deste recorte: {fmt(N_ISSUE_DROPPED)} registros "
      f"({100*N_ISSUE_DROPPED/N_RAW:.1f}% do bruto de {fmt(N_RAW)}).")
print("Figuras geradas em", FIG_DIR)
for f in sorted(FIG_DIR.glob("*.png")):
    print(" -", f.name)
