"""Node 7 (code): clips -> each clip's template prompt text -> data/prompt.json.

direct_prompts then rewrites these drafts and saves prompt.json again.
"""

import logging
from typing import Any, Dict, List

from agent import config
from agent.helpers.json_files import save_json
from agent.helpers.prompt_template import render_prompt
from agent.state import PipelineState

log = logging.getLogger("agent")


def render_prompts(state: PipelineState) -> Dict[str, Any]:
    clips = state["clips"]
    for clip in clips:
        clip["prompt"] = render_prompt(clip)

    write_prompt_json(state["pdf_path"], clips, skills=["seedance-prompting"])
    return {"clips": clips}


def write_prompt_json(pdf_path: str, clips: List[Dict[str, Any]], skills: List[str]) -> None:
    save_json(
        config.PROMPT_JSON,
        {
            "source": pdf_path,
            "skills": skills,
            "clip_count": len(clips),
            "total_seconds": sum(c["duration_seconds"] for c in clips),
            "clips": clips,
        },
    )
    log.info("Wrote %d clips to %s", len(clips), config.PROMPT_JSON)
