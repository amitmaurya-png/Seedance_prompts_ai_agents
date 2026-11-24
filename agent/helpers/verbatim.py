"""Check that actions and dialogue are copied word for word, in order."""

import re
from typing import Any, Dict, Iterable, List

ASSET_TAG = re.compile(r"\s*\(@(?:Image|Video|Audio) \d+\)")
QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})


def normalize(text: str) -> str:
    """Compare text ignoring line wraps, curly quotes, and @Image tags."""
    text = ASSET_TAG.sub("", text).translate(QUOTES)
    return " ".join(text.split())


def shot_pieces(shots: Iterable[Dict[str, Any]]) -> List[str]:
    """Each shot's action followed by its dialogue lines, in order."""
    pieces = []
    for shot in shots:
        pieces.append(shot.get("action", ""))
        pieces.extend(line.get("line", "") for line in shot.get("dialogue", []))
    return pieces


def check_verbatim(pieces: Iterable[str], source: str) -> List[str]:
    """Pieces that don't appear in source word for word and in order.

    Each piece must be found after the previous one.
    """
    haystack = normalize(source)
    position = 0
    problems = []
    for piece in pieces:
        needle = normalize(piece)
        if not needle:
            continue
        found = haystack.find(needle, position)
        if found == -1:
            where = "out of order" if needle in haystack else "not in the source"
            problems.append(f"{where}: {_short(needle)}")
        else:
            position = found + len(needle)
    return problems


def find_dropped_text(pieces: Iterable[str], source: str) -> List[str]:
    """Stretches of story text in source that no piece covers.

    Character cues (all caps), parentheticals and transitions are ignored.
    """
    leftover = normalize(source)
    for piece in pieces:
        needle = normalize(piece)
        if needle:
            leftover = leftover.replace(needle, "\n", 1)

    dropped = []
    for chunk in leftover.split("\n"):
        chunk = re.sub(r"\([^)]*\)", " ", chunk)
        story_words = [w for w in chunk.split() if any(c.islower() for c in w)]
        if len(story_words) >= 3:
            dropped.append(_short(" ".join(chunk.split())))
    return dropped


def _short(text: str, limit: int = 80) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"
