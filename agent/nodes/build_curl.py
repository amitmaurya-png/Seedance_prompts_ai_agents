"""Node 9 (code, follows skill: seedance-curl): clips -> curl/curl_commands.json."""

import logging
from typing import Any, Dict

from agent import config
from agent.helpers.json_files import save_json
from agent.helpers.seedance_request import build_request, read_url_file
from agent.state import PipelineState

log = logging.getLogger("agent")


def build_curl(state: PipelineState) -> Dict[str, Any]:
    refs = config.CURL_REFERENCES_DIR
    image_urls = read_url_file(refs / "image_urls")
    audio_urls = read_url_file(refs / "audio_urls")
    last_frames = read_url_file(refs / "last_frames")

    commands = {
        clip["id"]: build_request(clip, image_urls, audio_urls, last_frames, config.SEEDANCE)
        for clip in state["clips"]
    }
    output = {
        "endpoint": config.SEEDANCE.endpoint,
        "model": config.SEEDANCE.model,
        "clips": commands,
    }
    save_json(config.CURL_JSON, output)

    ready = sum(1 for c in commands.values() if not c["missing"])
    log.info("Wrote curl commands to %s (%d/%d ready)", config.CURL_JSON, ready, len(commands))
    return {"curl_commands": output}
