"""The state that flows through the graph."""

import operator
from typing import Annotated, Any, Dict, List

from typing_extensions import TypedDict


class PipelineState(TypedDict, total=False):
    # Input
    pdf_path: str
    # load_skit: [{"number", "heading", "text"}]
    scenes: List[Dict[str, Any]]
    # extract_breakdown: {"source", "scenes": [{"number", "heading", "shots": [...]}]}
    breakdown: Dict[str, Any]
    # profile_characters: {CHARACTER NAME: {"name", "master_profile", "caps_rules",
    #                      "forbidden_readings", "voice"}}
    characters: Dict[str, Dict[str, Any]]
    # asset_prompts: [{"name", "kind", "model", "platform_settings", "prompt", "notes"}]
    asset_prompts: List[Dict[str, Any]]
    # plan_clips -> direct_prompts: the clips of data/prompt.json
    clips: List[Dict[str, Any]]
    # build_curl: {"clips": {clip id: {...}}}
    curl_commands: Dict[str, Any]
    # Any node can append; `operator.add` concatenates the lists.
    warnings: Annotated[List[str], operator.add]


def initial_state(pdf_path: str) -> PipelineState:
    return {"pdf_path": pdf_path, "warnings": []}
