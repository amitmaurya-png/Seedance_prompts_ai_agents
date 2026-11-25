"""Node 6 (LLM, skills: cinedance-director, acting-system, stylized-3d-film-director):
planned clips -> their Seedance 2.0 prompts -> data/prompt.json.

How it keeps LLM calls low:
- One call writes the prompts for up to DIRECTOR_CLIPS_PER_CALL clips of the
  same scene, so the skills are sent once per batch and the director sees the
  whole scene at once.
- Mechanical problems are fixed in code (agent/helpers/prompt_repair.py). The
  LLM is asked again only for clips whose dialogue or @Image tags are wrong,
  and only for those clips.
- Every batch's prompts are saved to data/clip_prompts.json as soon as they
  arrive. A later run reuses a saved prompt when its clip and acting profiles
  are unchanged and it still passes the checks.
"""

import json
import logging
import math
import re
from typing import Any, Dict, List, Tuple

from agent import config
from agent.helpers.clips import clip_speakers
from agent.helpers.json_files import ProgressFile, fingerprint, write_prompt_json
from agent.helpers.prompt_repair import prompt_problems, repair_prompt
from agent.llm import OpenAILLM
from agent.prompts import director_fix_request, director_request
from agent.state import Clip, PipelineState, Profile

log = logging.getLogger("agent")


def make_direct_prompts(llm: OpenAILLM):
    def direct_prompts(state: PipelineState) -> Dict[str, Any]:
        clips = state["clips"]
        characters = state.get("characters", {})
        progress = ProgressFile(config.CLIP_PROMPTS_JSON, state["pdf_path"], key="clips")
        profiles = {clip["id"]: _profiles_in_clip(clip, characters) for clip in clips}
        warnings: List[str] = []

        # 1. Reuse saved prompts that still fit.
        todo: List[Clip] = []
        for clip in clips:
            prompt = _saved_prompt(progress, clip, profiles[clip["id"]])
            if prompt:
                clip["prompt"] = prompt
            else:
                todo.append(clip)
        if len(todo) < len(clips):
            log.info("Director: reused %d saved prompt(s) from %s",
                     len(clips) - len(todo), config.CLIP_PROMPTS_JSON.name)

        # 2. Ask the LLM for the rest, a batch of one scene's clips per call.
        batches = _batches(todo)
        for number, batch in enumerate(batches, start=1):
            log.info("Director: call %d/%d, %s (%s)", number, len(batches),
                     ", ".join(c["id"] for c in batch), batch[0]["scene"])
            results = _direct_batch(llm, batch, profiles)

            for clip in batch:
                prompt, problems = results[clip["id"]]
                clip["prompt"] = prompt
                warnings += [f"director {clip['id']}: {p}" for p in problems]
                progress.add(clip["id"], {
                    "scene": clip["scene"],
                    "input": _input_key(clip, profiles[clip["id"]]),
                    "problems": problems,
                    "prompt": prompt,
                })

        write_prompt_json(config.PROMPT_JSON, state["pdf_path"], clips,
                          skills=list(config.DIRECTOR_SKILLS))
        log.info("Wrote %d clips to %s", len(clips), config.PROMPT_JSON)
        return {"clips": clips, "warnings": warnings}

    return direct_prompts


# --- Reuse -------------------------------------------------------------------


def _saved_prompt(progress: ProgressFile, clip: Clip, profiles: List[Profile]) -> str:
    """The saved prompt for this clip if its input is unchanged and it still passes; else ""."""
    entry = progress.saved(clip["id"])
    if not entry or entry.get("input") != _input_key(clip, profiles) or not entry.get("prompt"):
        return ""
    prompt = repair_prompt(entry["prompt"], clip, profiles)
    if prompt_problems(prompt, clip):
        return ""
    progress.keep(clip["id"], entry)
    return prompt


def _input_key(clip: Clip, profiles: List[Profile]) -> str:
    """A fingerprint of everything the clip's prompt is written from."""
    fields = ("scene_setting", "references", "shot_details", "audio", "constraints")
    return fingerprint({
        "clip": {name: clip.get(name) for name in fields},
        "profiles": profiles,
        "style": config.STYLE_LINE,
    })


# --- One LLM call per batch --------------------------------------------------


def _batches(clips: List[Clip]) -> List[List[Clip]]:
    """Consecutive clips of the same scene, split evenly into batches of at most
    DIRECTOR_CLIPS_PER_CALL (with 8: 10 clips -> 5 + 5)."""
    scenes: List[List[Clip]] = []
    for clip in clips:
        if scenes and scenes[-1][0].get("scene_number") == clip.get("scene_number"):
            scenes[-1].append(clip)
        else:
            scenes.append([clip])

    batches = []
    limit = max(1, config.DIRECTOR_CLIPS_PER_CALL)
    for scene_clips in scenes:
        size = math.ceil(len(scene_clips) / math.ceil(len(scene_clips) / limit))
        batches += [scene_clips[i : i + size] for i in range(0, len(scene_clips), size)]
    return batches


def _direct_batch(
    llm: OpenAILLM, batch: List[Clip], profiles: Dict[str, List[Profile]]
) -> Dict[str, Tuple[str, List[str]]]:
    """{clip id: (prompt, problems left)} for one batch: one call, then a retry
    for just the clips that still fail."""
    by_id = {clip["id"]: clip for clip in batch}
    batch_profiles = list({p["name"]: p for c in batch for p in profiles[c["id"]]}.values())
    prompts: Dict[str, str] = {}

    def accept(reply: Dict[str, Any], clip_ids) -> Dict[str, List[str]]:
        """Repair and store the returned prompts; return each clip's remaining problems."""
        returned = reply.get("prompts") if isinstance(reply.get("prompts"), dict) else {}
        for clip_id in clip_ids:
            text = returned.get(clip_id)
            if isinstance(text, str) and text.strip():
                prompts[clip_id] = repair_prompt(text.strip(), by_id[clip_id], profiles[clip_id])
        return {clip_id: prompt_problems(prompts.get(clip_id, ""), by_id[clip_id]) for clip_id in clip_ids}

    messages = [{"role": "user", "content": director_request(batch, batch_profiles, config.STYLE_LINE)}]
    reply = llm.chat_json(messages)
    problems = accept(reply, by_id)

    for _ in range(config.RETRIES):
        failing = {clip_id: found for clip_id, found in problems.items() if found}
        if not failing:
            break
        log.info("  %d clip(s) with problems; asking again for those only", len(failing))
        messages += [
            {"role": "assistant", "content": json.dumps(reply, ensure_ascii=False)},
            {"role": "user", "content": director_fix_request(failing)},
        ]
        reply = llm.chat_json(messages)
        problems.update(accept(reply, failing))

    return {clip_id: (prompts.get(clip_id, ""), problems[clip_id]) for clip_id in by_id}


# --- Acting profiles ---------------------------------------------------------


def _profiles_in_clip(clip: Clip, characters: Dict[str, Profile]) -> List[Profile]:
    """Profiles of the characters who speak in the clip or are named in it."""
    text = " ".join(
        [r["role"] for r in clip["references"]]
        + [shot.get("action", "") for shot in clip["shot_details"]]
    ).lower()
    speakers = set(clip_speakers(clip))
    return [
        profile
        for name, profile in characters.items()
        if name in speakers or re.search(rf"\b{re.escape(name.lower())}\b", text)
    ]
