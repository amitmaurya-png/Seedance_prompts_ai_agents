"""Graph nodes. Each node takes the state and returns the fields it updates.

    load_skit          code   skit PDF -> scenes
    extract_breakdown  LLM    scenes -> data/breakdown.json          (skit-to-prompt-json)
    build_clips        LLM    breakdown -> clips                     (skit-to-prompt-json, seedance-prompting)
    direct_camera      LLM    clips -> Camera: and Placement: lines  (camera-knowledge)
    render_prompts     code   clips -> prompt text, data/prompt.json
    build_curl         code   prompt.json -> curl/curl_commands.json (seedance-curl)
"""

import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from agent import config
from agent.curl_builder import build_request, read_url_file
from agent.files import save_json
from agent.llm import OpenAILLM
from agent.prompt_render import render_prompt
from agent.skit import check_verbatim, find_dropped_text, read_pdf_text, scene_pieces, split_scenes
from agent.state import PipelineState

log = logging.getLogger("agent")

Node = Callable[[PipelineState], Dict[str, Any]]

NO_SCRIPTS = (
    "The skills mention scripts (scripts/*.py) and project files that are not "
    "available here. Do that work yourself, and reply only with the JSON object "
    "described in the user message."
)

EXTRACT_SYSTEM = (
    "You turn one scene of a skit into a verbatim breakdown, following the "
    "skit-to-prompt-json skill: the breakdown is the source of truth, so copy every "
    "action and dialogue line word for word and in order. " + NO_SCRIPTS
)

CLIPS_SYSTEM = (
    "You group one scene's breakdown into Seedance 2.0 clips for data/prompt.json, "
    "following the skit-to-prompt-json and seedance-prompting skills and their "
    "reference files. Leave camera direction out: a later step writes it. " + NO_SCRIPTS
)

CAMERA_SYSTEM = (
    "You write camera direction for Seedance shots, following the camera-knowledge "
    "skill and its reference files. Change nothing except the camera and placement "
    "lines. " + NO_SCRIPTS
)


# --- 1. load_skit ------------------------------------------------------------


def load_skit(state: PipelineState) -> Dict[str, Any]:
    scenes = split_scenes(read_pdf_text(Path(state["pdf_path"])))
    if not scenes:
        raise ValueError(f"No INT./EXT. scene headings found in {state['pdf_path']}")
    if config.MAX_SCENES is not None:
        scenes = scenes[: config.MAX_SCENES]
    log.info("Loaded %d scenes from %s", len(scenes), state["pdf_path"])
    return {"scenes": scenes}


# --- 2. extract_breakdown ----------------------------------------------------


def make_extract_breakdown(llm: OpenAILLM) -> Node:
    def extract_breakdown(state: PipelineState) -> Dict[str, Any]:
        scenes, warnings = [], []
        for scene in state["scenes"]:
            log.info("Breakdown: scene %d/%d %s", scene["number"], len(state["scenes"]), scene["heading"])
            shots, problems = _ask_until_verbatim(
                llm,
                _extract_request(scene),
                check=lambda reply: _breakdown_problems(reply, scene["text"]),
            )
            for i, shot in enumerate(shots, start=1):
                shot["id"] = f"s{scene['number']}-{i}"
            scenes.append({"number": scene["number"], "heading": scene["heading"], "shots": shots})
            warnings += [f"breakdown scene {scene['number']}: {p}" for p in problems]

        breakdown = {"source": state["pdf_path"], "scenes": scenes}
        save_json(config.BREAKDOWN_JSON, breakdown)
        return {"breakdown": breakdown, "warnings": warnings}

    return extract_breakdown


def _extract_request(scene: Dict[str, Any]) -> str:
    return f"""Scene {scene['number']}: {scene['heading']}

Split the scene text below into shots. A shot is one action paragraph (or consecutive action paragraphs) followed by the dialogue spoken until the next action. Copy text exactly: rejoin lines broken by page wraps, but don't change, add, drop, or reorder any words. Character cue lines (e.g. "NIM") become `character`; parentheticals like "(whispering)" go in `parenthetical`; "(V.O.)" sets `voice_over` to true. If the scene opens with dialogue, the first shot's action is "".

Reply with JSON:
{{"shots": [{{"action": "...", "dialogue": [{{"character": "NIM", "line": "...", "parenthetical": "", "voice_over": false}}]}}]}}

Scene text:
\"\"\"
{scene['text']}
\"\"\""""


def _breakdown_problems(reply: Dict[str, Any], source: str) -> List[str]:
    pieces = scene_pieces(reply)
    problems = check_verbatim(pieces, source)
    problems += [f"dropped from the breakdown: {d}" for d in find_dropped_text(pieces, source)]
    return problems


# --- 3. build_clips ----------------------------------------------------------


def make_build_clips(llm: OpenAILLM) -> Node:
    def build_clips(state: PipelineState) -> Dict[str, Any]:
        image_names = sorted(read_url_file(config.CURL_REFERENCES_DIR / "image_urls"))
        clips: List[Dict[str, Any]] = []
        warnings: List[str] = []

        for scene in state["breakdown"]["scenes"]:
            log.info("Clips: scene %d %s", scene["number"], scene["heading"])
            reply_clips, problems = _ask_until_verbatim(
                llm,
                _clips_request(scene, image_names),
                check=lambda reply: _clip_problems(reply, scene),
                key="clips",
            )
            warnings += [f"clips scene {scene['number']}: {p}" for p in problems]

            for index, raw in enumerate(reply_clips):
                previous = clips[-1]["id"] if clips else None
                clips.append(_finish_clip(raw, len(clips) + 1, scene, index, previous))

        return {"clips": clips, "warnings": warnings}

    return build_clips


def _clips_request(scene: Dict[str, Any], image_names: List[str]) -> str:
    shots = json.dumps(scene["shots"], ensure_ascii=False, indent=1)
    base = "\n".join(f"- {c}" for c in config.BASE_CONSTRAINTS)
    return f"""Scene {scene['number']}: {scene['heading']}

Group this scene's breakdown shots into Seedance 2.0 clips, in order.

Reference images that exist (NAME list): {", ".join(image_names) or "none"}
Name each reference's role after one of these when it fits (e.g. "Miri character reference", "Saba's courtyard scene reference", "Children group reference"). Characters without an image still get a reference and a subject.

Breakdown shots:
{shots}

Rules:
- Copy each action and dialogue line verbatim and in order. Only tag names with their image, as "Miri (@Image 1)"; change nothing else.
- Each clip: 4-15 s, up to 3 shots, about 28 spoken words, up to 4 characters.
- References in order: characters, then groups, then the scene image. Don't list the previous clip's last frame; it is added automatically after your references.
- `continuity` on a shot is only for "still present" notes; the hand-off line is added automatically.
- `constraints`: clip-specific ones only (e.g. Jesus's face never shown). These are added automatically:
{base}

Reply with JSON:
{{"clips": [{{
  "source": ["s{scene['number']}-1"],
  "duration_seconds": 10,
  "references": [{{"n": 1, "role": "Miri character reference"}}],
  "subjects": ["Define the young village girl in @Image 1 as Miri"],
  "scene_image": 2,
  "shot_details": [{{
    "title": "...", "continuity": "", "action": "...", "eyeline": "",
    "dialogue": [{{"character": "MIRI", "speaker_tag": "Miri (@Image 1)", "line": "...",
                  "parenthetical": "", "voice_over": false, "emotion": "", "intensity": "",
                  "delivery": "", "addressee": ""}}]
  }}],
  "audio": {{"music": "", "ambience": "", "sfx": [], "voices": ["Miri (@Image 1) <voice>; clear English dialogue"]}},
  "constraints": []
}}]}}"""


def _clip_problems(reply: Dict[str, Any], scene: Dict[str, Any]) -> List[str]:
    clip_pieces: List[str] = []
    for clip in reply.get("clips", []):
        clip_pieces += scene_pieces({"shots": clip.get("shot_details", [])})
    breakdown_pieces = scene_pieces(scene)
    problems = [f"missing from the clips, {p}" for p in check_verbatim(breakdown_pieces, " ".join(clip_pieces))]
    problems += [f"changed or added, {p}" for p in check_verbatim(clip_pieces, " ".join(breakdown_pieces))]
    for clip in reply.get("clips", []):
        seconds = clip.get("duration_seconds", 0)
        if not 4 <= seconds <= 15:
            problems.append(f"clip {clip.get('source')} is {seconds}s (must be 4-15)")
        if len(clip.get("shot_details", [])) > 3:
            problems.append(f"clip {clip.get('source')} has more than 3 shots")
    return problems


def _finish_clip(
    raw: Dict[str, Any], number: int, scene: Dict[str, Any], index_in_scene: int, previous: str
) -> Dict[str, Any]:
    """Add the fields the skills define as fixed: id, format, style, continuity, params."""
    references = sorted(raw.get("references", []), key=lambda r: r["n"])
    shots = raw.get("shot_details", [])
    constraints = list(config.BASE_CONSTRAINTS)
    continuity = {"mode": "new_scene", "previous_clip": previous}

    if index_in_scene > 0:
        frame_n = len(references) + 1
        references.append({"n": frame_n, "role": f"last frame of {previous} (continuity reference)"})
        handoff = (
            f"Continue the same moment from @Image {frame_n}: keep the lighting, positions, "
            "props, and character appearance exactly as in that frame"
        )
        if shots:
            note = shots[0].get("continuity", "")
            shots[0]["continuity"] = f"{handoff}; {note}" if note else handoff
        constraints.append(
            f"Match lighting, positions, props, and character appearance to @Image {frame_n}"
        )
        continuity = {"mode": "continue_scene", "previous_clip": previous, "handoff_image": frame_n}

    constraints += [c for c in raw.get("constraints", []) if c not in constraints]
    seconds = int(raw.get("duration_seconds", 8))
    shot_count = len(shots)
    scene_image = raw.get("scene_image")

    return {
        "id": f"clip-{number:02d}",
        "scene": scene["heading"],
        "source": raw.get("source", []),
        "duration_seconds": seconds,
        "api_params": {
            "model": config.SEEDANCE.model,
            "ratio": config.SEEDANCE.ratio,
            "duration": seconds,
            "return_last_frame": config.SEEDANCE.return_last_frame,
        },
        "format": f"{seconds}s / {config.SEEDANCE.ratio} / "
        + ("one continuous shot" if shot_count == 1 else f"{shot_count} shots / soft cuts"),
        "style": config.STYLE_LINE,
        "references": references,
        "subjects": raw.get("subjects", []),
        "scene_setting": f"{scene['heading']} (@Image {scene_image})" if scene_image else scene["heading"],
        "shot_details": shots,
        "audio": raw.get("audio", {}),
        "constraints": constraints,
        "continuity": continuity,
    }


# --- 4. direct_camera --------------------------------------------------------


def make_direct_camera(llm: OpenAILLM) -> Node:
    def direct_camera(state: PipelineState) -> Dict[str, Any]:
        clips = state["clips"]
        warnings: List[str] = []

        for heading, scene_clips in _group_by_scene(clips):
            log.info("Camera: %s (%d clips)", heading, len(scene_clips))
            reply = llm.chat_json([{"role": "user", "content": _camera_request(heading, scene_clips)}])
            directions = {d.get("key"): d for d in reply.get("shots", [])}

            for clip in scene_clips:
                for number, shot in enumerate(clip["shot_details"], start=1):
                    key = f"{clip['id']}:{number}"
                    direction = directions.get(key)
                    if not direction:
                        warnings.append(f"camera: no direction returned for {key}")
                        continue
                    shot["camera"] = direction.get("camera", "")
                    shot["placement"] = direction.get("placement", "")
                    shot["camera_reason"] = direction.get("reason", "")

        return {"clips": clips, "warnings": warnings}

    return direct_camera


def _group_by_scene(clips: List[Dict[str, Any]]) -> List[Tuple[str, List[Dict[str, Any]]]]:
    groups: List[Tuple[str, List[Dict[str, Any]]]] = []
    for clip in clips:
        if groups and groups[-1][0] == clip["scene"]:
            groups[-1][1].append(clip)
        else:
            groups.append((clip["scene"], [clip]))
    return groups


def _camera_request(heading: str, clips: List[Dict[str, Any]]) -> str:
    shots = []
    for clip in clips:
        for number, shot in enumerate(clip["shot_details"], start=1):
            shots.append(
                {
                    "key": f"{clip['id']}:{number}",
                    "title": shot.get("title", ""),
                    "action": shot.get("action", ""),
                    "dialogue": [
                        f"{d.get('character')} to {d.get('addressee') or '?'}: {d.get('line')}"
                        for d in shot.get("dialogue", [])
                    ],
                }
            )
    return f"""Scene: {heading}

Write the camera direction for every shot of this scene, in order. The first shot opens the scene.

Shots:
{json.dumps(shots, ensure_ascii=False, indent=1)}

For each shot:
- "camera": `<shot size>[, <angle>][, <one movement>]`, e.g. "Medium close-up, low angle, slow push-in"; "static" when the camera holds. One movement per shot.
- "placement": the shot's main character and where they sit in the frame (which third, which way they face, who else is where), keeping each character on the same side within the scene (180° rule).
- "reason": the detected genre and mood, and why this camera fits, in one sentence.

Reply with JSON:
{{"shots": [{{"key": "clip-01:1", "camera": "...", "placement": "...", "reason": "..."}}]}}"""


# --- 5. render_prompts -------------------------------------------------------


def render_prompts(state: PipelineState) -> Dict[str, Any]:
    clips = state["clips"]
    for clip in clips:
        clip["prompt"] = render_prompt(clip)

    prompt_json = {
        "source": state["pdf_path"],
        "skill": "seedance-prompting",
        "syntax": "skills/seedance-prompting/references/prompt_syntax.md",
        "clip_count": len(clips),
        "total_seconds": sum(c["duration_seconds"] for c in clips),
        "clips": clips,
    }
    save_json(config.PROMPT_JSON, prompt_json)
    log.info("Wrote %d clips to %s", len(clips), config.PROMPT_JSON)
    return {"clips": clips}


# --- 6. build_curl -----------------------------------------------------------


def build_curl(state: PipelineState) -> Dict[str, Any]:
    refs = config.CURL_REFERENCES_DIR
    image_urls = read_url_file(refs / "image_urls")
    audio_urls = read_url_file(refs / "audio_urls")
    last_frames = read_url_file(refs / "last_frames")

    commands = {
        clip["id"]: build_request(clip, image_urls, audio_urls, last_frames, config.SEEDANCE)
        for clip in state["clips"]
    }
    output = {"endpoint": config.SEEDANCE.endpoint, "model": config.SEEDANCE.model, "clips": commands}
    save_json(config.CURL_JSON, output)

    ready = sum(1 for c in commands.values() if not c["missing"])
    log.info("Wrote curl commands to %s (%d/%d ready)", config.CURL_JSON, ready, len(commands))
    return {"curl_commands": output}


# --- Shared ------------------------------------------------------------------


def _ask_until_verbatim(
    llm: OpenAILLM,
    request: str,
    check: Callable[[Dict[str, Any]], List[str]],
    key: str = "shots",
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Ask, check the reply, and ask again with the problems listed (VERBATIM_RETRIES times).

    Returns the last reply's list under `key` and any problems that remain.
    """
    messages = [{"role": "user", "content": request}]
    for attempt in range(config.VERBATIM_RETRIES + 1):
        reply = llm.chat_json(messages)
        problems = check(reply)
        if not problems or attempt == config.VERBATIM_RETRIES:
            return reply.get(key, []), problems
        log.info("  verbatim check found %d problem(s); asking again", len(problems))
        messages += [
            {"role": "assistant", "content": json.dumps(reply, ensure_ascii=False)},
            {
                "role": "user",
                "content": "These problems were found:\n- "
                + "\n- ".join(problems)
                + "\nFix them and reply with the full corrected JSON.",
            },
        ]
    return [], []
