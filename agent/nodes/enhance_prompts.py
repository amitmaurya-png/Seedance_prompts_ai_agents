"""Node 7 (LLM, skill: enhancer-prompt): director prompts -> enhanced prompts
-> data/prompt.json.

A second pass over every clip's finished prompt. The enhancer replaces vague
wording with deterministic locks (FOV, camera speed, timestamps, prop states,
lighting) without changing the story.

- One call enhances up to ENHANCER_CLIPS_PER_CALL clips of the same scene.
- Each enhanced prompt is repaired and checked like a director prompt
  (verbatim dialogue, the clip's own @Image tags, style block, voices). A clip
  whose enhanced prompt still fails after the retries keeps its director
  prompt, with a warning.
- Results are saved to data/enhanced_prompts.json after every call, next to
  the director prompt they came from. A later run reuses a saved prompt when
  the director prompt, the skill and the clip are unchanged.
- Set ENHANCE_PROMPTS = False in agent/config.py to skip this node.
"""

import logging

from agent import config
from agent.helpers.checkpoints import ProgressFile, fingerprint
from agent.helpers.clips import clip_profiles, scene_batches
from agent.helpers.json_files import write_prompt_json
from agent.helpers.prompt_repair import prompt_problems, repair_prompt
from agent.llm import OpenAILLM
from agent.prompts import enhancer_request
from agent.retry import ask_for_prompts
from agent.state import Clip, Node, PipelineState, Profile, StateUpdate

log = logging.getLogger("agent")


def make_enhance_prompts(llm: OpenAILLM) -> Node:
    def enhance_prompts(state: PipelineState) -> StateUpdate:
        clips = state["clips"]
        characters = state.get("characters", {})
        progress = ProgressFile(config.ENHANCED_PROMPTS_JSON, state["pdf_path"], key="clips")
        profiles = {clip["id"]: clip_profiles(clip, characters) for clip in clips}
        # Changing the skill or the enhancer's instructions invalidates saved prompts.
        instructions = fingerprint(llm.system_prompt)
        input_keys = {clip["id"]: _input_key(clip, instructions) for clip in clips}
        warnings: list[str] = []

        # 1. Reuse saved enhanced prompts that still fit.
        todo: list[Clip] = []
        for clip in clips:
            prompt = _saved_prompt(progress, clip, profiles[clip["id"]], input_keys[clip["id"]])
            if prompt:
                clip["prompt"] = prompt
            else:
                todo.append(clip)
        if len(todo) < len(clips):
            log.info(
                "Enhancer: reused %d saved prompt(s) from %s",
                len(clips) - len(todo),
                config.ENHANCED_PROMPTS_JSON.name,
            )

        # 2. Ask the LLM for the rest, a batch of one scene's clips per call.
        batches = scene_batches(todo, config.ENHANCER_CLIPS_PER_CALL)
        for number, batch in enumerate(batches, start=1):
            log.info(
                "Enhancer: call %d/%d, %s (%s)",
                number,
                len(batches),
                ", ".join(c["id"] for c in batch),
                batch[0]["scene"],
            )
            request = enhancer_request(batch, config.STYLE_LINE)
            results = ask_for_prompts(llm, request, batch, profiles)

            for clip in batch:
                enhanced, problems = results[clip["id"]]
                director_prompt = clip["prompt"]
                if problems:
                    warnings += [
                        f"enhancer {clip['id']}: kept the director prompt ({p})" for p in problems
                    ]
                else:
                    clip["prompt"] = enhanced
                progress.add(
                    clip["id"],
                    {
                        "scene": clip["scene"],
                        "input": input_keys[clip["id"]],
                        "problems": problems,
                        "director_prompt": director_prompt,
                        "prompt": enhanced,
                    },
                )

        skills = list(config.DIRECTOR_SKILLS + config.ENHANCER_SKILLS)
        write_prompt_json(config.PROMPT_JSON, state["pdf_path"], clips, skills=skills)
        log.info("Wrote %d enhanced clips to %s", len(clips), config.PROMPT_JSON)
        return {"clips": clips, "warnings": warnings}

    return enhance_prompts


# --- Reuse -------------------------------------------------------------------


def _saved_prompt(
    progress: ProgressFile, clip: Clip, profiles: list[Profile], input_key: str
) -> str:
    """The saved enhanced prompt if its input is unchanged and it still passes; else ""."""
    entry = progress.saved(clip["id"])
    if not entry or entry.get("input") != input_key or not entry.get("prompt"):
        return ""
    prompt = repair_prompt(entry["prompt"], clip, profiles)
    if prompt_problems(prompt, clip):
        return ""
    progress.keep(clip["id"], entry)
    return prompt


def _input_key(clip: Clip, instructions: str) -> str:
    """A fingerprint of everything the enhanced prompt is written from."""
    return fingerprint(
        {
            "director_prompt": clip["prompt"],
            "references": clip["references"],
            "shot_details": clip["shot_details"],
            "style": config.STYLE_LINE,
            "instructions": instructions,
        }
    )
