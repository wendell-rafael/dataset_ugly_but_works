#!/usr/bin/env python3
"""Gera os gráficos (PNG) usados em RESULTADOS_PILOTO.md.

Roda uma única vez sobre os dados já coletados (data/ubw_collected_full.csv,
data/repo_occurrence_counts.csv) e os números fixos da rodada 1 registrados
na análise do piloto de 20 repositórios (antes da correção de vendoring).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = ROOT / "figures"
FIG_DIR.mkdir(exist_ok=True)

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
COLOR_WARN = "#E24B4A"
COLOR_OK = "#639922"

df = pd.read_csv(ROOT / "data" / "ubw_collected_full.csv")

# Números da rodada 1 (piloto de 20 repos), registrados antes da correção
# de vendoring/schema — servem só para o gráfico comparativo.
ROUND1 = {
    "total_records": 28,
    "repos_with_occurrence": 6,
    "repos_total": 20,
    "vendoring_pct": 73,
    "category": {"A": 5, "B": 2, "C": 21},
    "artifact_type": {"code_comment": 22, "pr_body": 5, "issue_body": 1, "commit_message": 0},
}

ROUND2 = {
    "total_records": len(df),
    "repos_with_occurrence": df["repo_full_name"].nunique(),
    "repos_total": 140,
    "vendoring_pct": 0,
    "category": df["category_ubw"].value_counts().to_dict(),
    "artifact_type": df["artifact_type"].value_counts().to_dict(),
}


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(FIG_DIR / name, dpi=160, bbox_inches="tight")
    plt.close(fig)


# --- 1. Registros totais: rodada 1 vs rodada 2 -------------------------------
fig, ax = plt.subplots(figsize=(5.5, 3.2))
rounds = ["Rodada 1\n(20 repos)", "Rodada 2\n(140 repos)"]
values = [ROUND1["total_records"], ROUND2["total_records"]]
bars = ax.bar(rounds, values, color=[COLOR_NEUTRAL, COLOR_NEUTRAL], width=0.5)
for b, v in zip(bars, values):
    ax.text(b.get_x() + b.get_width() / 2, v + 1.5, str(v), ha="center", fontweight="medium")
ax.set_ylabel("Registros coletados")
ax.set_ylim(0, max(values) * 1.25)
save(fig, "01_registros_totais.png")

# --- 2. Repositórios com ocorrência (proporção) ------------------------------
fig, ax = plt.subplots(figsize=(5.5, 3.2))
labels = ["Rodada 1", "Rodada 2"]
with_occ = [ROUND1["repos_with_occurrence"], ROUND2["repos_with_occurrence"]]
totals = [ROUND1["repos_total"], ROUND2["repos_total"]]
without_occ = [t - w for t, w in zip(totals, with_occ)]
ax.bar(labels, with_occ, label="Com ocorrência UBW", color=COLOR_B, width=0.5)
ax.bar(labels, without_occ, bottom=with_occ, label="Zero ocorrências (denominador RQ1)", color="#D3D1C7", width=0.5)
for i, (w, t) in enumerate(zip(with_occ, totals)):
    ax.text(i, t + 2, f"{w}/{t} ({100*w/t:.0f}%)", ha="center", fontweight="medium", fontsize=10)
ax.set_ylabel("Repositórios")
ax.set_ylim(0, max(totals) * 1.2)
ax.legend(loc="upper left", fontsize=9, frameon=False)
save(fig, "02_repos_com_ocorrencia.png")

# --- 3. Contaminação por vendoring: antes/depois -----------------------------
fig, ax = plt.subplots(figsize=(5.5, 3.2))
labels = ["Rodada 1\n(antes do filtro)", "Rodada 2\n(depois do filtro)"]
values = [ROUND1["vendoring_pct"], ROUND2["vendoring_pct"]]
colors = [COLOR_WARN, COLOR_OK]
bars = ax.bar(labels, values, color=colors, width=0.5)
for b, v in zip(bars, values):
    ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v}%", ha="center", fontweight="medium")
ax.set_ylabel("% de code_comment em paths vendorizados")
ax.set_ylim(0, 100)
save(fig, "03_vendoring_antes_depois.png")

# --- 4. Categoria A/B/C (rodada 2) -------------------------------------------
fig, ax = plt.subplots(figsize=(5.5, 3.2))
cats = ["A — estética", "B — workaround", "C — incerteza"]
vals = [ROUND2["category"].get("A", 0), ROUND2["category"].get("B", 0), ROUND2["category"].get("C", 0)]
bars = ax.bar(cats, vals, color=[COLOR_A, COLOR_B, COLOR_C], width=0.55)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 1, str(v), ha="center", fontweight="medium")
ax.set_ylabel("Registros")
ax.set_ylim(0, max(vals) * 1.25)
save(fig, "04_categoria_rodada2.png")

# --- 5. Tipo de artefato (rodada 2) ------------------------------------------
fig, ax = plt.subplots(figsize=(5.5, 3.2))
order = ["code_comment", "commit_message", "pr_body", "issue_body"]
vals = [ROUND2["artifact_type"].get(k, 0) for k in order]
bars = ax.barh(order, vals, color=COLOR_NEUTRAL, height=0.55)
for b, v in zip(bars, vals):
    ax.text(v + 1, b.get_y() + b.get_height() / 2, str(v), va="center", fontweight="medium")
ax.set_xlabel("Registros")
ax.invert_yaxis()
ax.set_xlim(0, max(vals) * 1.25)
save(fig, "05_artefato_rodada2.png")

# --- 6. Top expressões (rodada 2), com destaque para as de alto risco --------
fig, ax = plt.subplots(figsize=(6, 3.6))
expr_counts = df["matched_expression"].value_counts().head(8)
high_risk = {"magic number", "don't touch"}
colors = [COLOR_WARN if e in high_risk else COLOR_NEUTRAL for e in expr_counts.index]
bars = ax.barh(expr_counts.index[::-1], expr_counts.values[::-1], color=colors[::-1], height=0.6)
for b, v in zip(bars, expr_counts.values[::-1]):
    ax.text(v + 0.8, b.get_y() + b.get_height() / 2, str(v), va="center", fontweight="medium", fontsize=9)
ax.set_xlabel("Registros")
ax.set_xlim(0, expr_counts.max() * 1.2)
save(fig, "06_top_expressoes.png")

# --- 7. Precisão manual amostrada: alto risco vs baixo risco -----------------
fig, ax = plt.subplots(figsize=(5.5, 3.2))
groups = ["magic number\n(10 checados)", "don't touch\n(12 checados)", "expressões de\nrisco A/B (28)"]
true_positive_pct = [0, 0, 100]
bars = ax.bar(groups, true_positive_pct, color=[COLOR_WARN, COLOR_WARN, COLOR_OK], width=0.55)
for b, v in zip(bars, true_positive_pct):
    ax.text(b.get_x() + b.get_width() / 2, v + 3, f"{v}%", ha="center", fontweight="medium")
ax.set_ylabel("% verdadeiro positivo (inspeção manual)")
ax.set_ylim(0, 115)
save(fig, "07_precisao_amostrada.png")

print("Figuras geradas em", FIG_DIR)
for f in sorted(FIG_DIR.glob("*.png")):
    print(" -", f.name)
