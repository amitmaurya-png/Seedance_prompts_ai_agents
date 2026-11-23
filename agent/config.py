"""Settings for the LLM call, in one place."""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class LLMConfig:
    # Override with OPENAI_MODEL in .env.
    model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-5.5"))
    max_completion_tokens: int = 16000
    # For reasoning models: "low" | "medium" | "high". None uses the model default.
    reasoning_effort: Optional[str] = None
    system_prompt: str = "You are a helpful assistant. Answer clearly and concisely."
