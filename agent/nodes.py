"""Graph nodes. Each node takes the state and returns the fields it updates."""

from typing import Any, Callable, Dict

from agent.llm import OpenAILLM, to_assistant_message
from agent.state import GraphState

Node = Callable[[GraphState], Dict[str, Any]]


def make_llm_node(llm: OpenAILLM) -> Node:
    """Create the node that sends the conversation to the LLM."""

    def llm_node(state: GraphState) -> Dict[str, Any]:
        reply = llm.chat(state["messages"])
        return {
            "messages": [to_assistant_message(reply)],
            "answer": reply.content or "",
        }

    return llm_node
