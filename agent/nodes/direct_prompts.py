"""Node 6 (LLM, skills: cinedance-director, acting-system, stylized-3d-film-director):
each planned clip -> its Seedance 2.0 prompt -> data/prompt.json.

Code checks that the prompt keeps the dialogue, the @Image tags, the style
line and the voices, and asks again with the problems listed. After every
clip's LLM call, its prompt is saved to data/clip_prompts.json; prompt.json is
written once all clips are done.
"""

import logging
import re
from typing import Any, Dict, List

from agent import config
from agent.helpers.json_files import ProgressFile, write_prompt_json
from agent.helpers.verbatim import check_verbatim, normalize
from agent.llm import OpenAILLM
from agent.nodes.retry import Reply, ask_until_valid
from agent.prompts import director_request
from agent.state import PipelineState

log = logging.getLogger("agent")

Clip = Dict[str, Any]
IMAGE_TAG = re.compile(r"@Image (\d+)")
OTHER_TAG = re.compile(r"@(?:Video|Audio) \d+")


def make_direct_prompts(llm: OpenAILLM):
    def direct_prompts(state: PipelineState) -> Dict[str, Any]:
        clips = state["clips"]
        characters = state.get("characters", {})
        warnings: List[str] = []
        progress = ProgressFile(config.CLIP_PROMPTS_JSON, state["pdf_path"], key="clips")

        for index, clip in enumerate(clips, start=1):
            log.info("Director: %s (%d/%d)", clip["id"], index, len(clips))
            profiles = _profiles_in_clip(clip, characters)
            reply, problems = ask_until_valid(
                llm,
                director_request(clip, profiles, config.STYLE_LINE),
                find_problems=lambda r: _prompt_problems(r, clip, profiles),
            )
            warnings += [f"director {clip['id']}: {p}" for p in problems]

            clip["prompt"] = (reply.get("prompt") or "").strip()
            progress.add(
                clip["id"],
                {"scene": clip["scene"], "problems": problems, "prompt": clip["prompt"]},
            )

        write_prompt_json(
            config.PROMPT_JSON, state["pdf_path"], clips, skills=list(config.DIRECTOR_SKILLS)
        )
        log.info("Wrote %d clips to %s", len(clips), config.PROMPT_JSON)
        return {"clips": clips, "warnings": warnings}

    return direct_prompts


def _speakers(clip: Clip) -> List[str]:
    return [
        line.get("character", "").strip().upper()
        for shot in clip["shot_details"]
        for line in shot.get("dialogue", [])
    ]


def _profiles_in_clip(clip: Clip, characters: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Profiles of characters who speak in the clip or are named in it."""
    text = " ".join(
        [r["role"] for r in clip["references"]]
        + [shot.get("action", "") for shot in clip["shot_details"]]
    ).lower()
    speakers = set(_speakers(clip))
    return [
        profile
        for name, profile in characters.items()
        if name in speakers or re.search(rf"\b{re.escape(name.lower())}\b", text)
    ]


def _prompt_problems(reply: Reply, clip: Clip, profiles: List[Dict[str, Any]]) -> List[str]:
    prompt = reply.get("prompt") or ""
    if not prompt.strip():
        return ["the reply has no prompt"]

    lines = [line["line"] for shot in clip["shot_details"] for line in shot.get("dialogue", [])]
    problems = [f"dialogue {p}" for p in check_verbatim(lines, prompt)]

    expected = {str(r["n"]) for r in clip["references"]}
    used = set(IMAGE_TAG.findall(prompt))
    problems += [f"@Image {n} is never used" for n in sorted(expected - used)]
    problems += [f"@Image {n} is not one of the clip's references" for n in sorted(used - expected)]
    if OTHER_TAG.search(prompt):
        problems.append("remove @Video/@Audio tags; voice references are attached automatically")

    if normalize(config.STYLE_LINE) not in normalize(prompt):
        problems.append(f"the style block is not word for word: {config.STYLE_LINE}")

    speakers = set(_speakers(clip))
    for profile in profiles:
        voice = (profile.get("voice") or "").strip().strip('"')
        if profile["name"].strip().upper() in speakers and voice:
            if normalize(voice) not in normalize(prompt):
                problems.append(f"{profile['name']}'s voice prompt is not pasted word for word")
    return problems
