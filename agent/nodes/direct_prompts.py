"""Node 6 (LLM, skills: cinedance-director, acting-system, stylized-3d-film-director):
planned clips -> their Seedance 2.0 prompts -> data/prompt.json.

Calls are kept low:
- One call writes the prompts for up to DIRECTOR_CLIPS_PER_CALL clips of the
  same scene, so the skills are sent once per batch and the director sees the
  whole scene at once.
- Mechanical problems are fixed in code (style block, voice prompts, stray
  @Audio/@Video tags, unused @Image references). The LLM is asked again only
  for clips whose dialogue or @Image tags are wrong, and only for those clips.
- After every call, the batch's prompts are saved to data/clip_prompts.json. A
  later run reuses a saved prompt when its clip and acting profiles are
  unchanged and it still passes the checks.
"""

import json
import logging
import math
import re
from typing import Any, Dict, List, Tuple

from agent import config
from agent.helpers.json_files import ProgressFile, fingerprint, write_prompt_json
from agent.helpers.verbatim import check_verbatim, normalize
from agent.llm import OpenAILLM
from agent.prompts import director_fix_request, director_request
from agent.state import PipelineState

log = logging.getLogger("agent")

Clip = Dict[str, Any]
Profile = Dict[str, Any]
IMAGE_TAG = re.compile(r"@Image (\d+)")
OTHER_TAG = re.compile(r"\s*\(?@(?:Video|Audio) \d+\)?")


def make_direct_prompts(llm: OpenAILLM):
    def direct_prompts(state: PipelineState) -> Dict[str, Any]:
        clips = state["clips"]
        characters = state.get("characters", {})
        progress = ProgressFile(config.CLIP_PROMPTS_JSON, state["pdf_path"], key="clips")
        profiles = {clip["id"]: _profiles_in_clip(clip, characters) for clip in clips}
        warnings: List[str] = []

        # Reuse saved prompts that still fit; the rest go to the LLM.
        todo: List[Clip] = []
        for clip in clips:
            entry = progress.saved(clip["id"])
            key = _input_key(clip, profiles[clip["id"]])
            if entry and entry.get("input") == key and entry.get("prompt"):
                prompt = _repair(entry["prompt"], clip, profiles[clip["id"]])
                if not _problems(prompt, clip):
                    clip["prompt"] = prompt
                    progress.keep(clip["id"], entry)
                    continue
            todo.append(clip)
        if len(todo) < len(clips):
            log.info("Director: reused %d saved prompt(s) from %s",
                     len(clips) - len(todo), config.CLIP_PROMPTS_JSON.name)

        batches = _batches(todo)
        for number, batch in enumerate(batches, start=1):
            log.info("Director: call %d/%d, %s (%s)", number, len(batches),
                     ", ".join(c["id"] for c in batch), batch[0]["scene"])
            results = _direct_batch(llm, batch, profiles)
            for clip in batch:
                prompt, problems = results[clip["id"]]
                clip["prompt"] = prompt
                warnings += [f"director {clip['id']}: {p}" for p in problems]
                progress.add(
                    clip["id"],
                    {
                        "scene": clip["scene"],
                        "input": _input_key(clip, profiles[clip["id"]]),
                        "problems": problems,
                        "prompt": prompt,
                    },
                )

        write_prompt_json(
            config.PROMPT_JSON, state["pdf_path"], clips, skills=list(config.DIRECTOR_SKILLS)
        )
        log.info("Wrote %d clips to %s", len(clips), config.PROMPT_JSON)
        return {"clips": clips, "warnings": warnings}

    return direct_prompts


# --- Batching ----------------------------------------------------------------


def _batches(clips: List[Clip]) -> List[List[Clip]]:
    """Consecutive clips of the same scene, split evenly into calls of at most
    DIRECTOR_CLIPS_PER_CALL (10 clips -> 5 + 5)."""
    scenes: List[List[Clip]] = []
    for clip in clips:
        scene = clip.get("scene_number", clip["scene"])
        if scenes and scenes[-1][0].get("scene_number", scenes[-1][0]["scene"]) == scene:
            scenes[-1].append(clip)
        else:
            scenes.append([clip])

    batches = []
    size_limit = max(1, config.DIRECTOR_CLIPS_PER_CALL)
    for scene_clips in scenes:
        count = math.ceil(len(scene_clips) / size_limit)
        size = math.ceil(len(scene_clips) / count)
        batches += [scene_clips[i : i + size] for i in range(0, len(scene_clips), size)]
    return batches


def _direct_batch(
    llm: OpenAILLM, batch: List[Clip], profiles: Dict[str, List[Profile]]
) -> Dict[str, Tuple[str, List[str]]]:
    """Prompts for one batch: one call, then retries only for clips that still fail."""
    by_id = {clip["id"]: clip for clip in batch}
    batch_profiles = list({p["name"]: p for c in batch for p in profiles[c["id"]]}.values())

    messages = [{"role": "user", "content": director_request(batch, batch_profiles, config.STYLE_LINE)}]
    prompts: Dict[str, str] = {}

    def take(reply: Dict[str, Any], ids) -> Dict[str, List[str]]:
        returned = reply.get("prompts") or {}
        for clip_id in ids:
            text = returned.get(clip_id) if isinstance(returned, dict) else None
            if isinstance(text, str) and text.strip():
                prompts[clip_id] = _repair(text.strip(), by_id[clip_id], profiles[clip_id])
        return {
            clip_id: _problems(prompts.get(clip_id, ""), by_id[clip_id])
            for clip_id in ids
        }

    reply = llm.chat_json(messages)
    problems = take(reply, by_id)

    for _ in range(config.VERBATIM_RETRIES):
        failing = {clip_id: found for clip_id, found in problems.items() if found}
        if not failing:
            break
        log.info("  %d clip(s) with problems; asking again for those only", len(failing))
        messages += [
            {"role": "assistant", "content": json.dumps(reply, ensure_ascii=False)},
            {"role": "user", "content": director_fix_request(failing)},
        ]
        reply = llm.chat_json(messages)
        problems.update(take(reply, failing))

    return {clip_id: (prompts.get(clip_id, ""), problems[clip_id]) for clip_id in by_id}


# --- Clip facts --------------------------------------------------------------


def _speakers(clip: Clip) -> List[str]:
    return [
        line.get("character", "").strip().upper()
        for shot in clip["shot_details"]
        for line in shot.get("dialogue", [])
    ]


def _profiles_in_clip(clip: Clip, characters: Dict[str, Profile]) -> List[Profile]:
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


def _input_key(clip: Clip, profiles: List[Profile]) -> str:
    """Everything the clip's prompt is written from; a saved prompt is reused only if it matches."""
    return fingerprint(
        {
            "clip": {k: clip.get(k) for k in ("scene_setting", "references", "shot_details", "audio", "constraints")},
            "profiles": profiles,
            "style": config.STYLE_LINE,
        }
    )


def _voices(clip: Clip, profiles: List[Profile]) -> List[str]:
    """Locked voice prompts of the characters who speak in the clip."""
    speakers = set(_speakers(clip))
    return [
        (p.get("voice") or "").strip()
        for p in profiles
        if p["name"].strip().upper() in speakers and (p.get("voice") or "").strip()
    ]


# --- Repair and checks -------------------------------------------------------


def _repair(prompt: str, clip: Clip, profiles: List[Profile]) -> str:
    """Fix in code what doesn't need the LLM's judgement."""
    prompt = OTHER_TAG.sub("", prompt)

    if normalize(config.STYLE_LINE) not in normalize(prompt):
        prompt = _add_to_section(prompt, "STYLE", config.STYLE_LINE, after_first_block=True)

    used = set(IMAGE_TAG.findall(prompt))
    for ref in clip["references"]:
        if str(ref["n"]) not in used:
            prompt = _add_to_section(prompt, "ACTIVE REFERENCES", f"@Image {ref['n']}: {ref['role']}")

    for voice in _voices(clip, profiles):
        if normalize(voice.strip('"')) not in normalize(prompt):
            prompt = _add_to_section(prompt, "AUDIO", voice)
    return prompt


def _add_to_section(prompt: str, heading: str, line: str, after_first_block: bool = False) -> str:
    """Add a line under a section heading, creating the section if it's missing."""
    lines = prompt.split("\n")
    for index, text in enumerate(lines):
        if text.strip().rstrip(":").upper() == heading:
            lines.insert(index + 1, line)
            return "\n".join(lines)
    blocks = prompt.split("\n\n")
    position = 1 if after_first_block else len(blocks)
    blocks.insert(position, f"{heading}\n{line}")
    return "\n\n".join(blocks)


def _problems(prompt: str, clip: Clip) -> List[str]:
    """What still needs the LLM after `_repair`: wrong dialogue or unknown @Image tags."""
    if not prompt.strip():
        return ["no prompt was returned for this clip"]

    lines = [line["line"] for shot in clip["shot_details"] for line in shot.get("dialogue", [])]
    problems = [f"dialogue {p}" for p in check_verbatim(lines, prompt)]

    expected = {str(r["n"]) for r in clip["references"]}
    unknown = sorted(set(IMAGE_TAG.findall(prompt)) - expected, key=int)
    problems += [f"@Image {n} is not one of this clip's references" for n in unknown]
    return problems
