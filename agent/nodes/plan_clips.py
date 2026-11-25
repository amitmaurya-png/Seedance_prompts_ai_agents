"""Node 5 (LLM, skill: stylized-3d-film-director): breakdown -> clips.

For each scene, the LLM groups its shots into clips (1-4 shots, 4-15 s each).
Code then repairs the durations and adds the fixed fields (agent/helpers/clips.py).

Every scene's result is saved to data/clip_plans.json as soon as it's done. A
later run reuses a saved scene when its breakdown is unchanged and the plan
still passes the checks, so only new or failed scenes cost an LLM call.
"""

import logging
from typing import Any, Dict, List, Optional

from agent import config
from agent.helpers.checkpoints import ProgressFile, fingerprint
from agent.helpers.clips import MAX_SECONDS, MAX_SHOTS, MIN_SECONDS, finish_clip, repair_durations
from agent.helpers.seedance_request import read_url_file
from agent.helpers.verbatim import check_verbatim, shot_pieces
from agent.llm import OpenAILLM
from agent.prompts import plan_request
from agent.retry import Reply, ask_until_valid
from agent.state import Clip, PipelineState, Scene

log = logging.getLogger("agent")


def make_plan_clips(llm: OpenAILLM):
    def plan_clips(state: PipelineState) -> Dict[str, Any]:
        image_names = sorted(read_url_file(config.CURL_REFERENCES_DIR / "image_urls"))
        progress = ProgressFile(config.CLIP_PLANS_JSON, state["pdf_path"], key="scenes")
        clips: List[Clip] = []
        warnings: List[str] = []
        reused = 0

        for scene in state["breakdown"]["scenes"]:
            scene_id = str(scene["number"])
            shots_hash = fingerprint(scene["shots"])

            # 1. The plan: reuse the saved one if it still fits, else ask the LLM.
            plan = _saved_plan(progress.saved(scene_id), scene, shots_hash)
            was_saved = plan is not None
            if was_saved:
                problems: List[str] = []
                reused += 1
            else:
                log.info("Clips: scene %d %s", scene["number"], scene["heading"])
                plan, problems = ask_until_valid(
                    llm,
                    plan_request(scene, image_names),
                    find_problems=lambda reply: _plan_problems(reply, scene),
                    repair=repair_durations,
                )
                warnings += [f"clips scene {scene['number']}: {p}" for p in problems]

            # 2. Full clips, numbered across the whole skit.
            scene_clips = _finish_scene(plan, scene, first_number=len(clips) + 1,
                                        previous_id=clips[-1]["id"] if clips else None)
            clips += scene_clips

            # 3. Checkpoint: write new plans now; a reused one is already in the file.
            entry = {
                "heading": scene["heading"],
                "shots_hash": shots_hash,
                "problems": problems,
                "reply": plan,  # the LLM's plan, durations repaired
                "clips": scene_clips,  # the same clips after finish_clip
            }
            if was_saved:
                progress.keep(scene_id, entry)
            else:
                progress.add(scene_id, entry)

        if reused:
            log.info("Clips: reused %d saved scene(s) from %s", reused, config.CLIP_PLANS_JSON.name)
        return {"clips": clips, "warnings": warnings}

    return plan_clips


def _finish_scene(plan: Reply, scene: Scene, first_number: int, previous_id: Optional[str]) -> List[Clip]:
    """The scene's planned clips as full clips; each later clip hands off from the one before."""
    clips: List[Clip] = []
    for index_in_scene, raw in enumerate(plan.get("clips", [])):
        clips.append(finish_clip(raw, first_number + index_in_scene, scene, index_in_scene, previous_id))
        previous_id = clips[-1]["id"]
    return clips


# --- Reuse -------------------------------------------------------------------


def _saved_plan(entry: Optional[Dict[str, Any]], scene: Scene, shots_hash: str) -> Optional[Reply]:
    """The saved plan for this scene, if the scene is unchanged and the plan still passes.

    Entries saved before `shots_hash` existed are checked against the breakdown
    instead (the verbatim check catches a changed scene).
    """
    if not entry or entry.get("heading") != scene["heading"] or not entry.get("reply"):
        return None
    if entry.get("shots_hash") not in (None, shots_hash):
        return None
    plan = repair_durations(entry["reply"])
    return None if _plan_problems(plan, scene) else plan


# --- Checks ------------------------------------------------------------------


def _plan_problems(reply: Reply, scene: Scene) -> List[str]:
    """Breakdown text missing from the clips, text changed or added, and size limits."""
    clips = reply.get("clips", [])
    clip_pieces = [p for clip in clips for p in shot_pieces(clip.get("shot_details", []))]
    breakdown_pieces = shot_pieces(scene["shots"])

    problems = [f"missing, {p}" for p in check_verbatim(breakdown_pieces, " ".join(clip_pieces))]
    problems += [f"changed or added, {p}" for p in check_verbatim(clip_pieces, " ".join(breakdown_pieces))]

    for clip in clips:
        name = f"clip {clip.get('source')}"
        seconds = clip.get("duration_seconds", 0)
        shots = clip.get("shot_details", [])
        shot_seconds = sum(s.get("seconds", 0) for s in shots)

        if not MIN_SECONDS <= seconds <= MAX_SECONDS:
            problems.append(f"{name} is {seconds}s (must be {MIN_SECONDS}-{MAX_SECONDS})")
        if not 1 <= len(shots) <= MAX_SHOTS:
            problems.append(f"{name} has {len(shots)} shots (must be 1-{MAX_SHOTS})")
        if shot_seconds != seconds:
            problems.append(f"{name}: shots add up to {shot_seconds}s, not {seconds}s")
    return problems
