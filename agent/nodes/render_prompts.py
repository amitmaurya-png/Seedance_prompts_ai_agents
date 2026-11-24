"""Node 5 (code): clips -> each clip's prompt text -> data/prompt.json."""

import logging
from typing import Any, Dict

from agent import config
from agent.helpers.json_files import save_json
from agent.helpers.prompt_template import render_prompt
from agent.state import PipelineState

log = logging.getLogger("agent")


def render_prompts(state: PipelineState) -> Dict[str, Any]:
    clips = state["clips"]
    for clip in clips:
        clip["prompt"] = render_prompt(clip)

    save_json(
        config.PROMPT_JSON,
        {
            "source": state["pdf_path"],
            "skill": "seedance-prompting",
            "syntax": "skills/seedance-prompting/references/prompt_syntax.md",
            "clip_count": len(clips),
            "total_seconds": sum(c["duration_seconds"] for c in clips),
            "clips": clips,
        },
    )
    log.info("Wrote %d clips to %s", len(clips), config.PROMPT_JSON)
    return {"clips": clips}
