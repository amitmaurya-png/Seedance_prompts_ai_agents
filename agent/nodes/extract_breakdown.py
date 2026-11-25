"""Node 2 (LLM, no skill): scenes -> verbatim breakdown -> data/breakdown.json.

One LLM call per scene splits the scene into shots (action + dialogue), copied
word for word. Reuses data/breakdown.json when it already has every scene.
"""

import logging
from typing import Any, Dict, List, Optional

from agent import config
from agent.helpers.checkpoints import load_saved
from agent.helpers.json_files import save_json
from agent.helpers.verbatim import check_verbatim, find_dropped_text, shot_pieces
from agent.llm import OpenAILLM
from agent.prompts import extract_request
from agent.retry import Reply, ask_until_valid
from agent.state import PipelineState, Scene, Shot

log = logging.getLogger("agent")


def make_extract_breakdown(llm: OpenAILLM):
    def extract_breakdown(state: PipelineState) -> Dict[str, Any]:
        saved = _saved_breakdown(state)
        if saved is not None:
            log.info("Breakdown: using saved %s (no LLM calls)", config.BREAKDOWN_JSON.name)
            return {"breakdown": saved}

        scenes: List[Scene] = []
        warnings: List[str] = []
        for scene in state["scenes"]:
            log.info("Breakdown: scene %d/%d %s", scene["number"], len(state["scenes"]), scene["heading"])
            reply, problems = ask_until_valid(
                llm,
                extract_request(scene),
                find_problems=lambda reply: _breakdown_problems(reply, scene["text"]),
            )
            scenes.append(_breakdown_scene(scene, reply.get("shots", [])))
            warnings += [f"breakdown scene {scene['number']}: {p}" for p in problems]

        breakdown = {"source": state["pdf_path"], "scenes": scenes}
        save_json(config.BREAKDOWN_JSON, breakdown)
        return {"breakdown": breakdown, "warnings": warnings}

    return extract_breakdown


def _saved_breakdown(state: PipelineState) -> Optional[Dict[str, Any]]:
    """The saved breakdown, cut to this run's scenes, if it has all of them."""
    saved = load_saved(config.BREAKDOWN_JSON, state["pdf_path"])
    if not saved:
        return None
    by_number = {scene.get("number"): scene for scene in saved.get("scenes", [])}
    needed = [scene["number"] for scene in state["scenes"]]
    if not all(number in by_number for number in needed):
        log.info("Breakdown: saved file lacks some scenes; calling the LLM")
        return None
    return {"source": saved["source"], "scenes": [by_number[n] for n in needed]}


def _breakdown_scene(scene: Scene, shots: List[Shot]) -> Scene:
    """The scene with its shots, each given an id like s3-1 (scene 3, shot 1)."""
    for number, shot in enumerate(shots, start=1):
        shot["id"] = f"s{scene['number']}-{number}"
    return {"number": scene["number"], "heading": scene["heading"], "shots": shots}


def _breakdown_problems(reply: Reply, scene_text: str) -> List[str]:
    """Text that isn't copied word for word, and story text that was left out."""
    pieces = shot_pieces(reply.get("shots", []))
    problems = check_verbatim(pieces, scene_text)
    problems += [f"dropped: {text}" for text in find_dropped_text(pieces, scene_text)]
    return problems
