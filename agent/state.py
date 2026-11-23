"""The state that flows through the graph."""

import operator
from typing import Annotated, Any, Dict, List

from typing_extensions import TypedDict

# A chat message in OpenAI format: {"role": "user" | "assistant", "content": ...}
Message = Dict[str, Any]


class GraphState(TypedDict):
    # `operator.add` appends each node's returned messages to the history.
    messages: Annotated[List[Message], operator.add]
    # First version of the answer, written by the writer node.
    draft: str
    # Final answer, written by the reviewer node.
    answer: str


def initial_state(user_input: str) -> GraphState:
    """Build the starting state for a single user question."""
    return {
        "messages": [{"role": "user", "content": user_input}],
        "draft": "",
        "answer": "",
    }


def latest_user_message(state: GraphState) -> str:
    """Text of the most recent user message in the history."""
    for message in reversed(state["messages"]):
        if message["role"] == "user":
            return message["content"]
    return ""
