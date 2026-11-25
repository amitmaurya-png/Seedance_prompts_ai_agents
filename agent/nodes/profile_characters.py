"""Node 3 (LLM, skills: acting-system, stylized-3d-film-director):
breakdown -> one acting profile per character -> data/characters.json.

Runs once for the whole skit, so every clip adapts the same profile and the
acting stays consistent across scenes.
"""

import logging
from typing import Any, Dict, List

from agent import config
from agent.helpers.breakdown_text import script_text, speakers as find_speakers
from agent.helpers.json_files import save_json
from agent.llm import OpenAILLM
from agent.nodes.retry import Reply, ask_until_valid
from agent.prompts import profile_request
from agent.state import PipelineState

log = logging.getLogger("agent")


def make_profile_characters(llm: OpenAILLM):
    def profile_characters(state: PipelineState) -> Dict[str, Any]:
        scenes = state["breakdown"]["scenes"]
        speakers = find_speakers(scenes)
        log.info("Profiles: %d speaking characters", len(speakers))

        reply, problems = ask_until_valid(
            llm,
            profile_request(script_text(scenes), speakers),
            find_problems=lambda r: _profile_problems(r, speakers),
        )
        characters = {
            c["name"].strip().upper(): c
            for c in reply.get("characters", [])
            if c.get("name")
        }
        save_json(config.CHARACTERS_JSON, {"characters": list(characters.values())})
        return {
            "characters": characters,
            "warnings": [f"profiles: {p}" for p in problems],
        }

    return profile_characters


def _profile_problems(reply: Reply, speakers: List[str]) -> List[str]:
    profiles = {c.get("name", "").strip().upper(): c for c in reply.get("characters", [])}
    problems = [f"no profile for {name}" for name in speakers if name not in profiles]
    for name, profile in profiles.items():
        for field in ("master_profile", "caps_rules", "voice"):
            if not profile.get(field):
                problems.append(f"{name} has no {field}")
    return problems
