"""Graph wiring:

START -> load_skit -> extract_breakdown -> profile_characters -> build_clips
      -> direct_camera -> render_prompts -> direct_prompts -> build_curl -> END
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
    make_build_clips,
    make_direct_camera,
    make_direct_prompts,
    make_extract_breakdown,
    make_profile_characters,
    render_prompts,
)
from agent.state import PipelineState


def build_graph(client: Optional[OpenAI] = None):
    # All LLM nodes share one OpenAI client; each loads only its own skills.
    client = client or OpenAI()

    def llm(system_prompt: str, skills, include_references: bool = True) -> OpenAILLM:
        cfg = LLMConfig(
            system_prompt=system_prompt, skills=skills, include_references=include_references
        )
        return OpenAILLM(cfg, client)

    # Nodes in run order.
    pipeline = [
        ("load_skit", load_skit),
        ("extract_breakdown", make_extract_breakdown(
            llm(prompts.EXTRACT_SYSTEM, config.EXTRACT_SKILLS, include_references=False))),
        ("profile_characters", make_profile_characters(
            llm(prompts.PROFILE_SYSTEM, config.PROFILE_SKILLS))),
        ("build_clips", make_build_clips(llm(prompts.CLIPS_SYSTEM, config.CLIP_SKILLS))),
        ("direct_camera", make_direct_camera(llm(prompts.CAMERA_SYSTEM, config.CAMERA_SKILLS))),
        ("render_prompts", render_prompts),
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
