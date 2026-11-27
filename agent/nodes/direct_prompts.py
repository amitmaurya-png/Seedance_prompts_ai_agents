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

import logging

from agent import config
from agent.helpers.checkpoints import ProgressFile, fingerprint
from agent.helpers.clips import clip_profiles, scene_batches
from agent.helpers.json_files import write_prompt_json
from agent.helpers.prompt_repair import prompt_problems, repair_prompt
from agent.llm import OpenAILLM
from agent.prompts import director_request
from agent.retry import ask_for_prompts
from agent.state import Clip, Node, PipelineState, Profile, StateUpdate

log = logging.getLogger("agent")


def make_direct_prompts(llm: OpenAILLM) -> Node:
    def direct_prompts(state: PipelineState) -> StateUpdate:
        clips = state["clips"]
        characters = state.get("characters", {})
        progress = ProgressFile(config.CLIP_PROMPTS_JSON, state["pdf_path"], key="clips")
        profiles = {clip["id"]: clip_profiles(clip, characters) for clip in clips}
        warnings: list[str] = []

        # 1. Reuse saved prompts that still fit.
        todo: list[Clip] = []
        for clip in clips:
            prompt = _saved_prompt(progress, clip, profiles[clip["id"]])
            if prompt:
                clip["prompt"] = prompt
            else:
                todo.append(clip)
        if len(todo) < len(clips):
            log.info(
                "Director: reused %d saved prompt(s) from %s",
                len(clips) - len(todo),
                config.CLIP_PROMPTS_JSON.name,
            )

        # 2. Ask the LLM for the rest, a batch of one scene's clips per call.
        batches = scene_batches(todo, config.DIRECTOR_CLIPS_PER_CALL)
        for number, batch in enumerate(batches, start=1):
            log.info(
                "Director: call %d/%d, %s (%s)",
                number,
                len(batches),
                ", ".join(c["id"] for c in batch),
                batch[0]["scene"],
            )
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


# --- Reuse -------------------------------------------------------------------


def _saved_prompt(progress: ProgressFile, clip: Clip, profiles: list[Profile]) -> str:
    """The saved prompt for this clip if its input is unchanged and it still passes; else ""."""
    entry = progress.saved(clip["id"])
    if not entry or entry.get("input") != _input_key(clip, profiles) or not entry.get("prompt"):
        return ""
    prompt = repair_prompt(entry["prompt"], clip, profiles)
    if prompt_problems(prompt, clip):
        return ""
    progress.keep(clip["id"], entry)
    return prompt


def _input_key(clip: Clip, profiles: list[Profile]) -> str:
    """A fingerprint of everything the clip's prompt is written from."""
    fields = ("scene_setting", "references", "shot_details", "audio", "constraints")
    return fingerprint(
        {
            "clip": {name: clip.get(name) for name in fields},
            "profiles": profiles,
            "style": config.STYLE_LINE,
        }
    )


# --- One LLM call per batch --------------------------------------------------


def _direct_batch(
    llm: OpenAILLM, batch: list[Clip], profiles: dict[str, list[Profile]]
) -> dict[str, tuple[str, list[str]]]:
    """{clip id: (prompt, problems left)} for one batch of one scene's clips."""
    batch_profiles = list({p["name"]: p for c in batch for p in profiles[c["id"]]}.values())
    request = director_request(batch, batch_profiles, config.STYLE_LINE)
    return ask_for_prompts(llm, request, batch, profiles)
