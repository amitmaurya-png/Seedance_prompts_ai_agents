"""Write the pipeline's JSON output files."""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from agent.state import Clip


def save_json(path: Path, data: Any, backup: bool = True) -> None:
    """Write JSON, first copying any existing file to <dir>/backups/<name>-<time>.json."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if backup and path.exists():
        backups = path.parent / "backups"
        backups.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(path, backups / f"{path.stem}-{stamp}{path.suffix}")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_prompt_json(path: Path, pdf_path: str, clips: list[Clip], skills: list[str]) -> None:
    """data/prompt.json: every clip with its final prompt."""
    save_json(
        path,
        {
            "source": pdf_path,
            "skills": skills,
            "clip_count": len(clips),
            "total_seconds": sum(c["duration_seconds"] for c in clips),
            "clips": clips,
        },
    )
