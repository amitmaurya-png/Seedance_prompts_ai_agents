"""Node 5 (LLM, skill: stylized-3d-film-director): breakdown -> clips.

The LLM groups each scene's shots into clips (at most 4 shots, 4-15 s). Fixed
fields (id, style, base constraints, continuity hand-off, API params) are added
in code by `finish_clip`.

Calls are kept low:
- Durations are repaired in code (clamped to 4-15 s, shot seconds rescaled to
  add up), so the LLM is asked again only for text or shot-count problems.
- After every scene's LLM call, its reply is saved to data/clip_plans.json. A
  later run reuses a saved scene when its breakdown is unchanged and the reply
  still passes the checks, so only new or failed scenes cost a call.
"""

import copy
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from agent import config
from agent.helpers.json_files import ProgressFile, fingerprint
from agent.helpers.seedance_request import read_url_file
from agent.helpers.verbatim import check_verbatim, shot_pieces
from agent.llm import OpenAILLM
from agent.nodes.retry import Reply, ask_until_valid
from agent.prompts import plan_request
from agent.state import PipelineState

log = logging.getLogger("agent")

Clip = Dict[str, Any]
MAX_SHOTS = 4  # stylized-3d-film-director: at most 4 shots per generation
OLD_HANDOFF = re.compile(r"Continue the same moment from @Image \d+:[^;]*?exactly as in that frame(?:; )?")


def make_plan_clips(llm: OpenAILLM):
    def plan_clips(state: PipelineState) -> Dict[str, Any]:
        image_names = sorted(read_url_file(config.CURL_REFERENCES_DIR / "image_urls"))
        clips: List[Clip] = []
        warnings: List[str] = []
        progress = ProgressFile(config.CLIP_PLANS_JSON, state["pdf_path"], key="scenes")

        reused = 0

        for scene in state["breakdown"]["scenes"]:
            scene_id = str(scene["number"])
            shots_hash = fingerprint(scene["shots"])
            reply = _saved_reply(progress.saved(scene_id), scene, shots_hash)
            was_reused = reply is not None
            if was_reused:
                problems: List[str] = []
                reused += 1
            else:
                log.info("Clips: scene %d %s", scene["number"], scene["heading"])
                reply, problems = ask_until_valid(
                    llm,
                    plan_request(scene, image_names),
                    find_problems=lambda r: _clip_problems(r, scene),
                    repair=_repair_durations,
                )
                warnings += [f"clips scene {scene['number']}: {p}" for p in problems]

            first_new = len(clips)
            for index_in_scene, raw in enumerate(reply.get("clips", [])):
                previous_id = clips[-1]["id"] if clips else None
                clips.append(finish_clip(raw, len(clips) + 1, scene, index_in_scene, previous_id))

            entry = {
                "heading": scene["heading"],
                "shots_hash": shots_hash,
                "problems": problems,
                "reply": reply,  # the LLM's clips, as returned (durations repaired)
                "clips": clips[first_new:],  # the same clips after finish_clip
            }
            if was_reused:
                progress.keep(scene_id, entry)  # already in the file; no rewrite
            else:
                progress.add(scene_id, entry)

        if reused:
            log.info("Clips: reused %d saved scene(s) from %s", reused, config.CLIP_PLANS_JSON.name)

        return {"clips": clips, "warnings": warnings}

    return plan_clips


# --- Reuse and repair --------------------------------------------------------


def _saved_reply(entry: Optional[Dict[str, Any]], scene: Dict[str, Any], shots_hash: str) -> Optional[Reply]:
    """The saved reply for this scene, if its input is unchanged and it still passes.

    Entries saved before `shots_hash` existed are checked against the
    breakdown instead (the verbatim check catches a changed scene).
    """
    if not entry or entry.get("heading") != scene["heading"] or not entry.get("reply"):
        return None
    if entry.get("shots_hash") not in (None, shots_hash):
        return None
    reply = _repair_durations(entry["reply"])
    return None if _clip_problems(reply, scene) else reply


def _repair_durations(reply: Reply) -> Reply:
    """Clamp each clip to 4-15 s and rescale its shots' seconds to add up to it."""
    for clip in reply.get("clips") or []:
        shots = clip.get("shot_details") or []
        try:
            seconds = int(round(float(clip.get("duration_seconds") or 0)))
        except (TypeError, ValueError):
            seconds = 0
        if not seconds:  # no clip duration: use the shots' total
            seconds = int(sum(_number(s.get("seconds")) for s in shots))
        seconds = min(max(seconds, 4), 15)
        clip["duration_seconds"] = seconds
        if shots and len(shots) <= seconds:
            for shot, shot_seconds in zip(shots, _split(seconds, [_number(s.get("seconds")) for s in shots])):
                shot["seconds"] = shot_seconds
    return reply


def _number(value: Any) -> float:
    try:
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        return 0.0


def _split(total: int, weights: List[float]) -> List[int]:
    """Whole seconds in proportion to weights (equal if none), each at least 1, summing to total."""
    if sum(weights) <= 0:
        weights = [1.0] * len(weights)
    spare = total - len(weights)  # every shot gets 1 s first
    shares = [spare * w / sum(weights) for w in weights]
    parts = [1 + int(share) for share in shares]
    by_remainder = sorted(range(len(shares)), key=lambda i: shares[i] - int(shares[i]), reverse=True)
    for i in by_remainder[: total - sum(parts)]:
        parts[i] += 1
    return parts


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
    raw = copy.deepcopy(raw)  # the reply is saved as returned; don't change it
    seconds = int(raw.get("duration_seconds") or 8)
    shots = raw.get("shot_details") or []
    references, scene_image = _number_references(raw)

    clip: Clip = {
        "id": f"clip-{number:02d}",
        "scene": scene["heading"],
        "scene_number": scene["number"],
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
        # Saved replies may already carry a hand-off line; replace it.
        note = OLD_HANDOFF.sub("", shots[0].get("continuity", "")).strip()
        shots[0]["continuity"] = f"{handoff}; {note}" if note else handoff

    clip["constraints"].append(
        f"Match lighting, positions, props, and character appearance to @Image {frame_n}"
    )
    clip["continuity"] = {
        "mode": "continue_scene",
        "previous_clip": previous_id,
        "handoff_image": frame_n,
    }
