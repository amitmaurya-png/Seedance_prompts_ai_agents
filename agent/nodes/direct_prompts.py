"""Node 8 (LLM, skills: cinedance-director, acting-system, stylized-3d-film-director):
each clip's template prompt -> the final Seedance 2.0 prompt -> data/prompt.json.

The template draft is kept in the clip as `template_prompt`. Code checks that
the rewrite keeps the dialogue, the @Image tags, the style line and the voices.
"""

import logging
import re
from typing import Any, Dict, List

from agent import config
from agent.helpers.verbatim import check_verbatim, normalize
from agent.llm import OpenAILLM
from agent.nodes.render_prompts import write_prompt_json
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

        for index, clip in enumerate(clips, start=1):
            log.info("Director: %s (%d/%d)", clip["id"], index, len(clips))
            profiles = _profiles_in_clip(clip, characters)
            reply, problems = ask_until_valid(
                llm,
                director_request(clip, profiles, config.STYLE_LINE),
                find_problems=lambda r: _prompt_problems(r, clip, profiles),
            )
            warnings += [f"director {clip['id']}: {p}" for p in problems]

            prompt = (reply.get("prompt") or "").strip()
            if prompt:
                clip["template_prompt"] = clip["prompt"]
                clip["prompt"] = prompt

        write_prompt_json(state["pdf_path"], clips, skills=list(config.DIRECTOR_SKILLS))
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
        clip.get("subjects", [])
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
