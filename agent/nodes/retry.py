"""Ask the LLM, check its reply, and ask again with the problems listed."""

import json
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from agent import config
from agent.llm import OpenAILLM
from agent.prompts import fix_request

log = logging.getLogger("agent")

Reply = Dict[str, Any]


def ask_until_valid(
    llm: OpenAILLM,
    request: str,
    find_problems: Callable[[Reply], List[str]],
    repair: Optional[Callable[[Reply], Reply]] = None,
) -> Tuple[Reply, List[str]]:
    """Return the last reply and the problems that remain after the retries.

    `repair` fixes mechanical problems in code before the check, so the LLM is
    only asked again for problems that need its judgement.
    """
    messages = [{"role": "user", "content": request}]
    reply = llm.chat_json(messages)
    if repair:
        reply = repair(reply)
    problems = find_problems(reply)

    for _ in range(config.VERBATIM_RETRIES):
        if not problems:
            break
        log.info("  found %d problem(s); asking again", len(problems))
        messages += [
            {"role": "assistant", "content": json.dumps(reply, ensure_ascii=False)},
            {"role": "user", "content": fix_request(problems)},
        ]
        reply = llm.chat_json(messages)
        if repair:
            reply = repair(reply)
        problems = find_problems(reply)

    return reply, problems
