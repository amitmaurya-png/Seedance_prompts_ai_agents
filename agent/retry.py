"""Ask the LLM, check its reply, and ask again with the problems listed."""

import json
import logging
from collections.abc import Callable
from typing import Any

from agent import config
from agent.llm import OpenAILLM
from agent.prompts import fix_request

log = logging.getLogger("agent")

Reply = dict[str, Any]


def ask_until_valid(
    llm: OpenAILLM,
    request: str,
    find_problems: Callable[[Reply], list[str]],
    repair: Callable[[Reply], Reply] | None = None,
) -> tuple[Reply, list[str]]:
    """Return the last reply and the problems that remain after the retries.

    `repair` fixes mechanical problems in code before the check, so the LLM is
    only asked again for problems that need its judgement.
    """
    messages = [{"role": "user", "content": request}]
    retries_left = config.RETRIES

    while True:
        reply = llm.chat_json(messages)
        if repair:
            reply = repair(reply)
        problems = find_problems(reply)
        if not problems or retries_left == 0:
            return reply, problems

        retries_left -= 1
        log.info("  found %d problem(s); asking again", len(problems))
        messages += [
            {"role": "assistant", "content": json.dumps(reply, ensure_ascii=False)},
            {"role": "user", "content": fix_request(problems)},
        ]
