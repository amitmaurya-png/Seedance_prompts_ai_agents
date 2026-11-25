"""Read and write the pipeline's JSON files."""

import hashlib
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("agent")


def save_json(path: Path, data: Any, backup: bool = True) -> None:
    """Write JSON, keeping a timestamped backup of any existing file in <dir>/backups/."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if backup and path.exists():
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


def load_saved(path: Path, pdf_path: str) -> Optional[Dict[str, Any]]:
    """A node's saved output, if it exists and was made from this skit.

    Returns None when the file is missing, unreadable, or from another PDF, so
    the node calls the LLM instead. Delete the file to make the node run again.
    """
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        log.warning("Ignoring %s (%s); calling the LLM instead", path.name, error)
        return None
    if not isinstance(data, dict):
        log.warning("Ignoring %s (not a JSON object); calling the LLM instead", path.name)
        return None
    # Files written before "source" was added are trusted as this skit's.
    source = data.get("source")
    if source and Path(source).resolve() != Path(pdf_path).resolve():
        log.info("%s is from another skit (%s); calling the LLM instead", path.name, source)
        return None
    return data


class ProgressFile:
    """A checkpoint file rewritten after every LLM call, so finished work survives
    a crash and the next run can reuse it.

    `saved(id)` returns the previous run's entry. `keep` carries a reused entry
    over without writing; `add` stores a new result and rewrites the file. The
    first write of a run backs up the previous run's file.
    """

    def __init__(self, path: Path, pdf_path: str, key: str):
        self.path, self.key = path, key
        previous = load_saved(path, pdf_path) or {}
        self._previous: Dict[str, Any] = previous.get(key) or {}
        self.data: Dict[str, Any] = {"source": pdf_path, key: {}}
        self._first_write = True

    def saved(self, item_id: str) -> Optional[Dict[str, Any]]:
        entry = self._previous.get(item_id)
        return entry if isinstance(entry, dict) else None

    def keep(self, item_id: str, entry: Dict[str, Any]) -> None:
        self.data[self.key][item_id] = entry

    def add(self, item_id: str, result: Dict[str, Any]) -> None:
        self.data[self.key][item_id] = result
        save_json(self.path, self.data, backup=self._first_write)
        self._first_write = False


def fingerprint(data: Any) -> str:
    """A short hash of a node's input, to tell whether a saved result still fits."""
    text = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
