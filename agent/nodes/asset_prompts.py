"""Node 4 (LLM, skills: lira-image-prompts, stylized-3d-film-director):
breakdown -> image prompts for character sheets and location plates
-> data/asset_prompts.json.

If data/asset_prompts.json already exists for this skit, it is used and no
LLM call is made.

Generate these images (Soul 2.0, Soul Cinema, NBP ...), host them, and add each
one's URL under its NAME in skills/seedance-curl/references/image_urls. The
clips then send them as their @Image references.
"""

import logging
import re
from typing import Any, Dict, List

from agent import config
from agent.helpers.breakdown_text import locations, script_text, speakers
from agent.helpers.json_files import load_saved, save_json
from agent.helpers.seedance_request import read_url_file
from agent.helpers.verbatim import normalize
from agent.llm import OpenAILLM
from agent.nodes.retry import Reply, ask_until_valid
from agent.prompts import asset_request
from agent.state import PipelineState

log = logging.getLogger("agent")

# Aspect ratios and resolutions belong in platform settings, not prompt text.
PLATFORM_TEXT = re.compile(r"--ar\b|\b\d{1,2}:\d{1,2}\b|\b[1-8]k\b", re.IGNORECASE)


def make_asset_prompts(llm: OpenAILLM):
    def asset_prompts(state: PipelineState) -> Dict[str, Any]:
        scenes = state["breakdown"]["scenes"]
        characters = list(dict.fromkeys(speakers(scenes) + list(state.get("characters", {}))))

        saved = load_saved(config.ASSET_PROMPTS_JSON, state["pdf_path"])
        if saved and saved.get("assets"):
            sheets = {a.get("name", "").strip().upper() for a in saved["assets"] if a.get("kind") == "character"}
            missing = [name for name in characters if name not in sheets]
            if not missing:
                log.info("Assets: using saved %s (no LLM call)", config.ASSET_PROMPTS_JSON.name)
                return {"asset_prompts": saved["assets"]}
            log.info("Assets: saved file has no sheet for %s; calling the LLM", ", ".join(missing))

        places = locations(scenes)
        image_names = sorted(read_url_file(config.CURL_REFERENCES_DIR / "image_urls"))
        log.info("Assets: %d characters, %d locations", len(characters), len(places))

        reply, problems = ask_until_valid(
            llm,
            asset_request(script_text(scenes), characters, places, image_names, config.STYLE_LINE),
            find_problems=lambda r: _asset_problems(r, characters),
        )
        assets = reply.get("assets", [])
        save_json(config.ASSET_PROMPTS_JSON, {"source": state["pdf_path"], "assets": assets})
        log.info("Wrote %d asset prompts to %s", len(assets), config.ASSET_PROMPTS_JSON)
        return {"asset_prompts": assets, "warnings": [f"assets: {p}" for p in problems]}

    return asset_prompts


def _asset_problems(reply: Reply, characters: List[str]) -> List[str]:
    assets: List[Dict[str, Any]] = reply.get("assets", [])
    named = {a.get("name", "").strip().upper() for a in assets if a.get("kind") == "character"}
    problems = [f"no character sheet for {name}" for name in characters if name not in named]
    if not any(a.get("kind") == "location" for a in assets):
        problems.append("no location plates")

    style = normalize(config.STYLE_LINE)
    for asset in assets:
        name, prompt = asset.get("name", "?"), asset.get("prompt", "")
        if not prompt.strip():
            problems.append(f"{name} has no prompt")
            continue
        if style not in normalize(prompt):
            problems.append(f"{name}: the style block is not word for word")
        found = PLATFORM_TEXT.search(prompt)
        if found:
            problems.append(f"{name}: move '{found.group()}' to platform_settings")
    return problems
