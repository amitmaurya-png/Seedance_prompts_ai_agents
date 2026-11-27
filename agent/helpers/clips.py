"""Clip rules that are plain code, not LLM choices.

A clip is one Seedance generation. plan_clips asks the LLM to group a scene's
shots into clips; everything below then makes those clips consistent:

    repair_durations  4-15 s per clip, shot seconds that add up
    finish_clip       id, API params, style, numbered references, constraints,
                      and the hand-off from the previous clip's last frame
    clip_speakers     who speaks in a clip
    clip_lines        what they say
    clip_profiles     the acting profiles of the characters in a clip
    scene_batches     one scene's clips, split evenly for one LLM call each
"""

import copy
import math
import re
from typing import Any

from agent import config
from agent.state import Clip, Profile, Scene

MIN_SECONDS, MAX_SECONDS = 4, 15  # Seedance 2.0 clip length
MAX_SHOTS = 4  # stylized-3d-film-director: at most 4 shots per generation

HANDOFF = (
    "Continue the same moment from @Image {n}: keep the lighting, positions, "
    "props, and character appearance exactly as in that frame"
)
# A hand-off line already in a saved reply, so it is replaced rather than doubled.
OLD_HANDOFF = re.compile(
    r"Continue the same moment from @Image \d+:[^;]*?exactly as in that frame(?:; )?"
)


# --- Who speaks --------------------------------------------------------------


def clip_speakers(clip: Clip) -> list[str]:
    """Characters (upper case) who speak in the clip, in order of their first line."""
    names: list[str] = []
    for line in _dialogue(clip):
        name = line.get("character", "").strip().upper()
        if name and name not in names:
            names.append(name)
    return names


def clip_lines(clip: Clip) -> list[str]:
    """Every spoken line of the clip, in order."""
    return [line["line"] for line in _dialogue(clip)]


def _dialogue(clip: Clip) -> list[dict[str, Any]]:
    return [line for shot in clip.get("shot_details", []) for line in shot.get("dialogue", [])]


def clip_profiles(clip: Clip, characters: dict[str, Profile]) -> list[Profile]:
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


# --- Batches -----------------------------------------------------------------


def scene_batches(clips: list[Clip], limit: int) -> list[list[Clip]]:
    """Consecutive clips of the same scene, split evenly into batches of at most
    `limit` (with 8: 10 clips -> 5 + 5)."""
    scenes: list[list[Clip]] = []
    for clip in clips:
        if scenes and scenes[-1][0].get("scene_number") == clip.get("scene_number"):
            scenes[-1].append(clip)
        else:
            scenes.append([clip])

    batches = []
    limit = max(1, limit)
    for scene_clips in scenes:
        size = math.ceil(len(scene_clips) / math.ceil(len(scene_clips) / limit))
        batches += [scene_clips[i : i + size] for i in range(0, len(scene_clips), size)]
    return batches


# --- Durations ---------------------------------------------------------------


def repair_durations(reply: dict[str, Any]) -> dict[str, Any]:
    """Clamp each planned clip to 4-15 s and rescale its shots' seconds to add up to it."""
    for clip in reply.get("clips") or []:
        shots = clip.get("shot_details") or []
        seconds = round(_number(clip.get("duration_seconds")))
        if not seconds:  # no clip duration given: use the shots' total
            seconds = round(sum(_number(s.get("seconds")) for s in shots))
        seconds = min(max(seconds, MIN_SECONDS), MAX_SECONDS)
        clip["duration_seconds"] = seconds

        if shots and len(shots) <= seconds:
            weights = [_number(s.get("seconds")) for s in shots]
            for shot, shot_seconds in zip(shots, split_seconds(seconds, weights), strict=True):
                shot["seconds"] = shot_seconds
    return reply


def split_seconds(total: int, weights: list[float]) -> list[int]:
    """Split `total` whole seconds in proportion to `weights` (equally if all are 0).

    Every part gets at least 1 s and the parts add up to `total`:
    split_seconds(10, [3, 3]) == [5, 5]; split_seconds(9, [5, 2]) == [6, 3].
    """
    if sum(weights) <= 0:
        weights = [1.0] * len(weights)
    spare = total - len(weights)  # every part gets 1 s first
    shares = [spare * w / sum(weights) for w in weights]
    parts = [1 + int(share) for share in shares]
    # Hand the seconds lost to rounding down to the largest remainders.
    by_remainder = sorted(
        range(len(shares)), key=lambda i: shares[i] - int(shares[i]), reverse=True
    )
    for i in by_remainder[: total - sum(parts)]:
        parts[i] += 1
    return parts


def _number(value: Any) -> float:
    """A non-negative number from whatever the LLM sent (None, "8", 8.0 ...)."""
    try:
        return max(float(value), 0.0)
    except (TypeError, ValueError):
        return 0.0


# --- Finished clips ----------------------------------------------------------


def finish_clip(
    raw: dict[str, Any],
    number: int,
    scene: Scene,
    index_in_scene: int,
    previous_id: str | None,
) -> Clip:
    """Turn one clip from the LLM's plan into a full clip for data/prompt.json."""
    raw = copy.deepcopy(raw)  # the reply is saved as returned; don't change it
    seconds = int(raw.get("duration_seconds") or 8)
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
        "scene_setting": f"{scene['heading']} (@Image {scene_image})"
        if scene_image
        else scene["heading"],
        "shot_details": raw.get("shot_details") or [],
        "audio": raw.get("audio", {}),
        "constraints": list(config.BASE_CONSTRAINTS),
        "continuity": {"mode": "new_scene", "previous_clip": previous_id},
    }

    # Later clips in a scene continue from the previous clip's last frame.
    if index_in_scene > 0:
        _add_handoff(clip, previous_id)

    clip["constraints"] += [c for c in raw.get("constraints", []) if c not in clip["constraints"]]
    return clip


def _number_references(raw: dict[str, Any]) -> tuple[list[dict[str, Any]], int | None]:
    """Number the references 1..N in the order listed (the LLM's own `n` can be
    missing or null). Returns the references and the scene image's new number.
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


def _add_handoff(clip: Clip, previous_id: str | None) -> None:
    """Add the previous clip's last frame as a reference, and tell shot 1 to start from it."""
    frame_n = len(clip["references"]) + 1
    clip["references"].append(
        {"n": frame_n, "role": f"last frame of {previous_id} (continuity reference)"}
    )

    shots = clip["shot_details"]
    if shots:
        note = OLD_HANDOFF.sub("", shots[0].get("continuity", "")).strip()
        handoff = HANDOFF.format(n=frame_n)
        shots[0]["continuity"] = f"{handoff}; {note}" if note else handoff

    clip["constraints"].append(
        f"Match lighting, positions, props, and character appearance to @Image {frame_n}"
    )
    clip["continuity"] = {
        "mode": "continue_scene",
        "previous_clip": previous_id,
        "handoff_image": frame_n,
    }
