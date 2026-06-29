"""Robuste Datei-Lese-/Schreiboperationen (macOS Sleep / parallele Zugriffe)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


def read_text(path: Path, *, retries: int = 5, encoding: str = "utf-8") -> str:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            return path.read_text(encoding=encoding)
        except OSError as exc:
            last = exc
            time.sleep(0.05 * (2**attempt))
    raise last or OSError(f"Lesen fehlgeschlagen: {path}")


def read_json(path: Path, *, retries: int = 5) -> Any:
    return json.loads(read_text(path, retries=retries))


def write_text_atomic(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    last: Exception | None = None
    for attempt in range(5):
        try:
            tmp.write_text(content, encoding=encoding)
            os.replace(tmp, path)
            return
        except OSError as exc:
            last = exc
            time.sleep(0.05 * (2**attempt))
    raise last or OSError(f"Schreiben fehlgeschlagen: {path}")


def write_json_atomic(path: Path, data: Any) -> None:
    write_text_atomic(path, json.dumps(data, indent=2), encoding="utf-8")
