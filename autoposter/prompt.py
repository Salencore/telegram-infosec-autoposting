from __future__ import annotations

import re
from pathlib import Path


def extract_system_prompt(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"## Системный промпт\s+```text\s+(.*?)\s+```", text, re.S)
    if not match:
        raise RuntimeError(f"System prompt block not found in {path}")
    return match.group(1).strip()
