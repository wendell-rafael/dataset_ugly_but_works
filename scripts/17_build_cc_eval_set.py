#!/usr/bin/env python3
"""Monta o pool de exemplos e o conjunto de avaliação do escopo `code_comment`.

Duas saídas, ambas versionadas:

1. `validation/panel/cc/exemplar_pool.json` — os 8 exemplos do few-shot fixo
   (4 positivos, 4 negativos), com `body_text` MASCARADO, a observação original
   do anotador em português e a tradução para o inglês que vai no prompt.
2. `validation/panel/cc/human_gold_379.csv` — o gabarito humano completo usado
   para estimar a precisão do dataset.
3. `validation/panel/cc/eval_371.csv` — o conjunto de avaliação das LLMs: os
   379 comentários de código MENOS os 8 usados como exemplo.

## Por que os exemplos saem da avaliação

Item usado como exemplo no prompt não pode ser avaliado pelo mesmo prompt — a
medida ficaria otimista por construção. Por isso 379 viram 371. O custo é pago
em negativos, que são o recurso escasso do experimento: o pool leva 4 de 22 e
deixa 18 na avaliação.

Positivos são abundantes (242 unânimes) e sair 4 não muda nada.

## Como os 8 foram escolhidos

Só de itens **unânimes** entre os três anotadores — item em que os humanos
divergiram é ambíguo, e ambiguidade em exemplo ensina a regra errada.

Os 4 negativos cobrem **um padrão cada**, dos quatro que emergiram das 16
observações de negativos unânimes. Com apenas 4 exemplos não há como
representar a frequência real dos padrões, então cobrir a variedade rende mais
que repetir o mais comum ("nenhuma admissão", 6 dos 16 casos). Cada escolha usa
um caso em que **os três anotadores deram o mesmo motivo**, não só o mesmo
rótulo — o motivo é o que vira o campo `Why` do exemplo.

Os 4 positivos variam a expressão-gatilho de propósito e foram escolhidos entre
os `body_text` mais curtos da sua expressão: exemplo curto custa menos token e
é pago 26.036 vezes na aplicação ao corpus.

## Sobre as traduções

`obs_pt` é o texto literal do anotador. `rationale_en` é **minha tradução**,
não dado humano. Os dois ficam no JSON para a tradução ser auditável contra o
original. O rótulo (`label`) é dos anotadores, sempre.

Uso:
    python3 scripts/17_build_cc_eval_set.py
    python3 scripts/17_build_cc_eval_set.py --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
GOLD_269 = RAIZ / "validation/sample_code_comment/analise/gold_code_comment_269.csv"
AMOSTRA = RAIZ / "validation/sample_code_comment/amostra_code_comment.csv"
GOLD_385 = RAIZ / "validation/panel/gold_test_385.csv"
SAIDA = RAIZ / "validation/panel/cc"

# Os 8 exemplos. `padrao` só existe nos negativos e nomeia qual das quatro
# situações da Seção NOT-UBW do prompt o caso ilustra.
#
# `fonte_obs` registra de qual anotador saiu o texto usado como base da
# tradução, nos casos em que os três escreveram redações diferentes para o
# mesmo motivo.
EXEMPLOS: tuple[dict, ...] = (
    # ---- negativos: um por padrão -------------------------------------
    {
        "item_id": "cc0106",
        "label": "NOT-UBW",
        "padrao": "points elsewhere",
        "fonte_obs": "Bruno",
        "rationale_en": (
            "The phrase describes an earlier implementation written by other "
            "people, which the present code avoids — not a substandard "
            "solution adopted here."
        ),
    },
    {
        "item_id": "cc0256",
        "label": "NOT-UBW",
        "padrao": "not adopted",
        "fonte_obs": "Bruno",
        "rationale_en": (
            "The comment raises a possible ugly hack and then explicitly "
            "decides against using it, so nothing substandard was kept."
        ),
    },
    {
        "item_id": "cc0269",
        "label": "NOT-UBW",
        "padrao": "identifier only",
        "fonte_obs": "Wendell",
        "rationale_en": (
            "The phrase is part of the name and description of a class and its "
            "test, not an admission about the code shown."
        ),
    },
    # O padrão "no admission" é, na prática, a assinatura do truncamento da
    # janela: em 6 dos 16 negativos unânimes a expressão não aparece no
    # `body_text` porque a linha do match ficou fora dos 2.000 caracteres (ver
    # panel_prompts_cc.py). Por decisão de 07/09/2026 esses casos são
    # negativos, então o padrão é regra legítima de julgamento e este exemplo
    # é o arquétipo dela — o juiz precisa aprender a responder NOT-UBW, não
    # `uncertain`, quando o trecho não traz admissão nenhuma.
    {
        "item_id": "cc0002",
        "label": "NOT-UBW",
        "padrao": "no admission",
        "fonte_obs": "Wendell",
        "rationale_en": (
            "Nothing in this snippet states that the code shown is a poorly "
            "built solution, so there is no admission to judge."
        ),
    },
    # ---- positivos: expressões variadas, corpos curtos ------------------
    {
        "item_id": "cc0008",
        "label": "UBW-TRUE",
        "fonte_obs": "Wendell",
        "rationale_en": (
            "The author grants the solution is not pretty but works, and says "
            "a proper fix would take more effort — kept anyway."
        ),
    },
    {
        "item_id": "cc0037",
        "label": "UBW-TRUE",
        "fonte_obs": "Wendell",
        "rationale_en": (
            "The phrase labels the code immediately below as an improvised "
            "solution, which is what makes it UBW."
        ),
    },
    {
        "item_id": "cc0099",
        "label": "UBW-TRUE",
        "fonte_obs": "Wendell",
        "rationale_en": (
            "The comment admits a stopgap kept in place until a known bug is "
            "fixed elsewhere."
        ),
    },
    {
        "item_id": "cc0244",
        "label": "UBW-TRUE",
        "fonte_obs": "Wendell",
        "rationale_en": (
            "The comment presents the code as a temporary fix; the author did "
            "not implement the proper solution and left this one running."
        ),
    },
)

# Reservas, caso um dos escolhidos se mostre ruim na primeira leitura de
# resultado. Trocar exemplo depois de ver resultado é ajuste na luz do
# desfecho: se acontecer, declarar e devolver o substituído à avaliação.
RESERVAS = {
    "points elsewhere": ["cc0053", "cc0035", "cc0085"],
    "not adopted": ["cc0194", "cc0049", "cc0091"],
    "no admission": ["cc0148", "cc0172", "cc0213"],
}


def carrega_mascarador():
    caminho = RAIZ / "scripts" / "06_export_publishable.py"
    spec = importlib.util.spec_from_file_location("export_publishable", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.apply_pii_masking


def sha256_texto(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    mascarar = carrega_mascarador()

    gold = pd.read_csv(GOLD_269)
    amostra = pd.read_csv(AMOSTRA, low_memory=False)
    # Só `body_text` vem da amostra: `url` e `repo_full_name` já estão no gold
    # (vieram dos CSV dos anotadores) e trazê-los de novo geraria url_x/url_y.
    novos = gold.merge(
        amostra[["item_id", "body_text"]],
        on="item_id", how="left", validate="one_to_one",
    )
    if novos.body_text.isna().any():
        raise SystemExit("body_text ausente após o merge com a amostra")

    ids_exemplo = [e["item_id"] for e in EXEMPLOS]
    if len(set(ids_exemplo)) != len(ids_exemplo):
        raise SystemExit("item_id repetido em EXEMPLOS")

    # --- pool de exemplos ------------------------------------------------
    pool, mascaras_total = [], {}
    for e in EXEMPLOS:
        linha = novos.loc[novos.item_id == e["item_id"]]
        if len(linha) != 1:
            raise SystemExit(f"{e['item_id']} não encontrado nos 269")
        r = linha.iloc[0]

        rotulo_humano = "UBW-TRUE" if bool(r.gold_is_ubw) else "NOT-UBW"
        if rotulo_humano != e["label"]:
            raise SystemExit(
                f"{e['item_id']}: label {e['label']} contradiz o gabarito "
                f"humano ({rotulo_humano})"
            )
        if not bool(r.unanime):
            raise SystemExit(f"{e['item_id']} não é unânime")

        corpo, contas, _ = mascarar(str(r.body_text), mask_mentions=True)
        for k, v in contas.items():
            mascaras_total[k] = mascaras_total.get(k, 0) + v

        pool.append({
            "item_id": e["item_id"],
            "label": e["label"],
            "padrao": e.get("padrao"),
            "matched_expression": r.matched_expression,
            "repo_full_name": r.repo_full_name,
            "body_text": corpo,
            "body_chars": len(corpo),
            "rationale": e["rationale_en"],
            "obs_pt": str(r[f"obs__{e['fonte_obs']}"]).strip(),
            "fonte_obs": e["fonte_obs"],
            "votos": {a: bool(r[f"voto__{a}"]) for a in ("Wendell", "Bruno", "Miguel")},
        })

    t385 = pd.read_csv(GOLD_385, low_memory=False)
    col_gold = next(c for c in t385.columns if "gold" in c.lower())
    herdados = t385.loc[t385.artifact_type == "code_comment"].copy()
    herdados["origem"] = "teste_385"
    herdados["gold"] = herdados[col_gold].astype(bool)
    herdados["item_id"] = [f"h{i:04d}" for i in range(1, len(herdados) + 1)]

    # Voto individual de cada anotador, não só a maioria. O achado mais forte do
    # dev200 foi a assimetria por anotador (os 10 modelos concordavam menos com
    # Wendell), e sem estas colunas a análise não pode ser repetida aqui. As
    # duas fontes usam nomes diferentes -- `voto__` nos 269, `vote__` nos 385.
    for nome in ("Wendell", "Bruno", "Miguel"):
        novos[f"vote__{nome}"] = novos[f"voto__{nome}"].astype(bool)
        herdados[f"vote__{nome}"] = herdados[f"vote__{nome}"].astype(bool)

    campos = ["item_id", "origem", "repo_full_name", "matched_expression",
              "body_text", "url", "gold",
              "vote__Wendell", "vote__Bruno", "vote__Miguel"]

    # Gabarito humano completo. Ele sustenta a estimativa de precisão do
    # dataset. Os exemplos few-shot só precisam sair da avaliação automática.
    novos["origem"] = "amostra_269"
    novos["gold"] = novos.gold_is_ubw.astype(bool)
    human_gold = pd.concat([novos[campos], herdados[campos]], ignore_index=True)

    corpos_gold = []
    for t in human_gold.body_text.astype(str):
        c, _, _ = mascarar(t, mask_mentions=True)
        corpos_gold.append(c)
    human_gold["body_text"] = corpos_gold

    # --- conjunto de avaliação das LLMs: 379 menos os 8 ------------------
    restantes = novos.loc[~novos.item_id.isin(ids_exemplo)].copy()
    aval = pd.concat([restantes[campos], herdados[campos]], ignore_index=True)

    corpos, contas_aval = [], {}
    for t in aval.body_text.astype(str):
        c, contas, _ = mascarar(t, mask_mentions=True)
        corpos.append(c)
        for k, v in contas.items():
            contas_aval[k] = contas_aval.get(k, 0) + v
    aval["body_text"] = corpos

    n_pos, n_neg = int(aval.gold.sum()), int((~aval.gold).sum())
    print(f"pool de exemplos: {len(pool)} "
          f"({sum(1 for e in pool if e['label']=='UBW-TRUE')} pos / "
          f"{sum(1 for e in pool if e['label']=='NOT-UBW')} neg)")
    print(f"  máscaras no pool: {mascaras_total or 'nenhuma'}")
    print(f"  corpo mediano: {int(pd.Series([e['body_chars'] for e in pool]).median())} chars")
    print(f"\navaliação: {len(aval)} itens ({n_pos} pos / {n_neg} neg)")
    print(f"  por origem: {aval.origem.value_counts().to_dict()}")
    print(f"  negativos por origem: "
          f"{aval.loc[~aval.gold].origem.value_counts().to_dict()}")
    print(f"  máscaras na avaliação: {contas_aval or 'nenhuma'}")

    if args.dry_run:
        return 0

    SAIDA.mkdir(parents=True, exist_ok=True)
    manifesto = {
        "script": Path(__file__).name,
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
        "prompt": "scripts/panel_prompts_cc.py",
        "exemplos": len(pool),
        "exemplos_item_id": ids_exemplo,
        "reservas": RESERVAS,
        "avaliacao_n": len(aval),
        "avaliacao_positivos": n_pos,
        "avaliacao_negativos": n_neg,
        "mascaras_pool": mascaras_total,
        "mascaras_avaliacao": contas_aval,
        "sha256_pool": sha256_texto(json.dumps(pool, sort_keys=True, ensure_ascii=False)),
        "nota_traducao": (
            "rationale é tradução do autor deste script a partir de obs_pt; "
            "label e voto são dos anotadores humanos"
        ),
        "nota_vazamento": (
            "os 8 item_id do pool foram removidos da avaliação: 379 -> "
            f"{len(aval)}. Negativos caíram de 28 para {n_neg}."
        ),
        "human_gold_n": len(human_gold),
        "human_gold_positivos": int(human_gold.gold.sum()),
        "human_gold_negativos": int((~human_gold.gold).sum()),
        "nota_estimativa_dataset": (
            "human_gold_379.csv usa os 379 itens humanos. A retirada dos 8 "
            "exemplos se aplica somente a eval_371.csv, usado para avaliar LLMs."
        ),
        "nota_janela_truncada": (
            "8 dos 28 negativos do conjunto de 379 (29%) não exibem a "
            "expressão-gatilho no body_text: a janela de ±3 linhas é truncada "
            "em 2.000 caracteres depois de concatenada, e linha longa "
            "(arquivo minificado) estoura o orçamento antes da linha do "
            "match. No corpus são 571 de 26.036 (2,19%). Decisão de "
            "2026-09-07: tratar como negativo, sem recoleta. A precisão "
            "medida é do pipeline (léxico + janela), não do léxico isolado."
        ),
    }
    (SAIDA / "exemplar_pool.json").write_text(
        json.dumps(pool, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    human_gold.to_csv(SAIDA / "human_gold_379.csv", index=False)
    aval.to_csv(SAIDA / f"eval_{len(aval)}.csv", index=False)
    (SAIDA / "manifest.json").write_text(
        json.dumps(manifesto, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nsaída em {SAIDA.relative_to(RAIZ)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
