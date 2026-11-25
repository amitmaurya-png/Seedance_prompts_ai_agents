"""The pipeline's nodes, one file each, in run order.

    load_skit           code   skit PDF -> scenes
    extract_breakdown   LLM    scenes -> data/breakdown.json          (skit-to-prompt-json)
    profile_characters  LLM    breakdown -> data/characters.json      (acting-system, stylized-3d-film-director)
    build_clips         LLM    breakdown -> clips                     (skit-to-prompt-json, seedance-prompting)
    direct_camera       LLM    clips -> Camera: and Placement: lines  (camera-knowledge)
    render_prompts      code   clips -> template prompt drafts
    direct_prompts      LLM    drafts -> final prompts, data/prompt.json
                               (cinedance-director, acting-system, stylized-3d-film-director)
    build_curl          code   clips -> curl/curl_commands.json       (seedance-curl rules)

LLM nodes are built by a make_<name>(llm) factory so each gets its own skills.
"""

from agent.nodes.build_clips import make_build_clips
from agent.nodes.build_curl import build_curl
from agent.nodes.direct_camera import make_direct_camera
from agent.nodes.direct_prompts import make_direct_prompts
from agent.nodes.extract_breakdown import make_extract_breakdown
from agent.nodes.load_skit import load_skit
from agent.nodes.profile_characters import make_profile_characters
from agent.nodes.render_prompts import render_prompts

__all__ = [
    "build_curl",
    "load_skit",
    "make_build_clips",
    "make_direct_camera",
    "make_direct_prompts",
    "make_extract_breakdown",
    "make_profile_characters",
    "render_prompts",
]
