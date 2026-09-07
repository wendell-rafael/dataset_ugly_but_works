#!/usr/bin/env python3
"""Quantifica (e opcionalmente filtra) duplicação de `body_text` de
`code_comment` ENTRE repositórios diferentes.

Achado da exploração de 2026-07-29: 28,1% dos comentários de código do corpus
consolidado compartilham o texto exato com pelo menos um outro repositório.
Isso é diferente do que a auditoria do Agente C mediu, que olhou duplicata
DENTRO do mesmo repo e path vendorizado (3,99%). Cruzando entre repositórios
aparecem duas causas que o filtro de path não pega:

  1. Biblioteca de terceiro copiada para dentro do repo sob um caminho que
     não bate com `VENDORED_PATH_MARKERS` (jQuery, Boost, Eigen).
  2. Hard fork que o GitHub não marca como fork, então passou pelo critério
     `is_fork=false` da triagem (radare2/rizin, godot/Redot/WeDot,
     TencentKona-8/11/corretto, jruby/truffleruby).

Só se aplica a `code_comment`. Para commit/issue/PR, texto idêntico entre
repos é quase sempre coincidência legítima de frase curta ("temp fix" como
mensagem de commit), não contaminação.

O corte de quantos repositórios caracterizam contaminação é DECISÃO DO
ORIENTADOR, não do script. Por isso o relatório sai quebrado por faixa e o
`--min-repos` é explícito, sem valor "certo" embutido.

Uso:
    # relatório, não escreve nada
    python3 validation/cross_repo_duplication.py data/full_run/ubw_collected_consolidated.csv

    # aplica o filtro (com backup), removendo clusters de 6+ repositórios
    python3 validation/cross_repo_duplication.py <csv> --min-repos 6 --apply
"""
from __future__ import annotations

import argparse
import csv
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(10_000_000)

FAIXAS = [
    (2, 3, "2 repos (par: fork ou coincidência)"),
    (3, 6, "3-5 repos"),
    (6, 21, "6-20 repos"),
    (21, 10**9, "21+ repos (biblioteca vendorizada)"),
]


def load(path: Path) -> tuple[list[dict], list[str]]:
    with path.open("rb") as f:
        raw = f.read().replace(b"\x00", b"")
    reader = csv.DictReader(raw.decode("utf-8", errors="replace").splitlines())
    rows = list(reader)
    return rows, list(reader.fieldnames or [])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("csv_path", type=Path)
    p.add_argument("--min-repos", type=int, default=6,
                   help="Mínimo de repositórios distintos para tratar o texto como contaminação (default: 6).")
    p.add_argument("--apply", action="store_true",
                   help="Escreve o CSV filtrado, com backup. Sem isso, só relata.")
    args = p.parse_args()

    if not args.csv_path.exists():
        sys.exit(f"Arquivo não encontrado: {args.csv_path}")

    rows, fieldnames = load(args.csv_path)
    cc = [r for r in rows if r.get("artifact_type") == "code_comment"]
    print(f"Total de registros: {len(rows):,}")
    print(f"code_comment: {len(cc):,}\n")

    repos_por_texto: dict[str, set[str]] = defaultdict(set)
    for r in cc:
        repos_por_texto[r["body_text"]].add(r["repo_full_name"])

    print("=== Distribuição por tamanho de cluster ===")
    for lo, hi, label in FAIXAS:
        textos = {t for t, reps in repos_por_texto.items() if lo <= len(reps) < hi}
        n_reg = sum(1 for r in cc if r["body_text"] in textos)
        pct = 100 * n_reg / len(cc) if cc else 0
        print(f"  {label:38s} textos={len(textos):5,}  registros={n_reg:6,} ({pct:4.1f}%)")

    print("\n=== Maiores clusters (provável biblioteca de terceiro) ===")
    for texto, reps in sorted(repos_por_texto.items(), key=lambda kv: -len(kv[1]))[:8]:
        amostra = sorted(reps)[:3]
        print(f"  {len(reps):4d} repos | {texto[:64]!r}")
        print(f"        ex: {', '.join(amostra)}")

    print("\n=== Pares que mais compartilham texto (provável hard fork) ===")
    pares: Counter = Counter()
    for reps in repos_por_texto.values():
        if 2 <= len(reps) <= 5:
            rs = sorted(reps)
            for i in range(len(rs)):
                for j in range(i + 1, len(rs)):
                    pares[(rs[i], rs[j])] += 1
    for (r1, r2), n in pares.most_common(10):
        print(f"  {n:4d} textos | {r1}  <->  {r2}")

    contaminados = {t for t, reps in repos_por_texto.items() if len(reps) >= args.min_repos}
    alvo = [r for r in cc if r["body_text"] in contaminados]
    print(f"\n=== Corte em --min-repos {args.min_repos} ===")
    print(f"registros de code_comment atingidos: {len(alvo):,} ({100*len(alvo)/len(cc):.1f}% do code_comment)")
    print(f"code_comment cairia de {len(cc):,} para {len(cc)-len(alvo):,}")

    if alvo:
        rem_alvo = sum(1 for r in alvo if r.get("is_censored") == "0")
        rem_geral = sum(1 for r in cc if r.get("is_censored") == "0")
        print(f"taxa de remoção nos atingidos: {100*rem_alvo/len(alvo):.1f}% "
              f"(geral: {100*rem_geral/len(cc):.1f}%)")
        exprs = Counter(r["matched_expression"] for r in alvo)
        print("expressões mais atingidas: " + ", ".join(f"{e}={n}" for e, n in exprs.most_common(5)))

    if not args.apply:
        print("\nDry-run. Nada foi escrito. Use --apply para gravar o CSV filtrado.")
        return

    ids_remover = {id(r) for r in alvo}
    mantidos = [r for r in rows if id(r) not in ids_remover]
    backup = args.csv_path.with_suffix(args.csv_path.suffix + f".bak_crossrepo{args.min_repos}")
    shutil.copy2(args.csv_path, backup)
    print(f"\nBackup: {backup}")
    with args.csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(mantidos)
    print(f"CSV filtrado: {args.csv_path} ({len(mantidos):,} linhas mantidas)")


if __name__ == "__main__":
    main()
