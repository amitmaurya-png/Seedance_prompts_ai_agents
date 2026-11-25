"""Read and write the pipeline's JSON files."""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def save_json(path: Path, data: Any) -> None:
    """Write JSON, keeping a timestamped backup of any existing file in <dir>/backups/."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backups = path.parent / "backups"
        backups.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(path, backups / f"{path.stem}-{stamp}{path.suffix}")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_prompt_json(path: Path, pdf_path: str, clips: List[Dict[str, Any]], skills: List[str]) -> None:
    """data/prompt.json: the clips with their final prompts."""
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
