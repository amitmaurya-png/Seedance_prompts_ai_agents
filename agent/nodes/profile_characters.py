"""Node 3 (LLM, skills: acting-system, stylized-3d-film-director):
breakdown -> one acting profile per character -> data/characters.json.

Runs once for the whole skit, so every clip adapts the same profile and the
acting stays consistent across scenes. If data/characters.json already has a
profile for every speaker, it is used and no LLM call is made.
"""

import logging
from typing import Any, Dict, List

from agent import config
from agent.helpers.breakdown_text import script_text, speakers as find_speakers
from agent.helpers.json_files import load_saved, save_json
from agent.llm import OpenAILLM
from agent.nodes.retry import Reply, ask_until_valid
from agent.prompts import profile_request
from agent.state import PipelineState

log = logging.getLogger("agent")


def make_profile_characters(llm: OpenAILLM):
    def profile_characters(state: PipelineState) -> Dict[str, Any]:
        scenes = state["breakdown"]["scenes"]
        speakers = find_speakers(scenes)

        saved = load_saved(config.CHARACTERS_JSON, state["pdf_path"])
        if saved:
            characters = _by_name(saved.get("characters", []))
            missing = [name for name in speakers if name not in characters]
            if not missing:
                log.info("Profiles: using saved %s (no LLM call)", config.CHARACTERS_JSON.name)
                return {"characters": characters}
            log.info("Profiles: saved file has no profile for %s; calling the LLM", ", ".join(missing))

        log.info("Profiles: %d speaking characters", len(speakers))

        reply, problems = ask_until_valid(
            llm,
            profile_request(script_text(scenes), speakers),
            find_problems=lambda r: _profile_problems(r, speakers),
        )
        characters = _by_name(reply.get("characters", []))
        save_json(
            config.CHARACTERS_JSON,
            {"source": state["pdf_path"], "characters": list(characters.values())},
        )
        return {
            "characters": characters,
            "warnings": [f"profiles: {p}" for p in problems],
        }

    return profile_characters


def _by_name(profiles: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {p["name"].strip().upper(): p for p in profiles if p.get("name")}


def _profile_problems(reply: Reply, speakers: List[str]) -> List[str]:
    profiles = {c.get("name", "").strip().upper(): c for c in reply.get("characters", [])}
    problems = [f"no profile for {name}" for name in speakers if name not in profiles]
    for name, profile in profiles.items():
        for field in ("master_profile", "caps_rules", "voice"):
            if not profile.get(field):
                problems.append(f"{name} has no {field}")
    return problems
