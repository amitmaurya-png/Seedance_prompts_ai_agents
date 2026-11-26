"""Read the breakdown back as script text, speakers and locations."""

import re

from agent.state import Scene

# The " - DAY" / " — MORNING" part of a heading (hyphen, en dash or em dash).
TIME_OF_DAY = re.compile(r"\s+[-–—]\s+[A-Z][A-Z .']*$")
INT_EXT = re.compile(r"^(?:INT\./EXT\.|INT\.|EXT\.)\s*")


def speakers(scenes: list[Scene]) -> list[str]:
    """Speaking characters (upper case), in order of their first line."""
    names: list[str] = []
    for scene in scenes:
        for shot in scene["shots"]:
            for line in shot.get("dialogue", []):
                name = line.get("character", "").strip().upper()
                if name and name not in names:
                    names.append(name)
    return names


def locations(scenes: list[Scene]) -> list[str]:
    """Distinct places from the scene headings, in order of first appearance.

    "EXT. SABA'S COURTYARD — DAY" -> "SABA'S COURTYARD"
    """
    places: list[str] = []
    for scene in scenes:
        place = TIME_OF_DAY.sub("", INT_EXT.sub("", scene["heading"].strip()))
        if place and place not in places:
            places.append(place)
    return places


def script_text(scenes: list[Scene]) -> str:
    """The breakdown as plain script text: heading, actions and lines."""
    parts = []
    for scene in scenes:
        parts.append(scene["heading"])
        for shot in scene["shots"]:
            if shot.get("action"):
                parts.append(shot["action"])
            for line in shot.get("dialogue", []):
                note = f" {line['parenthetical']}" if line.get("parenthetical") else ""
                parts.append(f"{line.get('character', '')}{note}: {line.get('line', '')}")
        parts.append("")
    return "\n".join(parts)
