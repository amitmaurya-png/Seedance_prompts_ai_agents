"""Graph wiring: START -> writer -> reviewer -> END."""

from typing import Optional

from langgraph.graph import END, START, StateGraph
from openai import OpenAI

from agent.config import REVIEWER_SKILLS, WRITER_SKILLS, LLMConfig
from agent.llm import OpenAILLM
from agent.nodes import make_reviewer_node, make_writer_node
from agent.state import GraphState

WRITER_NODE = "writer"
REVIEWER_NODE = "reviewer"


def build_graph(
    writer_llm: Optional[OpenAILLM] = None,
    reviewer_llm: Optional[OpenAILLM] = None,
):
    # Both nodes share one OpenAI client but load their own skill files.
    client = OpenAI()
    writer_llm = writer_llm or OpenAILLM(LLMConfig(skills=WRITER_SKILLS), client)
    reviewer_llm = reviewer_llm or OpenAILLM(LLMConfig(skills=REVIEWER_SKILLS), client)

    graph = StateGraph(GraphState)
    graph.add_node(WRITER_NODE, make_writer_node(writer_llm))
    graph.add_node(REVIEWER_NODE, make_reviewer_node(reviewer_llm))
    graph.add_edge(START, WRITER_NODE)
    graph.add_edge(WRITER_NODE, REVIEWER_NODE)
    graph.add_edge(REVIEWER_NODE, END)
    return graph.compile()
