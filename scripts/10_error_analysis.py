#!/usr/bin/env python3
"""Análise de erro — Etapa 5 do PLANO_EXPERIMENTO_LLM.md.

Caracteriza os itens em que o juiz discorda do consenso humano. Não faz chamada
nova de API: a justificativa do modelo (`rationale`) já é gravada por item em
cada execução, então esta etapa é filtragem e leitura, não execução.

Duas perguntas:

1. **Onde erra?** O erro se concentra em algum tipo de artefato, alguma
   expressão do léxico, textos de certo comprimento, ou nos itens em que os
   próprios humanos não foram unânimes?
2. **Por que erra?** Confronta a justificativa que o modelo escreveu com a
   justificativa do anotador humano, para o subconjunto que tem as duas.

A sobreposição com os itens não-unânimes é a checagem mais informativa: se o
juiz erra justamente onde os humanos também divergiram, o "erro" é menos um
defeito do modelo e mais uma zona de ambiguidade genuína do critério.

Uso:
    python 10_error_analysis.py --set gold_dev_200 --judge <slug>
    python 10_error_analysis.py --set gold_dev_200          # usa o líder do relatório
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PANEL_DIR = ROOT / "validation" / "panel"
RUNS_DIR = PANEL_DIR / "runs"
ANALYSIS_DIR = PANEL_DIR / "analysis"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ubw.error_analysis")

ALERT_LABEL = "não-UBW"
ABSTAIN_LABEL = "incerto"


def _load_analysis_module():
    path = Path(__file__).resolve().parent / "08_panel_analysis.py"
    spec = importlib.util.spec_from_file_location("ubw_panel_analysis", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pick_leader(set_name: str) -> str:
    """Juiz de maior kappa penalizado no último relatório gerado."""
    path = ANALYSIS_DIR / f"{set_name}__judges.csv"
    if not path.exists():
        raise SystemExit(f"{path} não existe — rode 08_panel_analysis.py report primeiro")
    table = pd.read_csv(path)
    return str(table.sort_values("kappa_penalizado", ascending=False).iloc[0]["juiz"])


def load_judge(set_name: str, judge: str) -> pd.DataFrame:
    path = RUNS_DIR / set_name / f"{judge}.jsonl"
    if not path.exists():
        raise SystemExit(f"execução não encontrada: {path}")
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    votes = pd.DataFrame(records).drop_duplicates(subset="item_id", keep="last")
    votes["item_id"] = votes["item_id"].astype(str)
    return votes[["item_id", "label", "rationale", "ok"]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--set", default="gold_dev_200")
    parser.add_argument("--judge", help="slug do juiz (default: o líder do relatório)")
    args = parser.parse_args()

    judge = args.judge or pick_leader(args.set)
    logger.info("analisando erros de: %s", judge)

    gold = pd.read_csv(PANEL_DIR / f"{args.set}.csv")
    gold["item_id"] = gold["item_id"].astype(str)
    data = gold.merge(load_judge(args.set, judge), on="item_id", how="left")

    data["gold"] = data["is_ubw_gold"].astype(bool)
    data["decidiu"] = data["label"].isin(["UBW-verdadeiro", ALERT_LABEL])
    data["previu_positivo"] = data["label"].eq("UBW-verdadeiro")
    # Abstenção conta como não-alerta, mesma convenção do script 08.
    data["previu_efetivo"] = data["previu_positivo"] | data["label"].eq(ABSTAIN_LABEL)
    data["errou"] = data["previu_efetivo"] != data["gold"]
    data["comprimento"] = data["body_text"].fillna("").astype(str).str.len()

    errors = data[data["errou"]].copy()
    # Dois tipos de erro, com consequências diferentes para o dataset publicado:
    # deixar passar um falso positivo (o juiz disse UBW, o humano disse que não)
    # é o que a coluna deveria ter capturado; alertar num item bom gera ruído.
    errors["tipo"] = errors.apply(
        lambda r: "deixou passar (FP não detectado)" if r["gold"] is False or not r["gold"]
        else "alerta indevido (item bom marcado)", axis=1)

    n = len(data)
    logger.info("%d erros em %d itens (%.1f%%)", len(errors), n, 100 * len(errors) / n)

    lines = [
        f"# Análise de erro — {judge}",
        "",
        f"Conjunto `{args.set}`: {n} itens, {int(data['gold'].sum())} positivos e "
        f"{int((~data['gold']).sum())} negativos no gabarito humano.",
        f"O juiz erra em **{len(errors)} itens ({100 * len(errors) / n:.1f}%)**, "
        "contando abstenção como não-alerta.",
        "",
        "## Tipo de erro",
        "",
        errors["tipo"].value_counts().to_frame("itens").to_markdown(),
        "",
        "## Onde o erro se concentra",
        "",
        "### Por tipo de artefato",
        "",
    ]

    by_artifact = pd.DataFrame({
        "itens": data.groupby("artifact_type").size(),
        "erros": errors.groupby("artifact_type").size(),
    }).fillna(0).astype(int)
    by_artifact["taxa_erro"] = (by_artifact["erros"] / by_artifact["itens"]).round(3)
    lines += [by_artifact.to_markdown(), ""]

    lines += ["### Por expressão do léxico (só as com 5+ itens)", ""]
    counts = data["matched_expression"].value_counts()
    keep = counts[counts >= 5].index
    by_expr = pd.DataFrame({
        "itens": data[data["matched_expression"].isin(keep)].groupby("matched_expression").size(),
        "erros": errors[errors["matched_expression"].isin(keep)].groupby("matched_expression").size(),
    }).fillna(0).astype(int)
    by_expr["taxa_erro"] = (by_expr["erros"] / by_expr["itens"]).round(3)
    lines += [by_expr.sort_values("taxa_erro", ascending=False).to_markdown(), ""]

    # Comprimento: mediana em vez de média, porque a distribuição de body_text é
    # muito assimétrica (mediana 275 caracteres, máximo na casa dos milhares).
    lines += [
        "### Por comprimento do texto",
        "",
        f"- Mediana de caracteres nos itens **certos**: "
        f"{int(data.loc[~data['errou'], 'comprimento'].median())}",
        f"- Mediana de caracteres nos itens **errados**: "
        f"{int(errors['comprimento'].median())}",
        "",
    ]

    if "unanime" in data.columns:
        unanime = data["unanime"].astype(bool)
        err_nao_unanime = int((data["errou"] & ~unanime).sum())
        total_nao_unanime = int((~unanime).sum())
        err_unanime = int((data["errou"] & unanime).sum())
        total_unanime = int(unanime.sum())
        lines += [
            "### Sobreposição com a discordância humana",
            "",
            "| Itens | Total | Erros do juiz | Taxa |",
            "|---|---|---|---|",
            f"| Humanos **unânimes** | {total_unanime} | {err_unanime} | "
            f"{err_unanime / total_unanime:.1%} |",
            f"| Humanos **divergiram** | {total_nao_unanime} | {err_nao_unanime} | "
            f"{err_nao_unanime / total_nao_unanime:.1%} |" if total_nao_unanime else
            "| Humanos **divergiram** | 0 | — | — |",
            "",
            "Se a taxa de erro é muito maior onde os humanos divergiram, o juiz está "
            "errando na zona de ambiguidade genuína do critério, não em casos claros — "
            "leitura mais branda do erro.",
            "",
        ]

    # Exemplos concretos: o que o modelo escreveu contra o que o humano escreveu.
    lines += ["## Exemplos — justificativa do modelo vs. do anotador", ""]
    com_ambas = errors[errors["rationale_human"].fillna("").astype(str).str.strip() != ""]
    sample = com_ambas.head(8) if len(com_ambas) else errors.head(8)
    if not len(sample):
        lines.append("(nenhum erro para exibir)")
    for _, row in sample.iterrows():
        gold_txt = "UBW-verdadeiro" if row["gold"] else "não-UBW"
        body = " ".join(str(row["body_text"]).split())[:260]
        lines += [
            f"**`{row['matched_expression']}`** · {row['artifact_type']} · "
            f"humano: **{gold_txt}** · modelo: **{row['label']}**",
            "",
            f"> {body}",
            "",
            f"- *Modelo:* {str(row['rationale'])[:300]}",
        ]
        human = str(row.get("rationale_human", "")).strip()
        if human:
            lines.append(f"- *Anotador:* {human[:300]}")
        lines.append("")

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = ANALYSIS_DIR / f"{args.set}__error_analysis__{judge}.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    errors.to_csv(ANALYSIS_DIR / f"{args.set}__errors__{judge}.csv", index=False)
    print("\n".join(lines))
    logger.info("relatório em %s", report_path)


if __name__ == "__main__":
    main()
