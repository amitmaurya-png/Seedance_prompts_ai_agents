"""Node 5 (LLM, skill: camera-knowledge): clips -> Camera: and Placement: lines."""

import logging
from typing import Any, Dict, List, Tuple

from agent.llm import OpenAILLM
from agent.prompts import camera_request
from agent.state import PipelineState

log = logging.getLogger("agent")

Clip = Dict[str, Any]


def make_direct_camera(llm: OpenAILLM):
    def direct_camera(state: PipelineState) -> Dict[str, Any]:
        clips = state["clips"]
        warnings: List[str] = []

        for heading, scene_clips in _group_by_scene(clips):
            log.info("Camera: %s (%d clips)", heading, len(scene_clips))
            request = camera_request(heading, _shots_for_camera(scene_clips))
            reply = llm.chat_json([{"role": "user", "content": request}])
            warnings += _apply_directions(scene_clips, reply.get("shots", []))

        return {"clips": clips, "warnings": warnings}

    return direct_camera


def _shot_key(clip: Clip, shot_number: int) -> str:
    """e.g. clip-03:2 for the second shot of clip-03."""
    return f"{clip['id']}:{shot_number}"


def _group_by_scene(clips: List[Clip]) -> List[Tuple[str, List[Clip]]]:
    """Consecutive clips with the same scene heading, in order."""
    groups: List[Tuple[str, List[Clip]]] = []
    for clip in clips:
        if groups and groups[-1][0] == clip["scene"]:
            groups[-1][1].append(clip)
        else:
            groups.append((clip["scene"], [clip]))
    return groups


def _shots_for_camera(clips: List[Clip]) -> List[Dict[str, Any]]:
    """What the camera step needs to see for each shot."""
    shots = []
    for clip in clips:
        for number, shot in enumerate(clip["shot_details"], start=1):
            shots.append(
                {
                    "key": _shot_key(clip, number),
                    "title": shot.get("title", ""),
                    "action": shot.get("action", ""),
                    "dialogue": [
                        f"{d.get('character')} to {d.get('addressee') or '?'}: {d.get('line')}"
                        for d in shot.get("dialogue", [])
                    ],
                }
            )
    return shots


def _apply_directions(clips: List[Clip], directions: List[Dict[str, Any]]) -> List[str]:
    """Write camera, placement and reason into each shot. Returns warnings."""
    by_key = {d.get("key"): d for d in directions}
    warnings = []
    for clip in clips:
        for number, shot in enumerate(clip["shot_details"], start=1):
            direction = by_key.get(_shot_key(clip, number))
            if not direction:
                warnings.append(f"camera: no direction returned for {_shot_key(clip, number)}")
                continue
            shot["camera"] = direction.get("camera", "")
            shot["placement"] = direction.get("placement", "")
            shot["camera_reason"] = direction.get("reason", "")
    return warnings
