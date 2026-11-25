"""Node 2 (LLM, no skill): scenes -> verbatim breakdown -> data/breakdown.json."""

import logging
from typing import Any, Dict, List

from agent import config
from agent.helpers.json_files import save_json
from agent.helpers.verbatim import check_verbatim, find_dropped_text, shot_pieces
from agent.llm import OpenAILLM
from agent.nodes.retry import Reply, ask_until_valid
from agent.prompts import extract_request
from agent.state import PipelineState

log = logging.getLogger("agent")


def make_extract_breakdown(llm: OpenAILLM):
    def extract_breakdown(state: PipelineState) -> Dict[str, Any]:
        scenes, warnings = [], []
        total = len(state["scenes"])

        for scene in state["scenes"]:
            log.info("Breakdown: scene %d/%d %s", scene["number"], total, scene["heading"])
            reply, problems = ask_until_valid(
                llm,
                extract_request(scene),
                find_problems=lambda r: _breakdown_problems(r, scene["text"]),
            )
            scenes.append(_breakdown_scene(scene, reply.get("shots", [])))
            warnings += [f"breakdown scene {scene['number']}: {p}" for p in problems]

        breakdown = {"source": state["pdf_path"], "scenes": scenes}
        save_json(config.BREAKDOWN_JSON, breakdown)
        return {"breakdown": breakdown, "warnings": warnings}

    return extract_breakdown


def _breakdown_scene(scene: Dict[str, Any], shots: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Give each shot an id like s3-1 (scene 3, shot 1)."""
    for number, shot in enumerate(shots, start=1):
        shot["id"] = f"s{scene['number']}-{number}"
    return {"number": scene["number"], "heading": scene["heading"], "shots": shots}


def _breakdown_problems(reply: Reply, scene_text: str) -> List[str]:
    pieces = shot_pieces(reply.get("shots", []))
    problems = check_verbatim(pieces, scene_text)
    problems += [f"dropped: {text}" for text in find_dropped_text(pieces, scene_text)]
    return problems
