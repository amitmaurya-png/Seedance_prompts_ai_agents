"""Node 4 (LLM, skills: lira-image-prompts, stylized-3d-film-director):
breakdown -> image prompts for character sheets and location plates
-> data/asset_prompts.json.

One LLM call for the whole skit. Reuses data/asset_prompts.json when it
already has a character sheet for every character.

What to do with the output: generate each image (Soul 2.0, Soul Cinema, NBP ...),
host it, and add its URL under its NAME in skills/seedance-curl/references/image_urls.
The clips then send it as one of their @Image references.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from agent import config
from agent.helpers.breakdown_text import locations, script_text, speakers
from agent.helpers.checkpoints import load_saved
from agent.helpers.json_files import save_json
from agent.helpers.seedance_request import read_url_file
from agent.helpers.verbatim import normalize
from agent.llm import OpenAILLM
from agent.prompts import asset_request
from agent.retry import Reply, ask_until_valid
from agent.state import PipelineState

log = logging.getLogger("agent")

Asset = Dict[str, Any]  # {"name", "kind", "model", "platform_settings", "prompt", "notes"}

# Aspect ratios and resolutions are platform settings; they don't belong in the prompt text.
PLATFORM_TEXT = re.compile(r"--ar\b|\b\d{1,2}:\d{1,2}\b|\b[1-8]k\b", re.IGNORECASE)


def make_asset_prompts(llm: OpenAILLM):
    def asset_prompts(state: PipelineState) -> Dict[str, Any]:
        scenes = state["breakdown"]["scenes"]
        characters = list(dict.fromkeys(speakers(scenes) + list(state.get("characters", {}))))

        saved = _saved_assets(state, characters)
        if saved is not None:
            log.info("Assets: using saved %s (no LLM call)", config.ASSET_PROMPTS_JSON.name)
            return {"asset_prompts": saved}

        places = locations(scenes)
        image_names = sorted(read_url_file(config.CURL_REFERENCES_DIR / "image_urls"))
        log.info("Assets: %d characters, %d locations", len(characters), len(places))
        reply, problems = ask_until_valid(
            llm,
            asset_request(script_text(scenes), characters, places, image_names, config.STYLE_LINE),
            find_problems=lambda reply: _asset_problems(reply, characters),
        )
        assets = reply.get("assets", [])
        save_json(config.ASSET_PROMPTS_JSON, {"source": state["pdf_path"], "assets": assets})
        log.info("Wrote %d asset prompts to %s", len(assets), config.ASSET_PROMPTS_JSON)
        return {"asset_prompts": assets, "warnings": [f"assets: {p}" for p in problems]}

    return asset_prompts


def _saved_assets(state: PipelineState, characters: List[str]) -> Optional[List[Asset]]:
    """The saved asset prompts, if there is a character sheet for every character."""
    saved = load_saved(config.ASSET_PROMPTS_JSON, state["pdf_path"])
    if not saved or not saved.get("assets"):
        return None
    missing = [name for name in characters if name not in _sheet_names(saved["assets"])]
    if missing:
        log.info("Assets: saved file has no sheet for %s; calling the LLM", ", ".join(missing))
        return None
    return saved["assets"]


def _sheet_names(assets: List[Asset]) -> set:
    """Upper-case names of the character sheets among the assets."""
    return {a.get("name", "").strip().upper() for a in assets if a.get("kind") == "character"}


def _asset_problems(reply: Reply, characters: List[str]) -> List[str]:
    """Missing sheets or plates, and prompts without the style block or with platform settings."""
    assets: List[Asset] = reply.get("assets", [])
    sheets = _sheet_names(assets)
    problems = [f"no character sheet for {name}" for name in characters if name not in sheets]
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
        platform_text = PLATFORM_TEXT.search(prompt)
        if platform_text:
            problems.append(f"{name}: move '{platform_text.group()}' to platform_settings")
    return problems
