"""Read the skit PDF and split it into scenes."""

import re
from pathlib import Path
from typing import List

from pypdf import PdfReader

from agent.state import Scene

SCENE_HEADING = re.compile(r"^(?:INT\.|EXT\.|INT/EXT\.?|EXT/INT\.?)\s.*$", re.MULTILINE)
PAGE_NUMBER_LINE = re.compile(r"^\s*\d+\.\s*$", re.MULTILINE)
MORE_LINE = re.compile(r"^\s*\(MORE\)\s*$", re.MULTILINE)
CONTD = re.compile(r"\s*\(CONT[’']D\)")


def read_pdf_text(path: Path) -> str:
    """Text of every page, with page numbers, (MORE) and (CONT'D) removed."""
    pages = (page.extract_text() or "" for page in PdfReader(str(path)).pages)
    text = "\n".join(pages)
    text = PAGE_NUMBER_LINE.sub("", text)
    text = MORE_LINE.sub("", text)
    return CONTD.sub("", text)


def split_scenes(text: str) -> List[Scene]:
    """Split the skit at INT./EXT. headings. Text before the first heading is dropped.

    Returns [{"number": 1, "heading": "EXT. ...", "text": "..."}].
    """
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
