#!/usr/bin/env python3
"""Verifica se algum arquivo versionavel carrega PII.

O repositorio e publico e commit e permanente -- sai do historico so
reescrevendo tudo e forcando push. Este script existe porque a checagem obvia
(olhar o cabecalho do CSV procurando coluna com "email" no nome) deixa passar o
caso mais comum: o e-mail esta *dentro* de `body_text`, em trailers
`Signed-off-by:` e `Co-authored-by:` que vieram do proprio artefato coletado.
Nenhuma coluna se chama "email" nesses arquivos.

Duas origens de PII, ambas verificadas aqui:
  1. colunas `author_name` / `author_login` / `author_email` -- dado bruto que
     fica no dataset de trabalho para uma survey futura;
  2. conteudo com e-mail literal em qualquer campo, `body_text` inclusive.

Uso:
    python3 scripts/14_check_pii.py              # o que o git versionaria
    python3 scripts/14_check_pii.py --staged     # so o que esta no index
    python3 scripts/14_check_pii.py caminho/...  # arquivos avulsos

Sai com codigo 1 se achar PII, para servir de pre-commit hook.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# Falsos positivos conhecidos: placeholders do mascarador, dominios de exemplo
# e os enderecos que o proprio GitHub gera para contas sem e-mail publico.
BENIGNO = re.compile(
    r"REDACTED|example\.(com|org|net)|@users\.noreply\.github\.com|^noreply@",
    re.IGNORECASE,
)

COLUNAS_PII = ("author_name", "author_login", "author_email")

# Texto e dado; binario nao interessa.
EXTENSOES = {".csv", ".jsonl", ".json", ".html", ".md", ".txt", ".tsv"}


def arquivos_versionaveis() -> list[Path]:
    """Tudo que o git versionaria: rastreado + novo nao ignorado."""
    saida = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=RAIZ, capture_output=True, text=True, check=True,
    ).stdout
    return [RAIZ / linha for linha in saida.splitlines() if linha]


def arquivos_no_index() -> list[Path]:
    saida = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        cwd=RAIZ, capture_output=True, text=True, check=True,
    ).stdout
    return [RAIZ / linha for linha in saida.splitlines() if linha]


def inspeciona(caminho: Path) -> tuple[list[str], list[str]]:
    """Devolve (emails_encontrados, colunas_de_pii)."""
    try:
        texto = caminho.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return [], []

    emails = sorted({m for m in EMAIL.findall(texto) if not BENIGNO.search(m)})

    colunas: list[str] = []
    if caminho.suffix == ".csv":
        try:
            cabecalho = next(csv.reader(texto.splitlines()))
        except (StopIteration, csv.Error):
            cabecalho = []
        colunas = [c for c in cabecalho if c in COLUNAS_PII]

    return emails, colunas


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("caminhos", nargs="*", type=Path)
    p.add_argument("--staged", action="store_true",
                   help="checa so o que esta no index do git")
    args = p.parse_args()

    if args.caminhos:
        alvos = args.caminhos
    elif args.staged:
        alvos = arquivos_no_index()
    else:
        alvos = arquivos_versionaveis()

    alvos = [a for a in alvos if a.suffix in EXTENSOES and a.is_file()]

    achados = []
    for alvo in sorted(alvos):
        emails, colunas = inspeciona(alvo)
        if emails or colunas:
            achados.append((alvo, emails, colunas))

    print(f"{len(alvos)} arquivos verificados")

    if not achados:
        print("OK -- nenhuma PII encontrada")
        return 0

    print(f"\nPII ENCONTRADA em {len(achados)} arquivo(s):\n")
    for alvo, emails, colunas in achados:
        rel = alvo.relative_to(RAIZ)
        print(f"  {rel}")
        if colunas:
            print(f"      colunas: {', '.join(colunas)}")
        if emails:
            amostra = ", ".join(emails[:3])
            resto = f" (+{len(emails) - 3})" if len(emails) > 3 else ""
            print(f"      {len(emails)} e-mail(s): {amostra}{resto}")
    print("\nOpcoes: manter fora do git (.gitignore) ou mascarar body_text com")
    print("o mascarador de scripts/06_export_publishable.py e versionar a copia")
    print("mascarada. Ver validation/POLITICA_ANONIMIZACAO.md.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
