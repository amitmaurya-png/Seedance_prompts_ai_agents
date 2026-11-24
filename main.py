"""Entry point: skit PDF -> breakdown.json -> prompt.json -> curl_commands.json.

    source .venv/bin/activate
    pip install -U -r requirements.txt
    python main.py                 # uses data/TSL.pdf
    python main.py path/to/skit.pdf

Reads OPENAI_API_KEY (and optionally OPENAI_MODEL) from .env.
Per-node skills, paths and MAX_SCENES are set in agent/config.py.
"""

import logging
import sys

from dotenv import load_dotenv

# Load .env before anything creates the OpenAI client.
load_dotenv()

from agent import build_graph, initial_state  # noqa: E402
from agent.config import CURL_JSON, PROMPT_JSON, SKIT_PDF  # noqa: E402


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else str(SKIT_PDF)

    result = build_graph().invoke(initial_state(pdf_path))

    clips = result["clips"]
    commands = result["curl_commands"]["clips"]
    ready = sum(1 for c in commands.values() if not c["missing"])
    print(f"\n{len(clips)} clips, {sum(c['duration_seconds'] for c in clips)} s total")
    print(f"prompt.json:        {PROMPT_JSON}")
    print(f"curl commands:      {CURL_JSON} ({ready}/{len(commands)} ready to send)")

    if result["warnings"]:
        print(f"\n{len(result['warnings'])} warning(s):")
        for warning in result["warnings"]:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
