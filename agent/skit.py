"""Read the skit PDF, split it into scenes, and check text is copied verbatim."""

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

from pypdf import PdfReader

SCENE_HEADING = re.compile(r"^(?:INT\.|EXT\.|INT/EXT\.?|EXT/INT\.?)\s.*$", re.MULTILINE)
PAGE_NUMBER_LINE = re.compile(r"^\s*\d+\.\s*$", re.MULTILINE)
MORE_LINE = re.compile(r"^\s*\(MORE\)\s*$", re.MULTILINE)
CONTD = re.compile(r"\s*\(CONT[’']D\)")
ASSET_TAG = re.compile(r"\s*\(@(?:Image|Video|Audio) \d+\)")
QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})


def read_pdf_text(path: Path) -> str:
    """Text of every page, with page numbers, (MORE) and (CONT'D) removed."""
    pages = (page.extract_text() or "" for page in PdfReader(str(path)).pages)
    text = "\n".join(pages)
    text = PAGE_NUMBER_LINE.sub("", text)
    text = MORE_LINE.sub("", text)
    return CONTD.sub("", text)


def split_scenes(text: str) -> List[Dict[str, Any]]:
    """Split the skit at INT./EXT. headings. Text before the first heading is dropped."""
    headings = list(SCENE_HEADING.finditer(text))
    scenes = []
    for number, match in enumerate(headings, start=1):
        end = headings[number].start() if number < len(headings) else len(text)
        scenes.append(
            {
                "number": number,
                "heading": match.group().strip(),
                "text": text[match.end() : end].strip(),
            }
        )
    return scenes


def normalize(text: str) -> str:
    """Compare text ignoring line wraps, curly quotes, and @Image tags."""
    text = ASSET_TAG.sub("", text).translate(QUOTES)
    return " ".join(text.split())


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


def scene_pieces(scene: Dict[str, Any]) -> List[str]:
    """A breakdown scene's actions and dialogue lines, in order."""
    pieces = []
    for shot in scene.get("shots", []):
        pieces.append(shot.get("action", ""))
        pieces.extend(line.get("line", "") for line in shot.get("dialogue", []))
    return pieces


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
        words = [w for w in chunk.split() if any(c.islower() for c in w)]
        if len(words) >= 3:
            dropped.append(_short(" ".join(chunk.split())))
    return dropped


def _short(text: str, limit: int = 80) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"
