"""The state that flows through the graph, and names for the dicts inside it."""

import operator
from collections.abc import Callable
from typing import Annotated, Any

from typing_extensions import TypedDict

# The pipeline passes plain JSON-style dicts. These names say which one is meant.
# A scene: {"number", "heading", "text"} from load_skit, or {"number", "heading", "shots"}
# in the breakdown.
Scene = dict[str, Any]
Shot = dict[str, Any]  # {"id", "action", "dialogue": [{"character", "line", ...}], ...}
Clip = dict[str, Any]  # one Seedance generation; see agent/helpers/clips.py
Profile = dict[str, Any]  # one character's acting profile; see profile_characters

# What a node returns: only the state keys it changes.
StateUpdate = dict[str, Any]


class PipelineState(TypedDict, total=False):
    # Input
    pdf_path: str
    # load_skit: [{"number", "heading", "text"}]
    scenes: list[Scene]
    # extract_breakdown: {"source", "scenes": [{"number", "heading", "shots": [...]}]}
    breakdown: dict[str, Any]
    # profile_characters: {CHARACTER NAME: {"name", "master_profile", "caps_rules",
    #                      "forbidden_readings", "voice"}}
    characters: dict[str, Profile]
    # asset_prompts: [{"name", "kind", "model", "platform_settings", "prompt", "notes"}]
    asset_prompts: list[dict[str, Any]]
    # plan_clips -> direct_prompts: the clips of data/prompt.json
    clips: list[Clip]
    # build_curl: {"clips": {clip id: {...}}}
    curl_commands: dict[str, Any]
    # Any node can append; `operator.add` concatenates the lists.
    warnings: Annotated[list[str], operator.add]


# A graph node: reads the state, returns the keys it changes.
Node = Callable[[PipelineState], StateUpdate]


def initial_state(pdf_path: str) -> PipelineState:
    """The state the graph starts from."""
    return {"pdf_path": pdf_path, "warnings": []}
