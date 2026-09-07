#!/usr/bin/env python3
"""Gera as copias publicaveis dos arquivos de validation/ que carregam PII.

O repositorio e publico. 34 arquivos em `validation/` nao podem ser versionados
como estao, por duas razoes distintas:

  1. colunas `author_name` / `author_login` / `author_email` / `author_hash` --
     identidade bruta, guardada no dataset de trabalho para uma survey futura;
  2. coluna `body_text` (e o texto embutido nos HTML) -- o artefato coletado traz
     e-mail em trailers `Signed-off-by:` e `Co-authored-by:`. Este e o caso da
     maioria, e o que engana: nenhuma coluna se chama "email".

Este script escreve um espelho em `validation/publicavel/`, mantendo a estrutura
de diretorios, com:

  - `body_text` mascarado pelo MESMO mascarador do export do corpus
    (`06_export_publishable.apply_pii_masking`), para os dois artefatos nao
    divergirem em politica;
  - as quatro colunas de identidade removidas.

`author_hash` sai junto das outras tres de proposito. E SHA-256 sem salt do
e-mail ou do login (`ubw.schema.compute_author_hash`), e o proprio schema
descreve como "reidentificavel com uma lista de candidatos" -- lista de logins
do GitHub e trivial de obter, entao em repositorio publico a pseudonimizacao
nao se sustenta. Nas amostras de validacao a identidade do autor nao entra em
nenhuma analise, logo nao ha o que perder removendo.

Os originais nao sao tocados: seguem em disco como versao de trabalho, fora do
git. Ver validation/POLITICA_ANONIMIZACAO.md e validation/D1_EXPORT_PII_FINDINGS.md.

Uso:
    python3 scripts/16_mascara_validation.py
    python3 scripts/16_mascara_validation.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BASE = RAIZ / "validation"
SAIDA = BASE / "publicavel"

COLUNAS_IDENTIDADE = ("author_name", "author_login", "author_email", "author_hash")

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
BENIGNO = re.compile(
    r"REDACTED|example\.(com|org|net)|@users\.noreply\.github\.com|^noreply@",
    re.IGNORECASE,
)


def carrega_mascarador():
    """Importa `apply_pii_masking` do 06 (nome de modulo comeca com digito)."""
    caminho = RAIZ / "scripts" / "06_export_publishable.py"
    spec = importlib.util.spec_from_file_location("export_publishable", caminho)
    if spec is None or spec.loader is None:
        raise SystemExit(f"nao consegui carregar {caminho}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.apply_pii_masking


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def emails_restantes(texto: str) -> list[str]:
    return sorted({m for m in EMAIL.findall(texto) if not BENIGNO.search(m)})


def alvos() -> list[Path]:
    """Arquivos de validation/ que carregam PII ou podem passar a carregar.

    A presenca da coluna `body_text` basta para entrar, mesmo sem e-mail hoje:
    "nao tem e-mail agora" nao e garantia se o arquivo for regerado a partir do
    corpus. Selecionar por conteudo atual deixaria um arquivo de fora sempre
    que a amostra mudasse.
    """
    encontrados = []
    for p in sorted(BASE.rglob("*")):
        if not p.is_file() or "archive" in p.parts or "publicavel" in p.parts:
            continue
        if p.suffix not in {".csv", ".html", ".md", ".json", ".jsonl"}:
            continue
        try:
            texto = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        tem_email = bool(emails_restantes(texto))
        tem_coluna = False
        if p.suffix == ".csv":
            try:
                cabecalho = next(csv.reader(texto.splitlines()))
                tem_coluna = any(
                    c in COLUNAS_IDENTIDADE or c == "body_text"
                    for c in cabecalho
                )
            except (StopIteration, csv.Error):
                pass
        if tem_email or tem_coluna:
            encontrados.append(p)
    return encontrados


def mascara_csv(origem: Path, destino: Path, mascarar, seco: bool) -> dict:
    with origem.open(encoding="utf-8-sig", newline="") as fh:
        leitor = csv.DictReader(fh)
        campos = list(leitor.fieldnames or [])
        removidas = [c for c in campos if c in COLUNAS_IDENTIDADE]
        mantidas = [c for c in campos if c not in COLUNAS_IDENTIDADE]
        linhas, contagens = [], Counter()

        for linha in leitor:
            saida = {c: linha.get(c) for c in mantidas}
            if "body_text" in saida:
                texto, contas, _ = mascarar(saida["body_text"], mask_mentions=True)
                saida["body_text"] = texto
                contagens.update(contas)
            linhas.append(saida)

    if not seco:
        destino.parent.mkdir(parents=True, exist_ok=True)
        with destino.open("w", encoding="utf-8", newline="") as fh:
            escritor = csv.DictWriter(fh, fieldnames=mantidas)
            escritor.writeheader()
            escritor.writerows(linhas)

    return {
        "linhas": len(linhas),
        "colunas_removidas": removidas,
        "mascaras": dict(sorted(contagens.items())),
    }


def mascara_texto(origem: Path, destino: Path, mascarar, seco: bool) -> dict:
    """HTML e Markdown: mascara o arquivo inteiro como um texto so.

    Os placeholders sao texto simples (`[PII_EMAIL_REDACTED]`), entao sobrevivem
    dentro de string JSON embutida em <script> sem quebrar a sintaxe. Mencoes
    ficam de fora aqui: `@algo` em HTML pega `@media`, `@font-face` e afins.
    """
    texto = origem.read_text(encoding="utf-8", errors="replace")
    mascarado, contas, _ = mascarar(texto, mask_mentions=False)
    if not seco:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(mascarado, encoding="utf-8")
    return {"bytes": len(mascarado), "mascaras": dict(sorted(contas.items()))}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    mascarar = carrega_mascarador()
    lista = alvos()
    print(f"{len(lista)} arquivos com PII\n")

    registros, falhas = [], []
    for origem in lista:
        rel = origem.relative_to(BASE)
        destino = SAIDA / rel
        if origem.suffix == ".csv":
            info = mascara_csv(origem, destino, mascarar, args.dry_run)
        else:
            info = mascara_texto(origem, destino, mascarar, args.dry_run)

        vazou = []
        if not args.dry_run and destino.exists():
            vazou = emails_restantes(
                destino.read_text(encoding="utf-8", errors="replace"))
            if vazou:
                falhas.append((rel, vazou))

        total = sum(info["mascaras"].values())
        marca = "FALHOU" if vazou else "ok"
        removidas = info.get("colunas_removidas") or []
        print(f"  {marca:6s} {total:>5} máscaras  "
              f"{'-' + str(len(removidas)) + ' cols  ' if removidas else '':9s}{rel}")

        entrada = {"arquivo": rel.as_posix(),
                   "origem_sha256": sha256(origem), **info}
        if not args.dry_run and destino.exists():
            entrada["saida_sha256"] = sha256(destino)
            entrada["emails_restantes"] = vazou
        registros.append(entrada)

    agregado = Counter()
    for r in registros:
        agregado.update(r["mascaras"])
    print(f"\nmáscaras aplicadas: {dict(sorted(agregado.items()))}")
    print(f"total: {sum(agregado.values())}")

    if falhas:
        print(f"\nFALHA -- e-mail sobrou em {len(falhas)} arquivo(s):")
        for rel, vazou in falhas:
            print(f"  {rel}: {vazou[:3]}")
        return 1

    if not args.dry_run:
        manifesto = {
            "script": Path(__file__).name,
            "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
            "mascarador": "scripts/06_export_publishable.py:apply_pii_masking",
            "colunas_removidas_sempre": list(COLUNAS_IDENTIDADE),
            "nota_author_hash": (
                "author_hash sai junto: SHA-256 sem salt de e-mail/login, "
                "reidentificavel com lista de candidatos (ubw/schema.py). Nao "
                "entra em nenhuma analise das amostras de validacao."
            ),
            "mascaras_agregadas": dict(sorted(agregado.items())),
            "arquivos": registros,
        }
        alvo = SAIDA / "manifest.json"
        alvo.write_text(json.dumps(manifesto, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
        print(f"\nmanifesto em {alvo.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
