"""Journal d'audit : une ligne JSON par appel d'outil (traçabilité)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLog:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.entries: list[dict[str, Any]] = []

    def record(self, **fields: Any) -> None:
        entry = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **fields}
        self.entries.append(entry)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def calls(self, tool: str | None = None) -> list[dict[str, Any]]:
        return [e for e in self.entries if e.get("event") == "tool_call" and tool in (None, e["tool"])]
