"""Graph wiring:

START -> load_skit -> extract_breakdown -> build_clips -> direct_camera
      -> render_prompts -> build_curl -> END
"""

from typing import Optional

from langgraph.graph import END, START, StateGraph
from openai import OpenAI

from agent.config import CAMERA_SKILLS, CLIP_SKILLS, EXTRACT_SKILLS, LLMConfig
from agent.llm import OpenAILLM
from agent.nodes import (
    CAMERA_SYSTEM,
    CLIPS_SYSTEM,
    EXTRACT_SYSTEM,
    build_curl,
    load_skit,
    make_build_clips,
    make_direct_camera,
    make_extract_breakdown,
    render_prompts,
)
from agent.state import PipelineState

PIPELINE = (
    "load_skit",
    "extract_breakdown",
    "build_clips",
    "direct_camera",
    "render_prompts",
    "build_curl",
)


def build_graph(client: Optional[OpenAI] = None):
    # All LLM nodes share one OpenAI client; each loads only its own skills.
    client = client or OpenAI()
    extract_llm = OpenAILLM(LLMConfig(system_prompt=EXTRACT_SYSTEM, skills=EXTRACT_SKILLS,
                                      include_references=False), client)
    clips_llm = OpenAILLM(LLMConfig(system_prompt=CLIPS_SYSTEM, skills=CLIP_SKILLS), client)
    camera_llm = OpenAILLM(LLMConfig(system_prompt=CAMERA_SYSTEM, skills=CAMERA_SKILLS), client)

    nodes = {
        "load_skit": load_skit,
        "extract_breakdown": make_extract_breakdown(extract_llm),
        "build_clips": make_build_clips(clips_llm),
        "direct_camera": make_direct_camera(camera_llm),
        "render_prompts": render_prompts,
        "build_curl": build_curl,
    }

    graph = StateGraph(PipelineState)
    for name in PIPELINE:
        graph.add_node(name, nodes[name])
    graph.add_edge(START, PIPELINE[0])
    for current, following in zip(PIPELINE, PIPELINE[1:]):
        graph.add_edge(current, following)
    graph.add_edge(PIPELINE[-1], END)
    return graph.compile()
