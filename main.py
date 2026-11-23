"""Entry point.

    source .venv/bin/activate
    pip install -U -r requirements.txt
    python main.py "Your question"

Reads OPENAI_API_KEY (and optionally OPENAI_MODEL) from .env.
Each node's skills are set in agent/config.py (WRITER_SKILLS, REVIEWER_SKILLS).
"""

import sys

from dotenv import load_dotenv

# Load .env before anything creates the OpenAI client.
load_dotenv()

from agent import build_graph, initial_state  # noqa: E402

DEFAULT_QUESTION = "A cat exploring a rainy Tokyo street at night"


def main() -> None:
    question = " ".join(sys.argv[1:]) or DEFAULT_QUESTION
    result = build_graph().invoke(initial_state(question))

    print("=== Draft (writer) ===")
    print(result["draft"])
    print("\n=== Final (reviewer) ===")
    print(result["answer"])


if __name__ == "__main__":
    main()
