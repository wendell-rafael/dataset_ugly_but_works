"""Dead Letter Queue: registra falhas persistentes de item de trabalho
(ex: repo+artefato) para revisão manual, e evita reprocessar cegamente um
item que já falhou repetidamente em toda retomada futura.

Diferente do CheckpointState (scripts/02_collect_multiartifact.py), que só
distingue "concluído" de "pendente" — sem DLQ, um item permanentemente
quebrado (repo apagado, grande demais pra clonar, etc.) fica "pendente"
pra sempre e é retentado do zero a cada retomada.
"""
from __future__ import annotations

import csv
import threading
import time
from pathlib import Path


class DeadLetterQueue:
    """Thread-safe. Cada falha de um item é uma linha no CSV de saída
    (append). Um item é considerado permanentemente morto (`should_skip`)
    após `max_attempts` falhas registradas.
    """

    FIELDNAMES = ["key", "reason", "attempt", "timestamp"]

    def __init__(self, path: Path, max_attempts: int = 3):
        self.path = path
        self.max_attempts = max_attempts
        self._lock = threading.Lock()
        self._attempts: dict[str, int] = {}

        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and self.path.stat().st_size > 0:
            with self.path.open("r", newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    key = row["key"]
                    self._attempts[key] = max(self._attempts.get(key, 0), int(row["attempt"]))

        write_header = not self.path.exists() or self.path.stat().st_size == 0
        self._fh = self.path.open("a", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._fh, fieldnames=self.FIELDNAMES)
        if write_header:
            self._writer.writeheader()
            self._fh.flush()

    def record_failure(self, key: str, reason: str) -> int:
        """Registra uma falha para `key`, retorna o número de tentativas
        acumuladas (incluindo esta)."""
        with self._lock:
            attempt = self._attempts.get(key, 0) + 1
            self._attempts[key] = attempt
            self._writer.writerow({
                "key": key,
                "reason": reason[:300],
                "attempt": attempt,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            })
            self._fh.flush()
            return attempt

    def should_skip(self, key: str) -> bool:
        """True se `key` já esgotou max_attempts — pula sem tentar de novo."""
        with self._lock:
            return self._attempts.get(key, 0) >= self.max_attempts

    def close(self) -> None:
        self._fh.close()
