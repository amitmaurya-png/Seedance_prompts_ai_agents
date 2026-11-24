"""Thin wrapper around the native OpenAI SDK."""

import json
from typing import Any, Dict, List, Optional

from openai import OpenAI

from agent.config import LLMConfig
from agent.skills import load_skills, render_skills

Message = Dict[str, Any]


class LLMRefusalError(RuntimeError):
    """Raised when the model declines the request."""


class LLMOutputError(RuntimeError):
    """Raised when the reply is cut off or isn't valid JSON."""


class OpenAILLM:
    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        client: Optional[OpenAI] = None,
    ) -> None:
        self.config = config or LLMConfig()
        # Reads OPENAI_API_KEY from the environment by default.
        self.client = client or OpenAI()
        self.skills = load_skills(
            self.config.skills_dir, self.config.skills, self.config.include_references
        )
        self.system_prompt = self._build_system_prompt()

    def chat(self, messages: List[Message]) -> str:
        """Send the conversation and return the reply text."""
        return self._complete(messages)

    def chat_json(self, messages: List[Message]) -> Dict[str, Any]:
        """Send the conversation and return the reply parsed as a JSON object."""
        text = self._complete(messages, response_format={"type": "json_object"})
        try:
            return json.loads(text)
        except json.JSONDecodeError as error:
            raise LLMOutputError(f"Reply is not valid JSON: {error}") from error

    def _build_system_prompt(self) -> str:
        """Base instructions followed by any loaded skills."""
        skills_section = render_skills(self.skills)
        return "\n\n".join(p for p in (self.config.system_prompt, skills_section) if p)

    def _complete(self, messages: List[Message], **extra: Any) -> str:
        completion = self.client.chat.completions.create(
            **self._request_params(messages), **extra
        )
        choice = completion.choices[0]
        if choice.message.refusal:
            raise LLMRefusalError(f"Model declined the request: {choice.message.refusal}")
        if choice.finish_reason == "length":
            raise LLMOutputError(
                "Reply was cut off at max_completion_tokens; raise it in LLMConfig"
            )
        return choice.message.content or ""

    def _request_params(self, messages: List[Message]) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "model": self.config.model,
            "max_completion_tokens": self.config.max_completion_tokens,
            "messages": [{"role": "system", "content": self.system_prompt}] + messages,
        }
        if self.config.reasoning_effort:
            params["reasoning_effort"] = self.config.reasoning_effort
        return params
