"""Settings for the LLM call, in one place."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Which skill files each node loads: folder names under skills/.
# Each name loads skills/<name>/SKILL.md.
WRITER_SKILLS: Tuple[str, ...] = ("seedance-prompt-writer",)
REVIEWER_SKILLS: Tuple[str, ...] = ("seedance-prompt-reviewer",)


@dataclass(frozen=True)
class LLMConfig:
    # Override with OPENAI_MODEL in .env.
    model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-5.5"))
    max_completion_tokens: int = 16000
    # For reasoning models: "low" | "medium" | "high". None uses the model default.
    reasoning_effort: Optional[str] = None
    system_prompt: str = "You are a helpful assistant. Answer clearly and concisely."
    # Skills in skills/<name>/SKILL.md are appended to the system prompt.
    skills_dir: Path = PROJECT_ROOT / "skills"
    # Names of the skills to load. () loads none; None loads every skill.
    skills: Optional[Tuple[str, ...]] = ()
