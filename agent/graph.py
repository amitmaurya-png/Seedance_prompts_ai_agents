"""Graph wiring:

START -> load_skit -> extract_breakdown -> profile_characters -> asset_prompts
      -> plan_clips -> direct_prompts -> build_curl -> END
"""

from typing import Optional

from langgraph.graph import END, START, StateGraph
from openai import OpenAI

from agent import config, prompts
from agent.config import LLMConfig
from agent.llm import OpenAILLM
from agent.nodes import (
    build_curl,
    load_skit,
    make_asset_prompts,
    make_direct_prompts,
    make_extract_breakdown,
    make_plan_clips,
    make_profile_characters,
)
from agent.state import PipelineState


def build_graph(client: Optional[OpenAI] = None):
    # All LLM nodes share one OpenAI client; each loads only its own skills.
    client = client or OpenAI()

    def llm(system_prompt: str, skills) -> OpenAILLM:
        return OpenAILLM(LLMConfig(system_prompt=system_prompt, skills=skills), client)

    # Nodes in run order.
    pipeline = [
        ("load_skit", load_skit),
        ("extract_breakdown", make_extract_breakdown(
            llm(prompts.EXTRACT_SYSTEM, config.EXTRACT_SKILLS))),
        ("profile_characters", make_profile_characters(
            llm(prompts.PROFILE_SYSTEM, config.PROFILE_SKILLS))),
        ("asset_prompts", make_asset_prompts(
            llm(prompts.ASSET_SYSTEM, config.ASSET_SKILLS))),
        ("plan_clips", make_plan_clips(llm(prompts.PLAN_SYSTEM, config.PLAN_SKILLS))),
        ("direct_prompts", make_direct_prompts(
            llm(prompts.DIRECTOR_SYSTEM, config.DIRECTOR_SKILLS))),
        ("build_curl", build_curl),
    ]

    graph = StateGraph(PipelineState)
    for name, node in pipeline:
        graph.add_node(name, node)

    names = [name for name, _ in pipeline]
    for current, following in zip([START] + names, names + [END]):
        graph.add_edge(current, following)
    return graph.compile()
