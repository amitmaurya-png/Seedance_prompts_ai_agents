"""The state that flows through the graph."""

import operator
from typing import Annotated, Any, Dict, List

from typing_extensions import TypedDict

# A chat message in OpenAI format: {"role": "user" | "assistant", "content": ...}
Message = Dict[str, Any]


class GraphState(TypedDict):
    # `operator.add` appends each node's returned messages to the history.
    messages: Annotated[List[Message], operator.add]
    # Plain-text answer from the latest LLM turn.
    answer: str


def initial_state(user_input: str) -> GraphState:
    """Build the starting state for a single user question."""
    return {
        "messages": [{"role": "user", "content": user_input}],
        "answer": "",
    }
