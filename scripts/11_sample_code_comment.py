#!/usr/bin/env python3
"""Amostra estratificada por expressão, restrita a comentários de código.

Desenho para o escopo reduzido do dataset (só `code_comment`), com a QP2
— precisão por expressão do léxico — mantida como entregável.

Por que estratificar em vez de sortear aleatoriamente: a distribuição das
expressões no estrato é muito assimétrica. Três expressões concentram 64% dos
26.036 comentários, e dez têm menos de 30 ocorrências no corpus inteiro. Uma
amostra aleatória de 379 itens traria ~98 de `this is a hack` e zero ou um item
da metade inferior do léxico — sem base para reportar precisão por expressão.

O desenho tem duas partes:

    censo    expressões com menos de MIN_CENSO ocorrências no corpus entram
             inteiras. São raras por natureza (`duct tape fix` tem 3 no corpus
             todo), e amostrar não faz sentido: o censo dá cobertura exata.
    amostra  as demais recebem alocação proporcional ao tamanho, com piso de
             PISO_ESTRATO itens, para que nenhuma expressão fique sem base.

**A amostra não é autoponderada.** Com piso e censo, expressões pequenas ficam
sobre-representadas em relação ao corpus. Qualquer estimativa GLOBAL de precisão
precisa reponderar pelos pesos gravados em `pesos_por_estrato.csv`; sem isso a
precisão global sai enviesada para o comportamento das expressões raras.

Itens já anotados na rodada multi-artefato são descontados da cota, não
re-sorteados.

Uso:
    python 11_sample_code_comment.py --out-dir ../validation/sample_code_comment
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "full_run" / "ubw_collected_consolidated.csv"
PANEL_DIR = ROOT / "validation" / "panel"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ubw.sample_cc")

ARTIFACT = "code_comment"
MIN_CENSO = 30       # abaixo disso, a expressão entra inteira
PISO_ESTRATO = 30    # mínimo de itens por expressão amostrada
ALVO_TOTAL = 379     # Cochran 95%/5%, p=0,50, corrigido para N=26.036
SEED = 42


def _chaves_de(nome: str) -> set[str]:
    """Chaves dos itens de um conjunto do painel, restritas ao artefato em escopo.

    Os `item_id` do painel são chave composta (`repo|tipo|artifact_id|expressão`),
    e o corpus tem `artifact_id` — a comparação usa a tripla que existe nos dois
    lados.
    """
    caminho = PANEL_DIR / f"{nome}.csv"
    if not caminho.exists():
        logger.warning("%s não encontrado", caminho)
        return set()
    df = pd.read_csv(caminho)
    df = df[df["artifact_type"] == ARTIFACT]
    chaves = set()
    for item_id in df["item_id"].astype(str):
        partes = item_id.split("|")
        if len(partes) >= 4:
            chaves.add("|".join(partes[:4]))
    return chaves


def carrega_ja_anotados() -> tuple[set[str], set[str]]:
    """Devolve (contam_para_o_alvo, apenas_excluir_do_sorteio).

    A distinção é metodológica, não de conveniência. Os itens do **conjunto de
    teste** já são validação: contam para o alvo de Cochran e não precisam ser
    reanotados. Os do **conjunto de calibração** foram usados para escolher
    prompt, modelo e regra de agregação do painel — estão queimados como medida
    independente. Eles são excluídos do sorteio (para ninguém reanotar item já
    visto) mas **não** contam para o alvo, senão a validação herdaria itens que
    influenciaram as decisões de método que ela deveria avaliar.
    """
    teste = _chaves_de("gold_test_385")
    calibracao = _chaves_de("gold_dev_200") - teste
    return teste, calibracao


def chave(row: pd.Series) -> str:
    return f"{row['repo_full_name']}|{row['artifact_type']}|{row['artifact_id']}|{row['matched_expression']}"


def amostra_simples(args: argparse.Namespace) -> None:
    """Amostragem aleatória simples do estrato, sem estratificar por expressão.

    Desenho adotado quando a análise por expressão do léxico sai de escopo. A
    vantagem sobre a versão estratificada não é só o tamanho: a amostra fica
    **autoponderada**, isto é, cada item representa a mesma fração do corpus, e a
    precisão global é a proporção simples de positivos — sem reponderação por
    estrato, que é onde é fácil errar na análise.

    Itens já anotados na rodada multi-artefato contam para o alvo e são
    descontados, não re-sorteados.
    """
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    corpus = pd.read_csv(CORPUS, low_memory=False)
    cc = corpus[corpus["artifact_type"] == ARTIFACT].copy()
    cc["_chave"] = cc.apply(chave, axis=1)

    teste, calibracao = carrega_ja_anotados()
    reaproveitaveis = int(cc["_chave"].isin(teste).sum())
    queimados = int(cc["_chave"].isin(calibracao).sum())
    logger.info("%d itens do conjunto de teste contam para o alvo; %d da calibração "
                "são excluídos do sorteio mas NÃO contam (foram usados para escolher "
                "prompt e modelo)", reaproveitaveis, queimados)
    disponivel = cc[~cc["_chave"].isin(teste | calibracao)]

    faltam = max(0, args.alvo - reaproveitaveis)
    n = min(faltam, len(disponivel))
    amostra = disponivel.sample(n=n, random_state=args.seed)
    amostra = amostra.drop(columns=["_chave"], errors="ignore").reset_index(drop=True)
    amostra.insert(0, "item_id", [f"cc{i + 1:04d}" for i in range(len(amostra))])
    amostra.to_csv(out / "amostra_code_comment.csv", index=False)

    manifest = {
        "artefato": ARTIFACT,
        "desenho": "aleatória simples (autoponderada)",
        "corpus_estrato": int(len(cc)),
        "alvo_cochran": args.alvo,
        "cochran": "95% de confiança, margem 5%, p=0,50, corrigido para população finita",
        "seed": args.seed,
        "do_teste_anterior_contam_para_alvo": reaproveitaveis,
        "da_calibracao_excluidos_sem_contar": queimados,
        "itens_novos_a_anotar": int(len(amostra)),
        "expressoes_na_amostra": int(amostra["matched_expression"].nunique()),
        "nota": ("amostra autoponderada: a precisão global é a proporção simples de "
                 "positivos, sem pesos. NÃO sustenta análise por expressão do léxico — "
                 "a cauda do léxico sai com zero ou poucos itens."),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False),
                                       encoding="utf-8")
    # Um desenho autoponderado não tem pesos por estrato; remover o arquivo da
    # versão estratificada evita que a análise use pesos que não valem mais.
    antigo = out / "pesos_por_estrato.csv"
    if antigo.exists():
        antigo.unlink()
        logger.info("pesos_por_estrato.csv removido (não se aplica a desenho autoponderado)")

    cobertura = amostra["matched_expression"].value_counts()
    logger.info("amostra aleatória simples: %d itens novos + %d reaproveitados = %d",
                len(amostra), reaproveitaveis, len(amostra) + reaproveitaveis)
    logger.info("expressões representadas: %d de %d do estrato",
                len(cobertura), cc["matched_expression"].nunique())
    print(cobertura.to_string())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default=str(ROOT / "validation" / "sample_code_comment"))
    ap.add_argument("--alvo", type=int, default=ALVO_TOTAL)
    ap.add_argument("--piso", type=int, default=PISO_ESTRATO)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--aleatoria-simples", action="store_true",
                    help="sorteio único do pool, sem estratificar por expressão. "
                         "A amostra fica autoponderada (não precisa de pesos na análise), "
                         "mas não sustenta análise por expressão do léxico.")
    args = ap.parse_args()

    if args.aleatoria_simples:
        return amostra_simples(args)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    corpus = pd.read_csv(CORPUS, low_memory=False)
    cc = corpus[corpus["artifact_type"] == ARTIFACT].copy()
    cc["_chave"] = cc.apply(chave, axis=1)
    logger.info("%s no corpus: %d itens, %d expressões",
                ARTIFACT, len(cc), cc["matched_expression"].nunique())

    ja = carrega_ja_anotados()
    cc["_ja_anotado"] = cc["_chave"].isin(ja)
    logger.info("%d itens do estrato já foram anotados na rodada multi-artefato",
                int(cc["_ja_anotado"].sum()))

    tamanhos = cc["matched_expression"].value_counts()
    raras = tamanhos[tamanhos < MIN_CENSO]
    comuns = tamanhos[tamanhos >= MIN_CENSO]

    # Alocação: proporcional ao tamanho, com piso. O piso é o que garante base
    # para a QP2 nas expressões de cauda longa.
    cota = (comuns / comuns.sum() * args.alvo).round().astype(int).clip(lower=args.piso)

    rng_base = args.seed
    blocos, pesos = [], []
    disponivel = cc[~cc["_ja_anotado"]]

    for expr in comuns.index:
        n_alvo = int(cota[expr])
        ja_tem = int(((cc["matched_expression"] == expr) & cc["_ja_anotado"]).sum())
        faltam = max(0, n_alvo - ja_tem)
        pool = disponivel[disponivel["matched_expression"] == expr]
        n = min(faltam, len(pool))
        if n:
            blocos.append(pool.sample(n=n, random_state=rng_base))
        rng_base += 1
        pesos.append({"matched_expression": expr, "estrato": "amostrada",
                      "no_corpus": int(comuns[expr]), "cota": n_alvo,
                      "ja_anotados": ja_tem, "novos": n,
                      "peso": comuns[expr] / max(1, n_alvo)})

    for expr in raras.index:
        ja_tem = int(((cc["matched_expression"] == expr) & cc["_ja_anotado"]).sum())
        pool = disponivel[disponivel["matched_expression"] == expr]
        if len(pool):
            blocos.append(pool)
        pesos.append({"matched_expression": expr, "estrato": "censo",
                      "no_corpus": int(raras[expr]), "cota": int(raras[expr]),
                      "ja_anotados": ja_tem, "novos": len(pool),
                      "peso": 1.0})

    amostra = pd.concat(blocos, ignore_index=True) if blocos else pd.DataFrame()
    amostra = amostra.drop(columns=["_chave", "_ja_anotado"], errors="ignore")
    # Ordem de apresentação embaralhada: anotar 60 itens seguidos da mesma
    # expressão cria efeito de arrastamento na decisão.
    amostra = amostra.sample(frac=1.0, random_state=args.seed).reset_index(drop=True)
    amostra.insert(0, "item_id", [f"cc{i + 1:04d}" for i in range(len(amostra))])

    amostra.to_csv(out / "amostra_code_comment.csv", index=False)
    tabela_pesos = pd.DataFrame(pesos).sort_values("no_corpus", ascending=False)
    tabela_pesos.to_csv(out / "pesos_por_estrato.csv", index=False)

    manifest = {
        "artefato": ARTIFACT,
        "corpus_estrato": int(len(cc)),
        "expressoes_no_estrato": int(cc["matched_expression"].nunique()),
        "alvo_cochran": args.alvo,
        "piso_por_estrato": args.piso,
        "corte_censo": MIN_CENSO,
        "seed": args.seed,
        "ja_anotados_reaproveitaveis": int(cc["_ja_anotado"].sum()),
        "itens_novos_a_anotar": int(len(amostra)),
        "expressoes_por_censo": int(len(raras)),
        "expressoes_amostradas": int(len(comuns)),
        "aviso": ("amostra NÃO autoponderada — use pesos_por_estrato.csv para "
                  "qualquer estimativa global"),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False),
                                       encoding="utf-8")

    print(tabela_pesos[["matched_expression", "estrato", "no_corpus", "cota",
                        "ja_anotados", "novos"]].to_string(index=False))
    logger.info("amostra com %d itens novos -> %s", len(amostra), out)


if __name__ == "__main__":
    main()
