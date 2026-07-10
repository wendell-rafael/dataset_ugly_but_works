"""Carregamento simples de arquivos .env, sem dependência externa."""
from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(path: str | Path = ".env") -> None:
    """Lê pares KEY=VALUE de um arquivo .env e injeta em os.environ.

    Não sobrescreve variáveis já definidas no ambiente (o ambiente do
    shell tem prioridade sobre o arquivo). Linhas vazias ou iniciadas com
    '#' são ignoradas.
    """
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value
