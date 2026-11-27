"""The pipeline's nodes, one file each, in run order.

    node                kind  input -> output
    load_skit           code  skit PDF -> scenes
    extract_breakdown   LLM   scenes -> data/breakdown.json
    profile_characters  LLM   breakdown -> data/characters.json
    asset_prompts       LLM   breakdown -> data/asset_prompts.json
    plan_clips          LLM   breakdown -> clips
    direct_prompts      LLM   clips -> prompts, data/prompt.json
    enhance_prompts     LLM   prompts -> enhanced prompts, data/prompt.json
    build_curl          code  clips -> curl/curl_commands.json (follows seedance-curl)

The skills each LLM node loads are listed in agent/config.py.

LLM nodes are built by a make_<name>(llm) factory so each gets its own skills.
"""

from agent.nodes.asset_prompts import make_asset_prompts
from agent.nodes.build_curl import build_curl
from agent.nodes.direct_prompts import make_direct_prompts
from agent.nodes.enhance_prompts import make_enhance_prompts
from agent.nodes.extract_breakdown import make_extract_breakdown
from agent.nodes.load_skit import load_skit
from agent.nodes.plan_clips import make_plan_clips
from agent.nodes.profile_characters import make_profile_characters

__all__ = [
    "build_curl",
    "load_skit",
    "make_asset_prompts",
    "make_direct_prompts",
    "make_enhance_prompts",
    "make_extract_breakdown",
    "make_plan_clips",
    "make_profile_characters",
]
