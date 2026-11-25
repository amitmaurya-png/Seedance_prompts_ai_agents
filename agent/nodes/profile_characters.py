"""Node 3 (LLM, skills: acting-system, stylized-3d-film-director):
breakdown -> one acting profile per character -> data/characters.json.

One LLM call for the whole skit, so every clip adapts the same profile and the
acting stays consistent across scenes. Reuses data/characters.json when it
already has a profile for every speaker.
"""

import logging
from typing import Any, Dict, List, Optional

from agent import config
from agent.helpers.breakdown_text import script_text, speakers
from agent.helpers.checkpoints import load_saved
from agent.helpers.json_files import save_json
from agent.llm import OpenAILLM
from agent.prompts import profile_request
from agent.retry import Reply, ask_until_valid
from agent.state import PipelineState, Profile

log = logging.getLogger("agent")

REQUIRED_FIELDS = ("master_profile", "caps_rules", "voice")


def make_profile_characters(llm: OpenAILLM):
    def profile_characters(state: PipelineState) -> Dict[str, Any]:
        scenes = state["breakdown"]["scenes"]
        names = speakers(scenes)

        saved = _saved_profiles(state, names)
        if saved is not None:
            log.info("Profiles: using saved %s (no LLM call)", config.CHARACTERS_JSON.name)
            return {"characters": saved}

        log.info("Profiles: %d speaking characters", len(names))
        reply, problems = ask_until_valid(
            llm,
            profile_request(script_text(scenes), names),
            find_problems=lambda reply: _profile_problems(reply, names),
        )
        characters = _by_name(reply.get("characters", []))
        save_json(
            config.CHARACTERS_JSON,
            {"source": state["pdf_path"], "characters": list(characters.values())},
        )
        return {"characters": characters, "warnings": [f"profiles: {p}" for p in problems]}

    return profile_characters


def _saved_profiles(state: PipelineState, names: List[str]) -> Optional[Dict[str, Profile]]:
    """The saved profiles, if there is one for every speaker."""
    saved = load_saved(config.CHARACTERS_JSON, state["pdf_path"])
    if not saved:
        return None
    characters = _by_name(saved.get("characters", []))
    missing = [name for name in names if name not in characters]
    if missing:
        log.info("Profiles: saved file has no profile for %s; calling the LLM", ", ".join(missing))
        return None
    return characters


def _by_name(profiles: List[Profile]) -> Dict[str, Profile]:
    """{"MIRI": {...}}: profiles keyed by upper-case name."""
    return {p["name"].strip().upper(): p for p in profiles if p.get("name")}


def _profile_problems(reply: Reply, names: List[str]) -> List[str]:
    """Speakers without a profile, and profiles missing a required field."""
    profiles = _by_name(reply.get("characters", []))
    problems = [f"no profile for {name}" for name in names if name not in profiles]
    for name, profile in profiles.items():
        problems += [f"{name} has no {field}" for field in REQUIRED_FIELDS if not profile.get(field)]
    return problems
