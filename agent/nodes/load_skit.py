"""Node 1 (code): skit PDF -> scenes."""

import logging
from pathlib import Path
from typing import Any, Dict

from agent import config
from agent.helpers.skit_pdf import read_pdf_text, split_scenes
from agent.state import PipelineState

log = logging.getLogger("agent")


def load_skit(state: PipelineState) -> Dict[str, Any]:
    pdf_path = state["pdf_path"]
    scenes = split_scenes(read_pdf_text(Path(pdf_path)))
    if not scenes:
        raise ValueError(f"No INT./EXT. scene headings found in {pdf_path}")

    if config.MAX_SCENES is not None:
        scenes = scenes[: config.MAX_SCENES]
    log.info("Loaded %d scenes from %s", len(scenes), pdf_path)
    return {"scenes": scenes}
