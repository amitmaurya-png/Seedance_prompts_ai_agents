"""Node 5 (LLM, skill: stylized-3d-film-director): breakdown -> clips.

The LLM groups each scene's shots into clips (at most 4 shots, 4-15 s). Fixed
fields (id, style, base constraints, continuity hand-off, API params) are added
in code by `finish_clip`.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from agent import config
from agent.helpers.seedance_request import read_url_file
from agent.helpers.verbatim import check_verbatim, shot_pieces
from agent.llm import OpenAILLM
from agent.nodes.retry import Reply, ask_until_valid
from agent.prompts import plan_request
from agent.state import PipelineState

log = logging.getLogger("agent")

Clip = Dict[str, Any]
MAX_SHOTS = 4  # stylized-3d-film-director: at most 4 shots per generation


def make_plan_clips(llm: OpenAILLM):
    def plan_clips(state: PipelineState) -> Dict[str, Any]:
        image_names = sorted(read_url_file(config.CURL_REFERENCES_DIR / "image_urls"))
        clips: List[Clip] = []
        warnings: List[str] = []

        for scene in state["breakdown"]["scenes"]:
            log.info("Clips: scene %d %s", scene["number"], scene["heading"])
            reply, problems = ask_until_valid(
                llm,
                plan_request(scene, image_names),
                find_problems=lambda r: _clip_problems(r, scene),
            )
            warnings += [f"clips scene {scene['number']}: {p}" for p in problems]

            for index_in_scene, raw in enumerate(reply.get("clips", [])):
                previous_id = clips[-1]["id"] if clips else None
                clips.append(finish_clip(raw, len(clips) + 1, scene, index_in_scene, previous_id))

        return {"clips": clips, "warnings": warnings}

    return plan_clips


# --- Checks ------------------------------------------------------------------


def _clip_problems(reply: Reply, scene: Dict[str, Any]) -> List[str]:
    """Breakdown text missing from the clips, text changed or added, and size limits."""
    clips = reply.get("clips", [])
    clip_pieces = [p for clip in clips for p in shot_pieces(clip.get("shot_details", []))]
    breakdown_pieces = shot_pieces(scene["shots"])

    problems = [f"missing, {p}" for p in check_verbatim(breakdown_pieces, " ".join(clip_pieces))]
    problems += [f"changed or added, {p}" for p in check_verbatim(clip_pieces, " ".join(breakdown_pieces))]

    for clip in clips:
        seconds = clip.get("duration_seconds", 0)
        if not 4 <= seconds <= 15:
            problems.append(f"clip {clip.get('source')} is {seconds}s (must be 4-15)")
        shots = clip.get("shot_details", [])
        if not 1 <= len(shots) <= MAX_SHOTS:
            problems.append(f"clip {clip.get('source')} has {len(shots)} shots (must be 1-{MAX_SHOTS})")
        shot_seconds = sum(s.get("seconds", 0) for s in shots)
        if shot_seconds != seconds:
            problems.append(
                f"clip {clip.get('source')}: shots add up to {shot_seconds}s, not {seconds}s"
            )
    return problems


# --- Fixed fields ------------------------------------------------------------


def finish_clip(
    raw: Clip,
    number: int,
    scene: Dict[str, Any],
    index_in_scene: int,
    previous_id: Optional[str],
) -> Clip:
    seconds = int(raw.get("duration_seconds") or 8)
    shots = raw.get("shot_details") or []
    references, scene_image = _number_references(raw)

    clip: Clip = {
        "id": f"clip-{number:02d}",
        "scene": scene["heading"],
        "source": raw.get("source", []),
        "duration_seconds": seconds,
        "api_params": {
            "model": config.SEEDANCE.model,
            "ratio": config.SEEDANCE.ratio,
            "duration": seconds,
            "return_last_frame": config.SEEDANCE.return_last_frame,
        },
        "style": config.STYLE_LINE,
        "references": references,
        "scene_setting": f"{scene['heading']} (@Image {scene_image})" if scene_image else scene["heading"],
        "shot_details": shots,
        "audio": raw.get("audio", {}),
        "constraints": list(config.BASE_CONSTRAINTS),
        "continuity": {"mode": "new_scene", "previous_clip": previous_id},
    }

    # Later clips in a scene continue from the previous clip's last frame.
    if index_in_scene > 0:
        _add_handoff(clip, previous_id)

    clip["constraints"] += [c for c in raw.get("constraints", []) if c not in clip["constraints"]]
    return clip


def _number_references(raw: Clip) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    """Number the references 1..N in the order listed; the model's `n` can be
    missing or null. Returns the references and the scene image's new number.
    """
    refs = [r for r in raw.get("references") or [] if isinstance(r, dict) and r.get("role")]

    numbered, old_to_new = [], {}
    for new_n, ref in enumerate(refs, start=1):
        if isinstance(ref.get("n"), int):
            old_to_new[ref["n"]] = new_n
        numbered.append({"n": new_n, "role": ref["role"]})

    scene_image = old_to_new.get(raw.get("scene_image"))
    if scene_image is None:  # fall back to the reference named as the scene
        scene_image = next((r["n"] for r in numbered if "scene" in r["role"].lower()), None)
    return numbered, scene_image


def _add_handoff(clip: Clip, previous_id: Optional[str]) -> None:
    """Add the last-frame image, shot 1's Continuity line, and the match constraint."""
    frame_n = len(clip["references"]) + 1
    clip["references"].append(
        {"n": frame_n, "role": f"last frame of {previous_id} (continuity reference)"}
    )

    handoff = (
        f"Continue the same moment from @Image {frame_n}: keep the lighting, positions, "
        "props, and character appearance exactly as in that frame"
    )
    shots = clip["shot_details"]
    if shots:
        note = shots[0].get("continuity", "")
        shots[0]["continuity"] = f"{handoff}; {note}" if note else handoff

    clip["constraints"].append(
        f"Match lighting, positions, props, and character appearance to @Image {frame_n}"
    )
    clip["continuity"] = {
        "mode": "continue_scene",
        "previous_clip": previous_id,
        "handoff_image": frame_n,
    }
