#!/usr/bin/env python3
"""Relatório descritivo do corpus — números para o paper do MSR Data Showcase.

Gera, a partir de um snapshot do corpus e da amostra anotada, todas as tabelas
que as seções Dataset Schema e Dataset Utility precisam, mais as figuras. Um
comando, saída determinística, para que congelar o v1.0 seja rodar de novo e
comparar.

O que sai:

    01_visao_geral          registros, repositórios, período, linguagens
    02_por_artefato         volume, participação e comprimento do texto
    04_por_expressao        volume por expressão, as 25
    05_por_repositorio      concentração: mediana, cauda, participação do topo
    06_temporal             registros por ano de criação
    07_sobrevivencia        remoção observada, só onde o evento é real
    08_precisao             precisão da amostra humana, global e por corte
    09_linguagens           linguagens principais dos repositórios

Sobre a Seção 07: o evento de remoção só tem o mesmo significado em
`code_comment`, onde vem do pareamento de eventos `+` e `-` do `git log -S`. Em
`pr_body`, `removed_at` é `merged_at` ou `closed_at`, isto é, fechamento de pull
request, que não é remoção de dívida. Misturar os dois numa curva só produz uma
curva de tempo até PR fechar. O relatório separa, e a separação é o ponto.

Uso:
    python 20_dataset_report.py \
        --corpus ../data/full_run/ubw_collected_consolidated.csv \
        --sample ../validation/panel/cc/human_gold_379.csv \
        --out-dir ../validation/dataset_report
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ubw.lexicon import all_expressions  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ubw.dataset_report")

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CORPUS = ROOT / "data" / "full_run" / "ubw_collected_consolidated.csv"
DEFAULT_SAMPLE = ROOT / "validation" / "panel" / "cc" / "human_gold_379.csv"
DEFAULT_OUT = ROOT / "validation" / "dataset_report"

# `issue_body` saiu da análise na reunião de 29/07/2026 (mediana de texto ~5x
# maior que a dos outros canais, conversacional). Continua coletado; fica fora
# do frame de amostragem e de todo número reportado.
EXCLUDED_ARTIFACTS = ("issue_body",)

# Só onde o evento de remoção significa remoção da dívida. Ver docstring.
SURVIVAL_ARTIFACTS = ("code_comment",)


def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """IC de Wilson para proporção. Preferido ao normal porque os cortes por
    estrato têm dezenas de itens e proporções perto de 1, onde a aproximação
    normal produz limite superior acima de 100%."""
    if n == 0:
        return float("nan"), float("nan")
    p = successes / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - margin) / denom, (centre + margin) / denom


def load_corpus(path: Path, exclude: tuple[str, ...]) -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(path, low_memory=False)
    raw = {"registros": len(df), "repositorios": int(df["repo_full_name"].nunique())}
    if exclude:
        df = df[~df["artifact_type"].isin(exclude)].copy()
    df["chars"] = df["body_text"].astype(str).str.len()
    df["created"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    df["ano"] = df["created"].dt.year
    return df, raw


# ---------------------------------------------------------------------------
# Tabelas
# ---------------------------------------------------------------------------


def t_visao_geral(df: pd.DataFrame, raw: dict, exclude: tuple[str, ...]) -> pd.DataFrame:
    validos = df["created"].dropna()
    rows = [
        ("Registros no corpus bruto", f"{raw['registros']:,}"),
        ("Repositórios no corpus bruto", f"{raw['repositorios']:,}"),
    ]
    if "escopo" in raw:
        rows += [
            (f"Registros no frame (sem {', '.join(exclude)})", f"{raw['registros_frame']:,}"),
            (f"Escopo do relatório", ", ".join(raw["escopo"])),
            ("Participação do escopo no frame",
             f"{len(df) / raw['registros_frame']:.1%}"),
        ]
    rows += [
        (f"Registros no escopo", f"{len(df):,}"),
        ("Repositórios com ao menos uma ocorrência", f"{df['repo_full_name'].nunique():,}"),
        ("Expressões do léxico", f"{len(all_expressions())}"),
        ("Expressões com ao menos uma ocorrência", f"{df['matched_expression'].nunique()}"),
        ("Linguagens principais distintas", f"{df['primary_language'].nunique()}"),
        ("Primeira ocorrência", str(validos.min().date()) if len(validos) else "—"),
        ("Última ocorrência", str(validos.max().date()) if len(validos) else "—"),
        ("Comprimento mediano do texto (caracteres)", f"{int(df['chars'].median())}"),
    ]
    return pd.DataFrame(rows, columns=["Métrica", "Valor"])


def t_por_artefato(df: pd.DataFrame) -> pd.DataFrame:
    out = df.groupby("artifact_type").agg(
        registros=("artifact_type", "size"),
        repositorios=("repo_full_name", "nunique"),
        chars_mediana=("chars", "median"),
        chars_p90=("chars", lambda s: s.quantile(0.9)),
    )
    out["participacao"] = (out["registros"] / len(df)).round(4)
    return out.reset_index().sort_values("registros", ascending=False)


def t_por_expressao(df: pd.DataFrame) -> pd.DataFrame:
    counts = df.groupby("matched_expression").agg(
        registros=("matched_expression", "size"),
        repositorios=("repo_full_name", "nunique"),
    )
    # As 25 do léxico, inclusive as que não apareceram: expressão com zero
    # ocorrência é resultado, não linha faltando.
    todas = pd.DataFrame({"matched_expression": all_expressions()}).set_index("matched_expression")
    out = todas.join(counts).fillna({"registros": 0, "repositorios": 0})
    out["participacao"] = (out["registros"] / len(df)).round(5)
    return out.reset_index().sort_values("registros", ascending=False).astype(
        {"registros": int, "repositorios": int})


def t_por_repositorio(df: pd.DataFrame) -> pd.DataFrame:
    counts = df.groupby("repo_full_name").size().sort_values(ascending=False)
    total = counts.sum()
    rows = [
        ("Repositórios com ocorrência", f"{len(counts):,}"),
        ("Ocorrências por repositório, mediana", f"{counts.median():.0f}"),
        ("Ocorrências por repositório, média", f"{counts.mean():.1f}"),
        ("Ocorrências por repositório, p90", f"{counts.quantile(0.9):.0f}"),
        ("Ocorrências por repositório, máximo", f"{counts.max():,}"),
        ("Repositórios com exatamente 1 ocorrência", f"{int((counts == 1).sum()):,} "
                                                     f"({(counts == 1).mean():.1%})"),
        ("Repositórios com 3 ou mais (subconjunto de RQ2)", f"{int((counts >= 3).sum()):,} "
                                                            f"({(counts >= 3).mean():.1%})"),
        ("Participação dos 10 maiores repositórios", f"{counts.head(10).sum() / total:.2%}"),
        ("Participação dos 1% maiores", f"{counts.head(max(1, len(counts) // 100)).sum() / total:.2%}"),
    ]
    return pd.DataFrame(rows, columns=["Métrica", "Valor"])


def t_temporal(df: pd.DataFrame) -> pd.DataFrame:
    out = df.dropna(subset=["ano"]).groupby("ano").agg(
        registros=("ano", "size"),
        repositorios=("repo_full_name", "nunique"),
    )
    out["participacao"] = (out["registros"] / out["registros"].sum()).round(4)
    return out.reset_index().astype({"ano": int})


def t_sobrevivencia(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Duas tabelas: o resumo por artefato, com a ressalva do significado do
    evento, e a curva de Kaplan-Meier apenas onde o evento é remoção de fato."""
    resumo = []
    for artefato, grupo in df.groupby("artifact_type"):
        observado = grupo["removed_at"].notna()
        semantica = ("remoção do comentário (git log -S)" if artefato in SURVIVAL_ARTIFACTS
                     else "fechamento/merge do artefato, NÃO é remoção de dívida")
        resumo.append({
            "artefato": artefato,
            "registros": len(grupo),
            "evento_observado": int(observado.sum()),
            "taxa_evento": round(observado.mean(), 4),
            "dias_mediana_ate_evento": grupo.loc[observado, "time_to_event_days"].median(),
            "significado_do_evento": semantica,
        })
    resumo_df = pd.DataFrame(resumo).sort_values("registros", ascending=False)

    alvo = df[df["artifact_type"].isin(SURVIVAL_ARTIFACTS)]
    km = kaplan_meier(alvo["time_to_event_days"], alvo["removed_at"].notna())
    return resumo_df, km


def kaplan_meier(durations: pd.Series, observed: pd.Series) -> pd.DataFrame:
    """Estimador de Kaplan-Meier. Implementado aqui, em vez de puxar o
    lifelines, porque é a única coisa que precisaríamos dele nesta etapa e a
    fórmula cabe em dez linhas: S(t) = prod (1 - d_i / n_i) sobre os tempos de
    evento, com n_i o número em risco imediatamente antes de t_i."""
    frame = pd.DataFrame({"t": pd.to_numeric(durations, errors="coerce"),
                          "e": observed.astype(bool)}).dropna(subset=["t"])
    frame = frame.sort_values("t")
    n = len(frame)
    rows, survival, at_risk = [], 1.0, n
    for t, grupo in frame.groupby("t"):
        eventos = int(grupo["e"].sum())
        if eventos:
            survival *= 1 - eventos / at_risk
        rows.append({"dias": float(t), "em_risco": at_risk, "eventos": eventos,
                     "sobrevivencia": survival})
        at_risk -= len(grupo)
    return pd.DataFrame(rows)


def t_precisao(sample: pd.DataFrame) -> pd.DataFrame:
    """Precisão do léxico medida na amostra anotada por humanos, global e por
    tipo de artefato, que é a única dimensão com desenho por trás: a amostra foi
    estratificada por ela. A categoria A/B/C do léxico deixou de ser dimensão
    analítica na reunião de 29/07/2026 e não é reportada."""
    coluna_gold = "is_ubw_gold" if "is_ubw_gold" in sample.columns else "gold"
    gold = sample[coluna_gold].astype(bool)
    rows = [_precision_row("Global", "todos", gold)]
    if "artifact_type" in sample.columns and sample["artifact_type"].nunique() > 1:
        for valor, indices in sample.groupby("artifact_type").groups.items():
            rows.append(_precision_row("tipo de artefato", str(valor), gold.loc[indices]))
    return pd.DataFrame(rows)


def _precision_row(corte: str, valor: str, gold: pd.Series) -> dict:
    n, k = len(gold), int(gold.sum())
    low, high = wilson_ci(k, n)
    return {
        "corte": corte, "valor": valor, "n": n, "positivos": k,
        "precisao": round(k / n, 4) if n else float("nan"),
        "ic95_low": round(low, 4), "ic95_high": round(high, 4),
        "largura_pp": round((high - low) * 100, 1),
    }


def t_linguagens(df: pd.DataFrame, top: int = 15) -> pd.DataFrame:
    out = df.groupby("primary_language").agg(
        registros=("primary_language", "size"),
        repositorios=("repo_full_name", "nunique"),
    ).sort_values("registros", ascending=False)
    out["participacao"] = (out["registros"] / len(df)).round(4)
    return out.head(top).reset_index()


# ---------------------------------------------------------------------------
# Figuras
# ---------------------------------------------------------------------------


def make_figures(df: pd.DataFrame, temporal: pd.DataFrame, km: pd.DataFrame,
                 out_dir: Path) -> list[Path]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []

    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.bar(temporal["ano"], temporal["registros"], color="#3b6ea5")
    ax.set_xlabel("Ano de criação do artefato")
    ax.set_ylabel("Registros")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    path = out_dir / "temporal.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    saved.append(path)

    top = df["matched_expression"].value_counts().head(10).sort_values()
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.barh(top.index, top.to_numpy(), color="#3b6ea5")
    ax.set_xlabel("Registros")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    path = out_dir / "top_expressoes.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    saved.append(path)

    if len(km):
        fig, ax = plt.subplots(figsize=(7, 3.2))
        ax.step(km["dias"], km["sobrevivencia"], where="post", color="#a5433b")
        ax.set_xlabel("Dias desde a introdução")
        ax.set_ylabel("Fração ainda presente")
        ax.set_ylim(0, 1)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        path = out_dir / "sobrevivencia_code_comment.png"
        fig.savefig(path, dpi=200)
        plt.close(fig)
        saved.append(path)

    return saved


# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    parser.add_argument("--sample", default=str(DEFAULT_SAMPLE))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--include-issue-body", action="store_true",
                        help="mantém issue_body no relatório (fora do padrão)")
    parser.add_argument("--only", nargs="*", metavar="ARTEFATO",
                        help="restringe o relatório a estes tipos de artefato "
                             "(ex.: --only code_comment, para o escopo publicado)")
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    exclude = () if args.include_issue_body else EXCLUDED_ARTIFACTS

    df, raw = load_corpus(Path(args.corpus), exclude)
    logger.info("corpus: %d registros após exclusões, de %d brutos", len(df), raw["registros"])
    if args.only:
        antes = len(df)
        df = df[df["artifact_type"].isin(args.only)].copy()
        logger.info("escopo restrito a %s: %d de %d registros",
                    ", ".join(args.only), len(df), antes)
        raw["escopo"] = list(args.only)
        raw["registros_frame"] = antes

    sobrevivencia, km = t_sobrevivencia(df)
    tabelas = {
        "01_visao_geral": t_visao_geral(df, raw, exclude or ("nenhum",)),
        "02_por_artefato": t_por_artefato(df),
        "04_por_expressao": t_por_expressao(df),
        "05_por_repositorio": t_por_repositorio(df),
        "06_temporal": t_temporal(df),
        "07_sobrevivencia": sobrevivencia,
        "09_linguagens": t_linguagens(df),
    }

    sample_path = Path(args.sample)
    if sample_path.exists():
        tabelas["08_precisao"] = t_precisao(pd.read_csv(sample_path))
    else:
        logger.warning("amostra não encontrada em %s; seção de precisão omitida", sample_path)

    for nome, tabela in tabelas.items():
        tabela.to_csv(out_dir / f"{nome}.csv", index=False)
    km.to_csv(out_dir / "07_km_code_comment.csv", index=False)

    figuras = [] if args.no_figures else make_figures(df, tabelas["06_temporal"], km,
                                                      out_dir / "figuras")

    linhas = [
        "# Relatório descritivo do corpus UBW",
        "",
        f"Gerado de `{args.corpus}`.",
        "Números sujeitos a mudança até o congelamento do snapshot v1.0.",
        "",
    ]
    titulos = {
        "01_visao_geral": "Visão geral",
        "02_por_artefato": "Por tipo de artefato",
        "04_por_expressao": "Por expressão",
        "05_por_repositorio": "Concentração por repositório",
        "06_temporal": "Distribuição temporal",
        "07_sobrevivencia": "Evento de remoção, por artefato",
        "08_precisao": "Precisão do léxico na amostra humana",
        "09_linguagens": "Linguagens principais",
    }
    for nome, tabela in tabelas.items():
        linhas += [f"## {titulos[nome]}", "", tabela.to_markdown(index=False, floatfmt=".4g"), ""]
        if nome == "07_sobrevivencia":
            linhas += [
                "O evento só significa remoção de dívida em `code_comment`, onde vem do "
                "pareamento de eventos `+` e `-` do `git log -S`. Em `pr_body` é merge ou "
                "fechamento do pull request. Curva de Kaplan-Meier em "
                "`07_km_code_comment.csv`, restrita a `code_comment`.",
                "",
            ]
    if figuras:
        linhas += ["## Figuras", ""] + [f"- `{p.relative_to(out_dir)}`" for p in figuras] + [""]

    (out_dir / "RELATORIO.md").write_text("\n".join(linhas), encoding="utf-8")
    logger.info("relatório em %s", out_dir / "RELATORIO.md")


if __name__ == "__main__":
    main()
