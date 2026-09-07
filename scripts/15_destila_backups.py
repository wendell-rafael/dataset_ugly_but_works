#!/usr/bin/env python3
"""Destila os .bak de CSV em trilha de auditoria pequena.

Os backups em `data/full_run/` guardam 527 MB para documentar correcoes que
removeram algumas centenas de registros. A informacao que importa e *quais*
registros sairam e por que -- isso cabe em ~1 MB, no mesmo formato que a rodada
de julho ja usou (`data/final/purged_records_2026-07-06.csv`).

Para cada par (backup, arquivo atual), extrai os registros presentes no backup e
ausentes no atual, identificados pela chave natural da coleta:

    repo_full_name + artifact_type + artifact_id + matched_expression

Escreve um CSV por par mais um manifesto com sha256 de entrada e saida, para a
exclusao do backup ficar auditavel depois.

Nao apaga nada. Rodar, conferir a saida e so entao remover os originais.

Uso:
    python3 scripts/15_destila_backups.py            # extrai e relata
    python3 scripts/15_destila_backups.py --dry-run  # so relata as contagens
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
BASE = RAIZ / "data" / "full_run"
SAIDA = BASE / "auditoria_backups"

CHAVE = ["repo_full_name", "artifact_type", "artifact_id", "matched_expression"]

# (backup, arquivo atual, rotulo, motivo da remocao)
PARES = [
    (
        "ubw_collected_consolidated.csv.bak_prerepair",
        "ubw_collected_consolidated.csv",
        "reparo_consolidado",
        "Registro descartado no reparo do CSV consolidado em 2026-07-27.",
    ),
    (
        "ubw_collected_full.csv.bak_botfilter",
        "ubw_collected_full.csv",
        "filtro_bot",
        "Artefato de bot: texto de changelog de terceiros citado em PR de bump "
        "de dependencia, nao fala do time. Filtro por login de bot.",
    ),
    (
        "ubw_collected_full.csv.bak_corrupcao_2026-07-23",
        "ubw_collected_full.csv",
        "corrupcao_2026-07-23",
        "Estagio anterior ao incidente de corrupcao de 2026-07-23. Diferenca "
        "inclui tanto registros removidos quanto registros coletados depois.",
    ),
]

# Vencido e regeravel por 06_export_publishable.py -- nao tem o que destilar.
DESCARTAVEIS = ["ubw_publishable_partial.csv"]


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def chaves(df: pd.DataFrame) -> pd.Series:
    """Chave natural da coleta, como texto.

    Concatena coluna a coluna em vez de `agg(join, axis=1)`: `artifact_id` vem
    como float quando a coluna tem NaN, e nesse caso o `astype(str)` do
    DataFrame inteiro nao normaliza todas as celulas. `\\x1f` como separador
    porque nome de repo e expressao podem conter praticamente qualquer coisa.
    """
    faltando = [c for c in CHAVE if c not in df.columns]
    if faltando:
        raise SystemExit(f"colunas de chave ausentes: {faltando}")
    partes = [df[c].fillna("").map(str) for c in CHAVE]
    chave = partes[0]
    for parte in partes[1:]:
        chave = chave + "\x1f" + parte
    return chave


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true",
                   help="so conta, nao escreve arquivo")
    args = p.parse_args()

    if not args.dry_run:
        SAIDA.mkdir(parents=True, exist_ok=True)

    registros: list[dict] = []
    extraidos: list[pd.DataFrame] = []
    for nome_bak, nome_atual, rotulo, motivo in PARES:
        bak, atual = BASE / nome_bak, BASE / nome_atual
        if not bak.exists():
            print(f"AUSENTE  {nome_bak} -- pulando")
            continue

        print(f"\n=== {rotulo} ===")
        print(f"  backup: {nome_bak}  ({bak.stat().st_size / 2**20:.0f} MB)")
        d_bak = pd.read_csv(bak, low_memory=False)
        d_atual = pd.read_csv(atual, low_memory=False)

        k_bak, k_atual = chaves(d_bak), chaves(d_atual)
        so_no_bak = d_bak.loc[~k_bak.isin(set(k_atual))].copy()
        so_no_atual = int((~k_atual.isin(set(k_bak))).sum())

        print(f"  backup {len(d_bak)} registros | atual {len(d_atual)}")
        print(f"  so no backup (extraidos): {len(so_no_bak)}")
        print(f"  so no atual (nao extraidos): {so_no_atual}")

        if len(so_no_bak):
            por_tipo = so_no_bak["artifact_type"].value_counts().to_dict()
            print(f"  por artefato: {por_tipo}")
            if "author_login" in so_no_bak.columns:
                top = so_no_bak["author_login"].value_counts().head(5).to_dict()
                print(f"  top autores: {top}")

        entrada = {
            "rotulo": rotulo,
            "motivo": motivo,
            "backup": nome_bak,
            "backup_sha256": sha256(bak),
            "backup_registros": int(len(d_bak)),
            "atual": nome_atual,
            "atual_registros": int(len(d_atual)),
            "extraidos": int(len(so_no_bak)),
            "so_no_atual": so_no_atual,
        }
        registros.append(entrada)

        if len(so_no_bak):
            so_no_bak.insert(0, "origem_backup", rotulo)
            extraidos.append(so_no_bak)

    # Um arquivo so, deduplicado: os backups se sobrepoem muito (o de corrupcao
    # e quase o mesmo conjunto do filtro de bot), e escrever um CSV por par
    # gastaria dezenas de MB para repetir os mesmos registros.
    if extraidos and not args.dry_run:
        juntos = pd.concat(extraidos, ignore_index=True)
        k = chaves(juntos)
        origem = (juntos.groupby(k.values)["origem_backup"]
                  .agg(lambda s: ";".join(sorted(set(s)))))
        juntos = juntos.loc[~k.duplicated()].copy()
        juntos["origem_backup"] = chaves(juntos).map(origem).values

        destino = SAIDA / "purged_registros.csv"
        juntos.to_csv(destino, index=False)
        print(f"\n=== consolidado ===")
        print(f"  {len(juntos)} registros unicos "
              f"(de {sum(len(e) for e in extraidos)} extraidos, com sobreposicao)")
        print(f"  por origem: "
              f"{juntos['origem_backup'].value_counts().to_dict()}")
        print(f"  -> {destino.relative_to(RAIZ)} "
              f"({destino.stat().st_size / 1024:.0f} KB)")
        manifesto_saida = {
            "arquivo": destino.name,
            "sha256": sha256(destino),
            "bytes": destino.stat().st_size,
            "registros": int(len(juntos)),
        }
    else:
        manifesto_saida = None

    print("\n=== descartaveis sem destilacao ===")
    for nome in DESCARTAVEIS:
        caminho = BASE / nome
        if caminho.exists():
            print(f"  {nome} ({caminho.stat().st_size / 2**20:.0f} MB) -- "
                  "vencido, regeravel por 06_export_publishable.py")

    if not args.dry_run:
        manifesto = {
            "script": Path(__file__).name,
            "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
            "chave_de_identidade": CHAVE,
            "saida": manifesto_saida,
            "pares": registros,
            "descartaveis_sem_destilacao": DESCARTAVEIS,
            "nota": "Os backups originais NAO foram apagados por este script. "
                    "Conferir esta saida antes de remove-los.",
        }
        alvo = SAIDA / "manifest.json"
        alvo.write_text(json.dumps(manifesto, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
        print(f"\nmanifesto em {alvo.relative_to(RAIZ)}")

    liberavel = sum((BASE / n).stat().st_size for n, _, _, _ in PARES
                    if (BASE / n).exists())
    liberavel += sum((BASE / n).stat().st_size for n in DESCARTAVEIS
                     if (BASE / n).exists())
    print(f"\nespaco liberavel ao remover os originais: "
          f"{liberavel / 2**20:.0f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
