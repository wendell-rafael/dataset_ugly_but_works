#!/usr/bin/env python3
"""Consolida a anotacao humana da amostra de code_comment.

Le os tres CSV brutos exportados pela UI de anotacao, confere integridade,
calcula concordancia (par a par e entre os tres), monta o gold por maioria e
estima a precisao do lexico com intervalo de Wilson.

A amostra e autoponderada (aleatoria simples dentro do estrato code_comment),
entao a precisao global e a proporcao simples de positivos -- sem pesos. A
analise por expressao NAO e sustentada por esse desenho: a cauda do lexico sai
com zero ou poucos itens. Ver validation/sample_code_comment/manifest.json.

Uso:
    python3 scripts/13_merge_code_comment.py
"""

from __future__ import annotations

import itertools
import json
import sys
from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
BASE = RAIZ / "validation" / "sample_code_comment"
BRUTOS = BASE / "anotacoes" / "brutos"
SAIDA = BASE / "analise"
AMOSTRA = BASE / "amostra_code_comment.csv"

ANOTADORES = ("Wendell", "Bruno", "Miguel")

# Itens em que o CSV do Bruno mudou entre o envio de 04/09 e o de 07/09.
# Os tres viraram True -> False, todos na direcao do consenso dos outros dois.
# A proveniencia dessa correcao esta registrada em anotacoes/PROVENIENCIA.md e
# ainda NAO foi confirmada; enquanto isso o script reporta os dois cenarios.
AJUSTE_BRUNO = {"cc0002": True, "cc0020": True, "cc0049": True}


def wilson(sucessos: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de Wilson (score) para uma proporcao binomial.

    Preferido ao Wald porque nao estoura os limites [0,1] nem colapsa quando a
    proporcao se aproxima de 1 -- exatamente o nosso caso (p ~ 0,92).
    """
    p = sucessos / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    meio = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, centro - meio), min(1.0, centro + meio)


def carrega() -> tuple[pd.DataFrame, list[str]]:
    """Devolve (votos, ids) com uma coluna booleana por anotador."""
    amostra = pd.read_csv(AMOSTRA)
    esperados = set(amostra["item_id"])

    quadros = {}
    problemas: list[str] = []
    for nome in ANOTADORES:
        caminho = BRUTOS / f"anotacao_code_comment_{nome}.csv"
        if not caminho.exists():
            problemas.append(f"{nome}: arquivo ausente em {caminho}")
            continue
        df = pd.read_csv(caminho, encoding="utf-8-sig")

        faltam = esperados - set(df["item_id"])
        sobram = set(df["item_id"]) - esperados
        if faltam:
            problemas.append(f"{nome}: {len(faltam)} itens da amostra sem voto")
        if sobram:
            problemas.append(f"{nome}: {len(sobram)} itens fora da amostra")
        if df["item_id"].duplicated().any():
            problemas.append(f"{nome}: item_id duplicado")
        if df["is_ubw"].isna().any():
            problemas.append(f"{nome}: is_ubw vazio")
        vazias = df["observacao"].fillna("").astype(str).str.strip().eq("").sum()
        if vazias:
            problemas.append(f"{nome}: {vazias} observacoes vazias")
        quadros[nome] = df.set_index("item_id")

    if problemas:
        for p in problemas:
            print(f"ERRO  {p}", file=sys.stderr)
        sys.exit(1)

    ids = sorted(esperados)
    votos = pd.DataFrame(index=pd.Index(ids, name="item_id"))
    votos["matched_expression"] = quadros[ANOTADORES[0]].loc[ids, "matched_expression"]
    votos["repo_full_name"] = quadros[ANOTADORES[0]].loc[ids, "repo_full_name"]
    votos["url"] = quadros[ANOTADORES[0]].loc[ids, "url"]
    for nome in ANOTADORES:
        votos[f"voto__{nome}"] = quadros[nome].loc[ids, "is_ubw"].astype(bool)
        votos[f"conf__{nome}"] = quadros[nome].loc[ids, "confidence"]
        votos[f"obs__{nome}"] = quadros[nome].loc[ids, "observacao"]
    return votos, ids


def par(x: np.ndarray, y: np.ndarray) -> dict:
    """Concordancia de um par: bruta, Cohen's kappa e AC1 de Gwet.

    O AC1 entra ao lado do kappa porque a prevalencia aqui e ~92% de positivos.
    Nessa faixa a concordancia esperada por acaso do kappa fica em torno de 0,85
    e sobra pouca escala para ele crescer -- o paradoxo descrito em
    Feinstein & Cicchetti (1990). O AC1 nao usa as marginais observadas para
    estimar o acaso, entao nao sofre do mesmo efeito.
    """
    n = len(x)
    a = int((x & y).sum())       # ambos True
    b = int((x & ~y).sum())      # so o primeiro
    c = int((~x & y).sum())      # so o segundo
    d = int((~x & ~y).sum())     # ambos False

    po = (a + d) / n
    pe = ((a + b) / n) * ((a + c) / n) + ((c + d) / n) * ((b + d) / n)
    kappa = (po - pe) / (1 - pe) if pe < 1 else float("nan")

    pi = (((a + b) / n) + ((a + c) / n)) / 2
    pe_ac1 = 2 * pi * (1 - pi)
    ac1 = (po - pe_ac1) / (1 - pe_ac1) if pe_ac1 < 1 else float("nan")

    return {
        "n": n, "ambos_ubw": a, "so_primeiro": b, "so_segundo": c,
        "ambos_nao": d, "divergencias": b + c,
        "concordancia_bruta": po, "pe_cohen": pe,
        "kappa_cohen": kappa, "ac1_gwet": ac1,
    }


def fleiss(matriz: np.ndarray) -> dict:
    """Fleiss' kappa e AC1 multi-avaliador para k anotadores e 2 categorias."""
    n, k = matriz.shape
    contagens = np.stack([matriz.sum(1), k - matriz.sum(1)], axis=1)
    p_item = ((contagens**2).sum(1) - k) / (k * (k - 1))
    p_barra = p_item.mean()
    p_cat = contagens.sum(0) / (n * k)
    pe = (p_cat**2).sum()
    pe_ac1 = 2 * p_cat[0] * (1 - p_cat[0])
    return {
        "n": n, "anotadores": k,
        "concordancia_media": p_barra,
        "pe_fleiss": pe,
        "kappa_fleiss": (p_barra - pe) / (1 - pe),
        "ac1_gwet": (p_barra - pe_ac1) / (1 - pe_ac1),
    }


def cenario(votos: pd.DataFrame, rotulo: str) -> tuple[pd.DataFrame, dict, dict]:
    colunas = [f"voto__{nome}" for nome in ANOTADORES]
    matriz = votos[colunas].to_numpy(dtype=int)

    linhas = []
    for x, y in itertools.combinations(ANOTADORES, 2):
        m = par(votos[f"voto__{x}"].to_numpy(), votos[f"voto__{y}"].to_numpy())
        linhas.append({"cenario": rotulo, "anotador_a": x, "anotador_b": y, **m})
    pares = pd.DataFrame(linhas)

    tres = {"cenario": rotulo, **fleiss(matriz)}

    n_true = matriz.sum(1)
    gold = n_true >= 2
    lo, hi = wilson(int(gold.sum()), len(gold))
    precisao = {
        "cenario": rotulo,
        "n": int(len(gold)),
        "positivos_gold": int(gold.sum()),
        "negativos_gold": int((~gold).sum()),
        "precisao": float(gold.mean()),
        "ic95_wilson_inf": lo,
        "ic95_wilson_sup": hi,
        "unanimes": int(((n_true == 0) | (n_true == 3)).sum()),
        "nao_unanimes": int(((n_true > 0) & (n_true < 3)).sum()),
    }
    return pares, tres, precisao


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    votos, ids = carrega()
    n = len(ids)
    print(f"integridade OK: {n} itens x {len(ANOTADORES)} anotadores\n")

    # --- cenario oficial (arquivos como recebidos) -----------------------
    pares, tres, precisao = cenario(votos, "recebido")

    # --- contrafactual: Bruno antes do ajuste de 07/09 -------------------
    antes = votos.copy()
    for item, valor in AJUSTE_BRUNO.items():
        antes.loc[item, "voto__Bruno"] = valor
    pares_a, tres_a, precisao_a = cenario(antes, "pre_ajuste_bruno")

    n_true = votos[[f"voto__{x}" for x in ANOTADORES]].to_numpy(dtype=int).sum(1)
    votos["n_ubw"] = n_true
    votos["gold_is_ubw"] = n_true >= 2
    votos["unanime"] = (n_true == 0) | (n_true == len(ANOTADORES))

    todos_pares = pd.concat([pares, pares_a], ignore_index=True)
    todos_tres = pd.DataFrame([tres, tres_a])
    todas_prec = pd.DataFrame([precisao, precisao_a])

    print("CONCORDANCIA PAR A PAR")
    for _, r in todos_pares.iterrows():
        print(f"  [{r.cenario:17s}] {r.anotador_a:8s} x {r.anotador_b:8s}  "
              f"bruta={r.concordancia_bruta:.4f}  kappa={r.kappa_cohen:.4f}  "
              f"AC1={r.ac1_gwet:.4f}  div={int(r.divergencias)}")
    print("\nENTRE OS TRES")
    for _, r in todos_tres.iterrows():
        print(f"  [{r.cenario:17s}] Fleiss kappa={r.kappa_fleiss:.4f}  "
              f"AC1={r.ac1_gwet:.4f}  bruta={r.concordancia_media:.4f}")
    print("\nPRECISAO DO LEXICO (gold por maioria)")
    for _, r in todas_prec.iterrows():
        print(f"  [{r.cenario:17s}] {r.precisao:.4f} "
              f"({int(r.positivos_gold)}/{int(r.n)})  "
              f"IC95 [{r.ic95_wilson_inf:.4f}, {r.ic95_wilson_sup:.4f}]  "
              f"unanimes={int(r.unanimes)}")

    print("\nPRECISAO POR ANOTADOR")
    linhas_ind = []
    for nome in ANOTADORES:
        s = int(votos[f"voto__{nome}"].sum())
        lo, hi = wilson(s, n)
        linhas_ind.append({"anotador": nome, "n": n, "positivos": s,
                           "precisao": s / n, "ic95_inf": lo, "ic95_sup": hi})
        print(f"  {nome:8s} {s/n:.4f} ({s}/{n})  IC95 [{lo:.4f}, {hi:.4f}]")

    nao_unan = votos.loc[~votos["unanime"]]
    print(f"\nNAO-UNANIMES: {len(nao_unan)}")
    print(nao_unan["matched_expression"].value_counts().to_string())

    todos_pares.to_csv(SAIDA / "concordancia_pares.csv", index=False)
    todos_tres.to_csv(SAIDA / "concordancia_tres.csv", index=False)
    todas_prec.to_csv(SAIDA / "precisao_lexico.csv", index=False)
    pd.DataFrame(linhas_ind).to_csv(SAIDA / "precisao_por_anotador.csv", index=False)
    votos.to_csv(SAIDA / "gold_code_comment_269.csv")
    nao_unan.to_csv(SAIDA / "nao_unanimes.csv")

    resumo = {
        "n_itens": n,
        "anotadores": list(ANOTADORES),
        "cenario_oficial": None,  # nenhum eleito enquanto a proveniencia estiver aberta
        "kappa_fleiss_recebido": tres["kappa_fleiss"],
        "kappa_fleiss_pre_ajuste": tres_a["kappa_fleiss"],
        "ac1_recebido": tres["ac1_gwet"],
        "precisao_lexico": precisao["precisao"],
        "ic95_wilson": [precisao["ic95_wilson_inf"], precisao["ic95_wilson_sup"]],
        "precisao_independe_do_ajuste": precisao["precisao"] == precisao_a["precisao"],
        "ajuste_bruno_itens": sorted(AJUSTE_BRUNO),
        "proveniencia_do_ajuste": "NAO CONFIRMADA -- ver anotacoes/PROVENIENCIA.md",
    }
    (SAIDA / "resumo.json").write_text(
        json.dumps(resumo, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nsaida em {SAIDA.relative_to(RAIZ)}/")


if __name__ == "__main__":
    main()
