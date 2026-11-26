"""Reuse earlier LLM results instead of paying for them again.

Two kinds of saved output:

    load_saved     a node's whole output file (breakdown.json, characters.json,
                   asset_prompts.json), reused when it fits the current run
    ProgressFile   a checkpoint written after every LLM call (clip_plans.json,
                   clip_prompts.json), reused item by item

    fingerprint    a short hash of an item's input; a saved item is reused only
                   when its input hasn't changed

Delete a file to make its node call the LLM again.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from agent.helpers.json_files import save_json

log = logging.getLogger("agent")


def load_saved(path: Path, pdf_path: str) -> dict[str, Any] | None:
    """The file's contents if it exists and was made from this skit, else None."""
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
    """A checkpoint file of {item id: result}, rewritten after every LLM call.

        saved(id)        the previous run's result for an item, or None
        keep(id, entry)  carry a reused result over (no write: it's already in the file)
        add(id, entry)   store a new result and rewrite the file

    The first write of a run backs up the previous run's file.
    """

    def __init__(self, path: Path, pdf_path: str, key: str):
        self.path, self.key = path, key
        previous = load_saved(path, pdf_path) or {}
        self._previous: dict[str, Any] = previous.get(key) or {}
        self.data: dict[str, Any] = {"source": pdf_path, key: {}}
        self._first_write = True

    def saved(self, item_id: str) -> dict[str, Any] | None:
        entry = self._previous.get(item_id)
        return entry if isinstance(entry, dict) else None

    def keep(self, item_id: str, entry: dict[str, Any]) -> None:
        self.data[self.key][item_id] = entry

    def add(self, item_id: str, entry: dict[str, Any]) -> None:
        self.data[self.key][item_id] = entry
        save_json(self.path, self.data, backup=self._first_write)
        self._first_write = False


def fingerprint(data: Any) -> str:
    """A short hash of some JSON-able input."""
    text = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
