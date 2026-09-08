#!/usr/bin/env python3
"""Figuras do Trilho B no escopo code_comment.

Três gráficos, todos a partir dos CSV já gravados por `08_panel_analysis.py` —
nenhuma chamada de API:

  1. `escada_tamanho.png`   kappa por número de parâmetros, dentro de cada
                            família. Responde "modelo maior resolve?".
  2. `correlacao_erro.png`  sobreposição dos vetores de erro entre os melhores
                            juízes. Responde "o painel adiciona algo?".
  3. `dev200_vs_eval371.png` por que o kappa da fatia code_comment da rodada
                            anterior não media nada.

Uso:
    python3 scripts/18_figuras_trilho_b.py
"""

from __future__ import annotations

import glob
import itertools
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
ANALISE = RAIZ / "validation" / "panel" / "analysis"
RUNS = RAIZ / "validation" / "panel" / "runs" / "eval_371"
SAIDA = RAIZ / "figures" / "trilho_b_cc"

# Parâmetros por modelo. `None` para os que não publicam o número — entram nos
# gráficos que não são de tamanho, mas ficam fora da escada.
PARAMETROS = {
    "google_gemma_3_4b_it": (4, "Gemma 3"),
    "google_gemma_3_12b_it": (12, "Gemma 3"),
    "google_gemma_3_27b_it": (27, "Gemma 3"),
    "qwen_qwen3_8b": (8, "Qwen 3"),
    "qwen_qwen3_14b": (14, "Qwen 3"),
    "qwen_qwen3_32b": (32, "Qwen 3"),
    "qwen_qwen3_235b_a22b_2507": (235, "Qwen 3 (MoE)"),
    "meta_llama_llama_3_1_8b_instruct": (8, "Llama 3.x"),
    "meta_llama_llama_3_3_70b_instruct": (70, "Llama 3.x"),
}
CURTO = {
    "anthropic_claude_sonnet_5": "Sonnet 5",
    "x_ai_grok_4_3": "Grok 4.3",
    "minimax_minimax_m2_5": "MiniMax M2.5",
    "meta_llama_llama_3_3_70b_instruct": "Llama 70B",
    "qwen_qwen3_14b": "Qwen 14B",
    "qwen_qwen3_235b_a22b_2507": "Qwen 235B",
    "minimax_minimax_m2_5 ": "MiniMax",
}

KAPPA_HUMANO = (0.787, 0.829)  # faixa par a par entre os três anotadores
COR = {"Gemma 3": "#c2410c", "Qwen 3": "#1d4ed8",
       "Qwen 3 (MoE)": "#60a5fa", "Llama 3.x": "#15803d"}


def carrega_juizes() -> pd.DataFrame:
    d = pd.read_csv(ANALISE / "eval_371__judges.csv")
    d = d[d.juiz.str.endswith("k8")].copy()
    d["m"] = d.juiz.str.replace("_fewshot_cc_k8", "", regex=False)
    return d


def fig_escada(d: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.axhspan(*KAPPA_HUMANO, color="#16a34a", alpha=0.12, zorder=0)
    ax.text(235, 0.845, "concordância entre os 3 anotadores humanos",
            fontsize=8.5, color="#166534", va="center", ha="right")

    for fam in ("Gemma 3", "Qwen 3", "Llama 3.x"):
        pts = sorted((PARAMETROS[m][0], k, m) for m, k in
                     zip(d.m, d.kappa_penalizado)
                     if m in PARAMETROS and PARAMETROS[m][1] == fam)
        if not pts:
            continue
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-",
                color=COR[fam], label=fam, lw=2, ms=7)

    # O MoE entra solto: 235 B de parâmetros com 22 B ativos por token não é
    # comparável aos densos na mesma curva.
    moe = [(PARAMETROS[m][0], k) for m, k in zip(d.m, d.kappa_penalizado)
           if m in PARAMETROS and PARAMETROS[m][1] == "Qwen 3 (MoE)"]
    if moe:
        ax.plot(*zip(*moe), "s", color=COR["Qwen 3 (MoE)"], ms=9,
                label="Qwen 3 235B (MoE, 22B ativos)")

    # Grok 4.3 e Sonnet 5 têm o MESMO kappa (0,537214, até a sexta decimal), o
    # que é justamente o achado. Uma linha e um rótulo só — dois rótulos
    # sobrepostos escondiam a informação em vez de mostrá-la.
    sem_tamanho = {"x_ai_grok_4_3": "Grok 4.3",
                   "anthropic_claude_sonnet_5": "Sonnet 5"}
    valores = {r: float(d.loc[d.m == m, "kappa_penalizado"].iloc[0])
               for m, r in sem_tamanho.items()
               if len(d.loc[d.m == m])}
    if valores:
        nivel = max(valores.values())
        ax.axhline(nivel, ls="--", lw=1.3, color="#6b7280")
        juntos = " = ".join(sorted(valores, key=lambda r: -valores[r]))
        ax.text(235, nivel + 0.018,
                f"{juntos}  (κ {nivel:.3f}, sem escala de parâmetros)",
                fontsize=8.5, color="#374151", ha="right")

    ax.set_xscale("log")
    ax.set_xticks([4, 8, 14, 27, 32, 70, 235])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_xlabel("parâmetros do modelo (bilhões, escala log)")
    ax.set_ylabel("κ de Cohen contra o gabarito humano")
    ax.set_title("Tamanho do modelo não prediz desempenho na tarefa",
                 fontsize=12, loc="left")
    ax.set_ylim(-0.03, 0.90)
    ax.legend(fontsize=8.5, loc="upper left", framealpha=0.9)
    ax.grid(alpha=0.25, ls=":")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(SAIDA / "escada_tamanho.png", dpi=170)
    plt.close(fig)


def vetores_de_erro() -> dict[str, set[str]]:
    e = pd.read_csv(RAIZ / "validation/panel/cc/eval_371.csv")
    e["item_id"] = e.item_id.astype(str)
    gold = dict(zip(e.item_id, e.gold.astype(bool)))
    erros = {}
    for f in glob.glob(str(RUNS / "*k8.jsonl")):
        nome = Path(f).stem.replace("_fewshot_cc_k8", "")
        votos = {str(r["item_id"]): r["label"]
                 for r in (json.loads(l) for l in open(f)) if r.get("ok")}
        erros[nome] = {i for i, g in gold.items()
                       if i in votos and (votos[i] == "não-UBW") != (not g)}
    return erros


def fig_correlacao(d: pd.DataFrame) -> None:
    erros = vetores_de_erro()
    top = list(d.nlargest(5, "kappa_penalizado").m)
    n = len(top)
    M = [[0.0] * n for _ in range(n)]
    for i, j in itertools.product(range(n), repeat=2):
        a, b = erros[top[i]], erros[top[j]]
        M[i][j] = len(a & b) / len(a | b) if (a | b) else 0.0

    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    im = ax.imshow(M, cmap="Oranges", vmin=0, vmax=1)
    rot = [CURTO.get(t, t)[:14] for t in top]
    ax.set_xticks(range(n), rot, rotation=35, ha="right", fontsize=9)
    ax.set_yticks(range(n), rot, fontsize=9)
    for i, j in itertools.product(range(n), repeat=2):
        ax.text(j, i, f"{M[i][j]:.2f}", ha="center", va="center", fontsize=9.5,
                color="white" if M[i][j] > 0.55 else "#1f2937")
    ax.set_title("Os juízes erram nos mesmos itens\n"
                 "sobreposição dos vetores de erro (Jaccard)",
                 fontsize=11.5, loc="left")
    fig.colorbar(im, ax=ax, shrink=0.8, label="fração de erros em comum")
    fig.tight_layout()
    fig.savefig(SAIDA / "correlacao_erro.png", dpi=170)
    plt.close(fig)


def fig_dev200(d: pd.DataFrame) -> None:
    """Por que o kappa da fatia code_comment do dev200 não media nada."""
    g = pd.read_csv(RAIZ / "validation/panel/gold_dev_200.csv", low_memory=False)
    cc = g[g.artifact_type == "code_comment"]
    gold_cc = dict(zip(cc.item_id.astype(str), cc.is_ubw_gold.astype(bool)))

    kappas = []
    for f in glob.glob(str(RAIZ / "validation/panel/runs/gold_dev_200/*.jsonl")):
        votos = {str(r["item_id"]): r["label"]
                 for r in (json.loads(l) for l in open(f)) if r.get("ok")}
        ids = [i for i in gold_cc if i in votos and votos[i] != "incerto"]
        if len(ids) < 50:
            continue
        pred = [votos[i] == "UBW-verdadeiro" for i in ids]
        ref = [gold_cc[i] for i in ids]
        n = len(ids)
        a = sum(1 for x, y in zip(pred, ref) if x and y)
        dd = sum(1 for x, y in zip(pred, ref) if not x and not y)
        b = sum(1 for x, y in zip(pred, ref) if x and not y)
        c = n - a - dd - b
        po = (a + dd) / n
        pe = ((a + b) / n) * ((a + c) / n) + ((c + dd) / n) * ((b + dd) / n)
        kappas.append((po - pe) / (1 - pe) if pe < 1 else float("nan"))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.4))
    ax1.hist([k for k in kappas if k == k], bins=20, color="#9ca3af",
             edgecolor="white")
    ax1.axvline(1.0, color="#b91c1c", lw=2)
    n_um = sum(1 for k in kappas if k == 1.0)
    ax1.text(0.98, ax1.get_ylim()[1] * 0.92, f"{n_um} de {len(kappas)} juízes\ncom κ = 1,000",
             ha="right", fontsize=9.5, color="#b91c1c")
    ax1.set_title("Rodada anterior: 57 itens, 1 negativo",
                  fontsize=11, loc="left")
    ax1.set_xlabel("κ na fatia de comentários de código")
    ax1.set_ylabel("nº de configurações de juiz")

    ax2.hist(d.kappa_penalizado.dropna(), bins=20, color="#1d4ed8",
             edgecolor="white")
    ax2.axvspan(*KAPPA_HUMANO, color="#16a34a", alpha=0.15)
    ax2.text(0.808, ax2.get_ylim()[1] * 0.9, "humanos", rotation=90,
             ha="center", fontsize=9, color="#166534")
    ax2.set_title("Esta rodada: 371 itens, 24 negativos",
                  fontsize=11, loc="left")
    ax2.set_xlabel("κ contra o gabarito humano")
    for ax in (ax1, ax2):
        ax.set_xlim(-0.1, 1.05)
        ax.grid(alpha=0.2, ls=":", axis="y")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    fig.suptitle("Um único negativo torna o κ inútil: acertar 1 item dava nota máxima",
                 fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(SAIDA / "dev200_vs_eval371.png", dpi=170)
    plt.close(fig)


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    d = carrega_juizes()
    fig_escada(d)
    fig_correlacao(d)
    fig_dev200(d)
    for p in sorted(SAIDA.glob("*.png")):
        print(f"  {p.relative_to(RAIZ)}  ({p.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
