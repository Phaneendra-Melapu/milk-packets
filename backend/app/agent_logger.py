import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = PROJECT_ROOT / "backend" / "logs"
LOG_FILE = LOG_DIR / "agent_logs.json"


def write_agent_log(
    agent_name: str,
    result: str,
    step: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent_name": agent_name,
        "step": step,
        "result": result,
        "details": details or {},
    }

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    entries = read_agent_logs(limit=0)
    entries.append(entry)
    LOG_FILE.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    return entry


def read_agent_logs(limit: int = 50) -> list[dict[str, Any]]:
    if not LOG_FILE.exists():
        return []

    entries = json.loads(LOG_FILE.read_text(encoding="utf-8"))
    if limit <= 0:
        return entries
    return entries[-limit:]
