#!/usr/bin/env python3
"""Fase 1d — Relatório de precisão pós-anotação: por expressão, categoria e
artefato, com IC de Wilson, reponderação pelos pesos reais dos estratos, e
o teste de especificidade sobre os near-miss adversariais (Agente B,
`validation/B_PLANO_AUDITORIA_FP.md`, Seções 1-2). Não substitui
`03_metrics_llm_triage.py metrics` — reusa `agreement_report` de lá (import,
sem alterar o arquivo) para κ/AC1, e cobre o que falta: precisão com IC,
reponderação, e especificidade.

Contrato de entrada — `--annotations` é um CSV longo com uma linha por
(item, anotador), contendo pelo menos:
    item_id, artifact_type, matched_expression, category_ubw,
    annotator_id, is_ubw, category_confirmed, confidence

`sample_stratum` (de qual pool de `03b` o item veio) deve estar presente —
normalmente juntando o `_internal_stratum_map_*.csv` gerado por
`03c_generate_batches.py` pelo `item_id`. Itens com `sample_stratum ==
"calibration"` são descartados automaticamente (Seção 3: calibração não
entra no κ nem na precisão final — independência já foi quebrada pela
discussão em grupo).

`--tiebreak-annotators` identifica o(s) ID(s) de anotador usados para
desempate (Seção 7, regra 4 do guideline) — o rótulo final de um item vem
do 3º anotador quando presente; senão, do consenso dos dois primários;
itens sem consenso e sem desempate ficam marcados `unresolved` e são
excluídos da precisão (contados e reportados, nunca descartados
silenciosamente).

Subcomandos:
    report   roda tudo: agreement_report (κ/AC1), precisão por expressão/
             categoria/artefato com Wilson CI, precisão global reponderada,
             especificidade sobre near-miss adversarial

Exemplo:
    python 03d_precision_report.py report \
        --annotations ../validation/annotations_long_final.csv \
        --weights ../validation/sample_final/sampling_weights_oficial.csv \
        --out-dir ../validation/precision_report_final
"""
from __future__ import annotations

import argparse
import logging
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

import importlib.util as _ilu  # noqa: E402


def _load_script03():
    path = Path(__file__).resolve().parent / "03_metrics_llm_triage.py"
    spec = _ilu.spec_from_file_location("ubw_script03", path)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


m03 = _load_script03()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ubw.precision_report")

Z_95 = 1.959963985  # z para IC de 95% (Wilson)
ACCEPTABLE_PRECISION_FLOOR = 0.50  # limiar de alerta (não gatilho automático — Seção 4)


def wilson_ci(successes: int, n: int, z: float = Z_95) -> tuple[float, float, float]:
    """Intervalo de Wilson para proporção binomial (Brown, Cai & DasGupta,
    2001) — mais adequado que Wald para n pequeno e p perto de 0 ou 1,
    exatamente o caso das expressões raras do léxico UBW (insumo do Agente
    A, P7). Retorna (p_hat, limite_inferior, limite_superior)."""
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    p_hat = successes / n
    denom = 1 + z**2 / n
    center = (p_hat + z**2 / (2 * n)) / denom
    half_width = (z * math.sqrt((p_hat * (1 - p_hat) / n) + (z**2 / (4 * n**2)))) / denom
    return (p_hat, max(0.0, center - half_width), min(1.0, center + half_width))


# Estratos em que um item single-anotado ainda entra em precisão/reponderação.
# No desenho de 3 anotadores (2026-07-29), a paralelização é feita por
# pessoas cuja concordância já foi medida na etapa de medição (mesmo pool,
# todos anotam) — o julgamento individual delas ali é confiável por
# construção, diferente de watch/near-miss, que são diagnósticos e nunca
# tiveram checagem cruzada em nenhum desenho.
TRUSTED_SINGLE_ANNOTATOR_STRATA = {"main_paralelizacao"}


def resolve_final_labels(annotations: pd.DataFrame, tiebreak_ids: set[str]) -> pd.DataFrame:
    """Um rótulo final por item_id: prioriza o 3º anotador (desempate) se
    presente; senão exige consenso UNÂNIME dos anotadores primários (2 no
    desenho antigo, até 3 na etapa de medição do desenho novo); sem consenso
    e sem desempate -> 'unresolved' (excluído da precisão, mas contado).

    `category_confirmed` é opcional: existe no desenho antigo (categoria
    A/B/C como tarefa de anotação), não existe mais a partir da reunião de
    2026-07-29 (categoria deixou de ser dimensão analítica validada, Seção 2
    do plano) — o código funciona nos dois formatos de CSV de anotação.

    `n_primary_annotators` registra quantos anotadores primários rotularam
    o item — usado depois para separar itens com checagem cruzada real
    (>=2) de itens só single-anotados, que só entram nas tabelas de precisão
    quando vêm de um estrato em `TRUSTED_SINGLE_ANNOTATOR_STRATA`."""
    has_category = "category_confirmed" in annotations.columns
    rows = []
    for item_id, group in annotations.groupby("item_id"):
        tb = group[group["annotator_id"].isin(tiebreak_ids)]
        primary = group[~group["annotator_id"].isin(tiebreak_ids)]
        n_primary = primary["annotator_id"].nunique()
        if not tb.empty:
            r = tb.iloc[0]
            rows.append({"item_id": item_id, "is_ubw": r["is_ubw"],
                         "category_confirmed": r["category_confirmed"] if has_category else None,
                         "resolution": "desempate", "n_primary_annotators": n_primary})
            continue
        is_ubw_vals = primary["is_ubw"].astype(str).unique()
        if len(is_ubw_vals) == 1:
            r = primary.iloc[0]
            if has_category:
                cat_vals = primary["category_confirmed"].unique()
                cat = r["category_confirmed"] if len(cat_vals) == 1 else "divergente_sem_desempate"
            else:
                cat = None
            resolution = "consenso" if n_primary >= 2 else "single_anotador"
            rows.append({"item_id": item_id, "is_ubw": r["is_ubw"], "category_confirmed": cat,
                         "resolution": resolution, "n_primary_annotators": n_primary})
        else:
            rows.append({"item_id": item_id, "is_ubw": None, "category_confirmed": None,
                         "resolution": "unresolved", "n_primary_annotators": n_primary})
    return pd.DataFrame(rows)


def precision_table(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    is_single = df["resolution"] == "single_anotador"
    trusted = df.get("sample_stratum", pd.Series(index=df.index, dtype=object)).isin(TRUSTED_SINGLE_ANNOTATOR_STRATA)
    untrusted_single = is_single & ~trusted
    if untrusted_single.any():
        logger.warning(
            "%d item(ns) com só 1 anotador primário, de estrato diagnóstico (watch/near-miss) "
            "EXCLUÍDO(S) das tabelas de precisão por '%s' — não têm checagem cruzada nem vêm de "
            "estrato validado por medição.", int(untrusted_single.sum()), group_col,
        )
    df = df[~(df["resolution"] == "unresolved") & ~untrusted_single].copy()
    df["is_ubw_bool"] = df["is_ubw"].astype(str).map({"True": True, "False": False, "true": True, "false": False})
    rows = []
    for key, group in df.groupby(group_col, dropna=False):
        n = len(group)
        tp = int(group["is_ubw_bool"].sum())
        p_hat, lo, hi = wilson_ci(tp, n)
        rows.append({group_col: key, "n": n, "true_positives": tp, "precision": round(p_hat, 4),
                     "wilson_ci_low": round(lo, 4), "wilson_ci_high": round(hi, 4)})
    table = pd.DataFrame(rows).sort_values("precision", na_position="last")
    below = table[table["precision"] < ACCEPTABLE_PRECISION_FLOOR]
    for _, r in below.iterrows():
        logger.warning(
            "%s='%s': precisão %.2f (IC 95%% Wilson [%.2f, %.2f]) abaixo do piso de %.2f. "
            "INSUMO PARA O ORIENTADOR (léxico congelado — Seção 7.5 do guideline; "
            "o agente NÃO altera o léxico).",
            group_col, r[group_col], r["precision"], r["wilson_ci_low"], r["wilson_ci_high"],
            ACCEPTABLE_PRECISION_FLOOR,
        )
    return table


def reweighted_global_precision(
    resolved: pd.DataFrame, joined: pd.DataFrame, weights: pd.DataFrame,
    representative_strata: tuple[str, ...] = ("main", "census_c", "main_medicao", "main_paralelizacao"),
) -> dict:
    """p_hat_global = sum_h w_h * p_hat_h, restrito aos estratos
    REPRESENTATIVOS — watch e near_miss são diagnósticos, não entram no
    denominador populacional (insumo do Agente A, P6).

    `stratum_key` casa com o formato de `weights["stratum"]`: no desenho
    antigo (com censo de Categoria C) é "categoria|artefato" ou "C|censo";
    a partir de 2026-07-29, sem categoria como dimensão analítica, os pesos
    em `sampling_weights_*.csv` são só o nome do tipo de artefato, então
    `stratum_key` é só o artefato quando a coluna `category_ubw` está
    ausente do arquivo de pesos (detectado automaticamente pelo formato de
    `weights["stratum"]`, sem precisar de outro parâmetro)."""
    df = resolved.merge(
        joined[["item_id", "category_ubw", "artifact_type", "sample_stratum"]].drop_duplicates("item_id"),
        on="item_id", how="left",
    )
    df = df[df["sample_stratum"].isin(representative_strata)]
    is_single = df["resolution"] == "single_anotador"
    untrusted_single = is_single & ~df["sample_stratum"].isin(TRUSTED_SINGLE_ANNOTATOR_STRATA)
    df = df[~(df["resolution"] == "unresolved") & ~untrusted_single].copy()
    df["is_ubw_bool"] = df["is_ubw"].astype(str).map({"True": True, "False": False, "true": True, "false": False})

    weights_by_artifact_only = not weights["stratum"].astype(str).str.contains(r"\|").any()
    if weights_by_artifact_only:
        df["stratum_key"] = df["artifact_type"]
    else:
        df["stratum_key"] = df.apply(
            lambda r: "C|censo" if r["sample_stratum"] == "census_c" else f"{r['category_ubw']}|{r['artifact_type']}",
            axis=1,
        )

    global_p = 0.0
    total_weight_used = 0.0
    detail = []
    for _, w in weights.iterrows():
        stratum = w["stratum"]
        sub = df[df["stratum_key"] == stratum]
        if sub.empty:
            logger.warning("Estrato '%s' sem itens anotados resolvidos — contribuição nula na reponderação.", stratum)
            continue
        p_h = sub["is_ubw_bool"].mean()
        global_p += w["weight"] * p_h
        total_weight_used += w["weight"]
        detail.append({"stratum": stratum, "weight": w["weight"], "n_annotated": len(sub), "precision": round(p_h, 4)})

    if total_weight_used < 0.999:
        logger.warning(
            "Só %.1f%% do peso populacional teve itens anotados; a precisão global reponderada "
            "abaixo é uma aproximação (estratos sem cobertura ficaram de fora do somatório).",
            total_weight_used * 100,
        )
    return {"global_precision_reweighted": round(global_p, 4), "total_weight_covered": round(total_weight_used, 4),
            "detail": detail}


def specificity_near_miss(resolved: pd.DataFrame, joined: pd.DataFrame) -> pd.DataFrame:
    """Especificidade: proporção de itens do pool near-miss adversarial que
    o(s) anotador(es) corretamente rejeitaram (is_ubw=False), por
    heurística que os selecionou. Mede se o pipeline (humano + léxico)
    rejeita o que deveria rejeitar — não é a mesma coisa que precisão."""
    df = resolved.merge(
        joined[["item_id", "sample_stratum", "near_miss_flags"]].drop_duplicates("item_id"),
        on="item_id", how="left",
    )
    df = df[(df["sample_stratum"] == "near_miss") & (df["resolution"] != "unresolved")].copy()
    if df.empty:
        return pd.DataFrame(columns=["heuristic", "n", "n_corretamente_rejeitado", "especificidade"])
    df["is_ubw_bool"] = df["is_ubw"].astype(str).map({"True": True, "False": False, "true": True, "false": False})
    rows = []
    exploded = df.assign(heuristic=df["near_miss_flags"].fillna("").str.split(";")).explode("heuristic")
    exploded = exploded[exploded["heuristic"] != ""]
    for h, group in exploded.groupby("heuristic"):
        n = len(group)
        rejected = int((~group["is_ubw_bool"]).sum())
        rows.append({"heuristic": h, "n": n, "n_corretamente_rejeitado": rejected,
                     "especificidade": round(rejected / n, 4) if n else float("nan")})
    overall_n = len(df)
    overall_rejected = int((~df["is_ubw_bool"]).sum())
    rows.append({"heuristic": "TODOS (pool near-miss)", "n": overall_n, "n_corretamente_rejeitado": overall_rejected,
                 "especificidade": round(overall_rejected / overall_n, 4) if overall_n else float("nan")})
    return pd.DataFrame(rows)


def cmd_report(args: argparse.Namespace) -> None:
    annotations = pd.read_csv(args.annotations, low_memory=False)
    if "sample_stratum" not in annotations.columns:
        raise SystemExit(
            "Coluna 'sample_stratum' ausente. Junte o _internal_stratum_map_*.csv "
            "(gerado por 03c_generate_batches.py) pelo item_id antes de rodar este relatório."
        )
    annotations = annotations[annotations["sample_stratum"] != "calibration"].copy()
    if annotations["is_ubw"].dtype == object:
        annotations["is_ubw"] = annotations["is_ubw"].map(
            {"True": True, "False": False, "true": True, "false": False, True: True, False: False}
        )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tiebreak_ids = set(args.tiebreak_annotators.split(",")) if args.tiebreak_annotators else set()

    # 1) kappa/AC1 — reusa 03 sem alterar; item_col = item_id (chave estável).
    #
    # CRÍTICO: nunca rodar agreement_report() numa única chamada sobre TODAS
    # as pools juntas quando pools diferentes têm duplas de anotadores
    # diferentes (ex.: A1+A2 no principal, A3+A4 no censo C). m03._pivot_pair
    # faz dropna nas colunas dos 2 primeiros annotator_id (ordem alfabética) —
    # se passássemos tudo junto, ele pegaria só A1/A2 e descartaria em
    # silêncio todo item do censo C (nunca visto por A1/A2), zerando
    # justamente a concordância da categoria mais sensível a falso positivo
    # sem erro nem aviso. Por isso: agrupa por sample_stratum (cada stratum
    # tem sua própria dupla fixa) e roda agreement_report() uma vez por
    # grupo, nunca misturado.
    kappa_input = annotations.rename(columns={"item_id": "artifact_id"})
    has_category = "category_confirmed" in kappa_input.columns
    if not has_category:
        # m03.agreement_report (script 03, não alterado) exige a coluna por
        # contrato. A partir de 2026-07-29 categoria não é mais tarefa de
        # anotação, então preenchemos um placeholder só para não quebrar a
        # chamada, e descartamos a métrica "category_confirmed (TP)" do
        # relatório final logo abaixo — ela não significa nada aqui.
        kappa_input = kappa_input.copy()
        kappa_input["category_confirmed"] = ""
        logger.info("CSV de anotação sem 'category_confirmed' (desenho pós-2026-07-29): "
                     "métrica de concordância de categoria não será reportada.")
    agreement_frames = []
    for stratum, group in kappa_input.groupby("sample_stratum"):
        n_annotators = group["annotator_id"].nunique()
        # Não basta ter >=2 anotadores DIFERENTES no estrato — precisa de
        # pelo menos um item anotado por 2+ pessoas ao mesmo tempo. Estratos
        # de cobertura individual (paralelização, watch, near-miss) têm
        # vários anotadores no total, mas nenhuma sobreposição por item; sem
        # essa checagem, m03.agreement_report quebra (tenta pivotar uma
        # dupla que nunca viu o mesmo item, sem tratamento de coluna
        # ausente — não alteramos o script 03 para corrigir isso ali).
        max_overlap = group.groupby("artifact_id")["annotator_id"].nunique().max() if n_annotators >= 2 else 0
        if n_annotators < 2 or max_overlap < 2:
            logger.warning(
                "Estrato '%s': %d anotador(es), mas nenhum item com 2+ rótulos independentes "
                "— sem par para calcular kappa/AC1 ali (esperado em pool de cobertura "
                "individual, ex.: paralelização, watch, near-miss).",
                stratum, n_annotators,
            )
            continue
        rep = m03.agreement_report(group, item_col="artifact_id")
        rep.insert(0, "sample_stratum", stratum)
        agreement_frames.append(rep)
    agreement = pd.concat(agreement_frames, ignore_index=True) if agreement_frames else pd.DataFrame()
    if not has_category and not agreement.empty:
        agreement = agreement[agreement["task"] != "category_confirmed (TP)"].copy()
    agreement.to_csv(out_dir / "agreement_report.csv", index=False)

    cat_geral = agreement[(agreement.get("task") == "category_confirmed (TP)") & (agreement.get("scope") == "geral")] \
        if not agreement.empty else agreement
    for _, r in cat_geral.iterrows():
        if pd.notna(r["kappa"]) and r["kappa"] < m03.LANDIS_KOCH_MIN_ACCEPTABLE_KAPPA:
            logger.warning(
                "Estrato '%s': kappa de category_confirmed = %.2f, abaixo de %.2f. "
                "Isso NUNCA fica escondido atrás de um agregado — cada estrato com dupla "
                "própria tem seu próprio número (Seção 5.5 do guideline).",
                r["sample_stratum"], r["kappa"], m03.LANDIS_KOCH_MIN_ACCEPTABLE_KAPPA,
            )

    # 2) rótulo final por item (consenso ou desempate).
    resolved = resolve_final_labels(annotations, tiebreak_ids)
    n_unresolved = (resolved["resolution"] == "unresolved").sum()
    if n_unresolved:
        logger.warning(
            "%d itens ficaram 'unresolved' (divergência sem 3º anotador) — excluídos da "
            "precisão, reportados separadamente.", n_unresolved,
        )
    resolved.to_csv(out_dir / "resolved_labels.csv", index=False)

    joined = resolved.merge(
        annotations[["item_id", "matched_expression", "category_ubw", "artifact_type", "sample_stratum"] +
                    (["near_miss_flags"] if "near_miss_flags" in annotations.columns else [])].drop_duplicates("item_id"),
        on="item_id", how="left",
    )

    # 3) precisão por expressão / categoria / artefato, com Wilson CI.
    precision_table(joined, "matched_expression").to_csv(out_dir / "precision_by_expression.csv", index=False)
    precision_table(joined, "category_ubw").to_csv(out_dir / "precision_by_category.csv", index=False)
    precision_table(joined, "artifact_type").to_csv(out_dir / "precision_by_artifact_type.csv", index=False)

    # 4) precisão global reponderada.
    if args.weights:
        weights = pd.read_csv(args.weights)
        global_report = reweighted_global_precision(resolved, joined, weights)
        pd.DataFrame(global_report["detail"]).to_csv(out_dir / "precision_global_detail.csv", index=False)
        logger.info("Precisão global reponderada: %.4f (cobertura de peso: %.1f%%)",
                     global_report["global_precision_reweighted"], global_report["total_weight_covered"] * 100)
        with (out_dir / "precision_global_summary.txt").open("w") as f:
            f.write(f"precisao_global_reponderada={global_report['global_precision_reweighted']}\n")
            f.write(f"cobertura_de_peso={global_report['total_weight_covered']}\n")
    else:
        logger.warning("--weights não informado; pulando precisão global reponderada.")

    # 5) especificidade sobre near-miss adversarial.
    spec = specificity_near_miss(resolved, joined)
    spec.to_csv(out_dir / "specificity_near_miss.csv", index=False)

    logger.info("Relatório de precisão completo salvo em %s", out_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("report", help="Gera o relatório completo de precisão pós-anotação.")
    p.add_argument("--annotations", required=True,
                    help="CSV longo: item_id, artifact_type, matched_expression, category_ubw, "
                         "annotator_id, is_ubw, category_confirmed, confidence, sample_stratum.")
    p.add_argument("--weights", default=None, help="sampling_weights_*.csv de 03b_final_sampling.py.")
    p.add_argument("--tiebreak-annotators", default="A3", help="IDs (separados por vírgula) do(s) 3º anotador(es).")
    p.add_argument("--out-dir", required=True)
    p.set_defaults(func=cmd_report)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
