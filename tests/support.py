from __future__ import annotations

import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parent.parent
TMP_ROOT = ROOT / ".test-tmp"
TMP_ROOT.mkdir(parents=True, exist_ok=True)


@contextmanager
def temp_dir() -> Iterator[str]:
    """Workspace-local temporary directory (sandbox-friendly, no chmod cleanup)."""
    path = TMP_ROOT / f"case-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield str(path)
    finally:
        shutil.rmtree(path, ignore_errors=True)
