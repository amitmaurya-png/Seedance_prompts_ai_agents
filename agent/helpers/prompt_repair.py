"""Fix and check a director prompt in code.

    repair_prompt    fixes what needs no judgement: the style block, unused
                     @Image references, voice prompts, stray @Audio/@Video tags
    prompt_problems  what is left for the LLM to fix: dialogue that isn't word
                     for word, and @Image tags that aren't the clip's references
"""

import re
from typing import List

from agent import config
from agent.helpers.clips import clip_lines, clip_speakers
from agent.helpers.verbatim import check_verbatim, normalize
from agent.state import Clip, Profile

IMAGE_TAG = re.compile(r"@Image (\d+)")
# Voice and video references are attached by build_curl, never written by the director.
AUDIO_OR_VIDEO_TAG = re.compile(r"\s*\(?@(?:Video|Audio) \d+\)?")


def repair_prompt(prompt: str, clip: Clip, profiles: List[Profile]) -> str:
    prompt = AUDIO_OR_VIDEO_TAG.sub("", prompt)

    if normalize(config.STYLE_LINE) not in normalize(prompt):
        prompt = _add_to_section(prompt, "STYLE", config.STYLE_LINE, near_top=True)

    used = set(IMAGE_TAG.findall(prompt))
    for ref in clip["references"]:
        if str(ref["n"]) not in used:
            prompt = _add_to_section(prompt, "ACTIVE REFERENCES", f"@Image {ref['n']}: {ref['role']}")

    for voice in speaker_voices(clip, profiles):
        if normalize(voice.strip('"')) not in normalize(prompt):
            prompt = _add_to_section(prompt, "AUDIO", voice)
    return prompt


def prompt_problems(prompt: str, clip: Clip) -> List[str]:
    if not prompt.strip():
        return ["no prompt was returned for this clip"]

    problems = [f"dialogue {p}" for p in check_verbatim(clip_lines(clip), prompt)]

    expected = {str(r["n"]) for r in clip["references"]}
    unknown = sorted(set(IMAGE_TAG.findall(prompt)) - expected, key=int)
    problems += [f"@Image {n} is not one of this clip's references" for n in unknown]
    return problems


def speaker_voices(clip: Clip, profiles: List[Profile]) -> List[str]:
    """The locked voice prompts of the characters who speak in the clip."""
    speakers = set(clip_speakers(clip))
    return [
        (p.get("voice") or "").strip()
        for p in profiles
        if p["name"].strip().upper() in speakers and (p.get("voice") or "").strip()
    ]


def _add_to_section(prompt: str, heading: str, line: str, near_top: bool = False) -> str:
    """Add a line under a section heading, creating the section if it's missing
    (as the second block when `near_top`, else at the end)."""
    lines = prompt.split("\n")
    for index, text in enumerate(lines):
        if text.strip().rstrip(":").upper() == heading:
            lines.insert(index + 1, line)
            return "\n".join(lines)

    blocks = prompt.split("\n\n")
    blocks.insert(1 if near_top else len(blocks), f"{heading}\n{line}")
    return "\n\n".join(blocks)
