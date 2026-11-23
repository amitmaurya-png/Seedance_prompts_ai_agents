"""Graph nodes. Each node takes the state and returns the fields it updates."""

from typing import Any, Callable, Dict

from agent.llm import OpenAILLM, to_assistant_message
from agent.state import GraphState, latest_user_message

Node = Callable[[GraphState], Dict[str, Any]]


def make_writer_node(llm: OpenAILLM) -> Node:
    """Node 1: answers the conversation and stores the result as a draft."""

    def writer_node(state: GraphState) -> Dict[str, Any]:
        reply = llm.chat(state["messages"])
        return {"draft": reply.content or ""}

    return writer_node


def make_reviewer_node(llm: OpenAILLM) -> Node:
    """Node 2: reviews the draft against the request and returns the final answer."""

    def reviewer_node(state: GraphState) -> Dict[str, Any]:
        review_request = (
            f"Original request:\n{latest_user_message(state)}\n\n"
            f"Draft to review:\n{state['draft']}"
        )
        reply = llm.chat([{"role": "user", "content": review_request}])
        return {
            "messages": [to_assistant_message(reply)],
            "answer": reply.content or "",
        }

    return reviewer_node
