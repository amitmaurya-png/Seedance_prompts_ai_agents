"""Entry point.

    source .venv/bin/activate
    pip install -U -r requirements.txt
    python main.py "Your question"

Reads OPENAI_API_KEY (and optionally OPENAI_MODEL) from .env.
Which skills load is set by ACTIVE_SKILLS in agent/config.py.
"""

import sys

from dotenv import load_dotenv

# Load .env before anything creates the OpenAI client.
load_dotenv()

from agent import build_graph, initial_state  # noqa: E402
from agent.llm import OpenAILLM  # noqa: E402

DEFAULT_QUESTION = "Explain LangGraph in two sentences."


def main() -> None:
    llm = OpenAILLM()
    print(f"[skills loaded: {', '.join(s.name for s in llm.skills) or 'none'}]")

    question = " ".join(sys.argv[1:]) or DEFAULT_QUESTION
    result = build_graph(llm).invoke(initial_state(question))
    print(result["answer"])


if __name__ == "__main__":
    main()
