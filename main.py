"""Entry point.

    source .venv/bin/activate
    pip install -U -r requirements.txt
    python main.py "Your question here"

Reads OPENAI_API_KEY (and optionally OPENAI_MODEL) from .env.
"""

import sys

from dotenv import load_dotenv

# Load .env before anything creates the OpenAI client.
load_dotenv()

from agent import build_graph, initial_state  # noqa: E402

DEFAULT_QUESTION = "Explain LangGraph in two sentences."


def main() -> None:
    question = " ".join(sys.argv[1:]) or DEFAULT_QUESTION
    app = build_graph()
    result = app.invoke(initial_state(question))
    print(result["answer"])


if __name__ == "__main__":
    main()
