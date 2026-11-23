"""Thin wrapper around the native OpenAI SDK."""

from typing import Any, Dict, List, Optional

from openai import OpenAI
from openai.types.chat import ChatCompletionMessage

from agent.config import LLMConfig
from agent.skills import load_skills, render_skills
from agent.state import Message


class LLMRefusalError(RuntimeError):
    """Raised when the model declines the request."""


class OpenAILLM:
    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        client: Optional[OpenAI] = None,
    ) -> None:
        self.config = config or LLMConfig()
        # Reads OPENAI_API_KEY from the environment by default.
        self.client = client or OpenAI()
        self.skills = load_skills(self.config.skills_dir, self.config.skills)
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Base instructions followed by any loaded skills."""
        skills_section = render_skills(self.skills)
        return "\n\n".join(p for p in (self.config.system_prompt, skills_section) if p)

    def chat(self, messages: List[Message]) -> ChatCompletionMessage:
        """Send the conversation to the model and return its reply message."""
        completion = self.client.chat.completions.create(**self._request_params(messages))
        reply = completion.choices[0].message
        if reply.refusal:
            raise LLMRefusalError(f"Model declined the request: {reply.refusal}")
        return reply

    def _request_params(self, messages: List[Message]) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "model": self.config.model,
            "max_completion_tokens": self.config.max_completion_tokens,
            "messages": [{"role": "system", "content": self.system_prompt}]
            + messages,
        }
        if self.config.reasoning_effort:
            params["reasoning_effort"] = self.config.reasoning_effort
        return params


def to_assistant_message(reply: ChatCompletionMessage) -> Message:
    """Convert a reply into a message to append to the history."""
    return {"role": "assistant", "content": reply.content or ""}
