"""Graph wiring: START -> llm -> END."""

from typing import Optional

from langgraph.graph import END, START, StateGraph

from agent.llm import OpenAILLM
from agent.nodes import make_llm_node
from agent.state import GraphState

LLM_NODE = "llm"


def build_graph(llm: Optional[OpenAILLM] = None):
    llm = llm or OpenAILLM()

    graph = StateGraph(GraphState)
    graph.add_node(LLM_NODE, make_llm_node(llm))
    graph.add_edge(START, LLM_NODE)
    graph.add_edge(LLM_NODE, END)
    return graph.compile()
