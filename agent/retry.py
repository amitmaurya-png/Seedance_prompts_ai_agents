"""Ask the LLM, check its reply, and ask again with the problems listed.

ask_until_valid   one reply checked as a whole
ask_for_prompts   one prompt per clip, each repaired and checked on its own;
                  a retry asks again only for the clips that still fail
"""

import json
import logging
from collections.abc import Callable
from typing import Any

from agent import config
from agent.helpers.prompt_repair import prompt_problems, repair_prompt
from agent.llm import OpenAILLM
from agent.prompts import fix_request, prompts_fix_request
from agent.state import Clip, Profile

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


def ask_for_prompts(
    llm: OpenAILLM,
    request: str,
    clips: list[Clip],
    profiles: dict[str, list[Profile]],
) -> dict[str, tuple[str, list[str]]]:
    """{clip id: (prompt, problems left)} for a request that asks for
    {"prompts": {clip id: prompt}}.

    Every prompt is repaired in code (repair_prompt) before it is checked
    (prompt_problems). Each retry asks again only for the clips that still fail.
    """
    by_id = {clip["id"]: clip for clip in clips}
    messages = [{"role": "user", "content": request}]

    prompts: dict[str, str] = {}
    problems: dict[str, list[str]] = {}
    asking_for = list(by_id)
    retries_left = config.RETRIES

    while True:
        reply = llm.chat_json(messages)
        for clip_id in asking_for:
            clip = by_id[clip_id]
            text = _returned_prompt(reply, clip_id)
            if text:  # a clip left out of a retry keeps its earlier prompt
                prompts[clip_id] = repair_prompt(text, clip, profiles[clip_id])
            problems[clip_id] = prompt_problems(prompts.get(clip_id, ""), clip)

        failing = {clip_id: found for clip_id, found in problems.items() if found}
        if not failing or retries_left == 0:
            return {clip_id: (prompts.get(clip_id, ""), problems[clip_id]) for clip_id in by_id}

        retries_left -= 1
        log.info("  %d clip(s) with problems; asking again for those only", len(failing))
        messages += [
            {"role": "assistant", "content": json.dumps(reply, ensure_ascii=False)},
            {"role": "user", "content": prompts_fix_request(failing)},
        ]
        asking_for = list(failing)


def _returned_prompt(reply: Reply, clip_id: str) -> str:
    """The prompt the reply holds for this clip, stripped; "" if it has none."""
    returned = reply.get("prompts")
    text = returned.get(clip_id) if isinstance(returned, dict) else None
    return text.strip() if isinstance(text, str) else ""
