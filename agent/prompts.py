"""Every instruction the LLM nodes send, in one place.

Each LLM node has a SYSTEM prompt (its role; the node's skills are appended to
it automatically) and a request builder for the user message.
"""

import json
from typing import Any, Dict, List

from agent.config import BASE_CONSTRAINTS

NO_SCRIPTS = (
    "The skills mention scripts (scripts/*.py) and project files that are not "
    "available here. Do that work yourself, and reply only with the JSON object "
    "described in the user message."
)


def fix_request(problems: List[str]) -> str:
    """Follow-up message when a reply fails the verbatim check."""
    listed = "\n- ".join(problems)
    return f"These problems were found:\n- {listed}\nFix them and reply with the full corrected JSON."


# --- extract_breakdown -------------------------------------------------------

EXTRACT_SYSTEM = (
    "You turn one scene of a skit into a verbatim breakdown, following the "
    "skit-to-prompt-json skill: the breakdown is the source of truth, so copy every "
    "action and dialogue line word for word and in order. " + NO_SCRIPTS
)


def extract_request(scene: Dict[str, Any]) -> str:
    return f"""Scene {scene['number']}: {scene['heading']}

Split the scene text below into shots. A shot is one action paragraph (or consecutive action paragraphs) followed by the dialogue spoken until the next action. Copy text exactly: rejoin lines broken by page wraps, but don't change, add, drop, or reorder any words. Character cue lines (e.g. "NIM") become `character`; parentheticals like "(whispering)" go in `parenthetical`; "(V.O.)" sets `voice_over` to true. If the scene opens with dialogue, the first shot's action is "".

Reply with JSON:
{{"shots": [{{"action": "...", "dialogue": [{{"character": "NIM", "line": "...", "parenthetical": "", "voice_over": false}}]}}]}}

Scene text:
\"\"\"
{scene['text']}
\"\"\""""


# --- build_clips -------------------------------------------------------------

CLIPS_SYSTEM = (
    "You group one scene's breakdown into Seedance 2.0 clips for data/prompt.json, "
    "following the skit-to-prompt-json and seedance-prompting skills and their "
    "reference files. Leave camera direction out: a later step writes it. " + NO_SCRIPTS
)


def clips_request(scene: Dict[str, Any], image_names: List[str]) -> str:
    shots = json.dumps(scene["shots"], ensure_ascii=False, indent=1)
    base_constraints = "\n".join(f"  - {c}" for c in BASE_CONSTRAINTS)
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
{base_constraints}

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


# --- direct_camera -----------------------------------------------------------

CAMERA_SYSTEM = (
    "You write camera direction for Seedance shots, following the camera-knowledge "
    "skill and its reference files. Change nothing except the camera and placement "
    "lines. " + NO_SCRIPTS
)


def camera_request(heading: str, shots: List[Dict[str, Any]]) -> str:
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


# --- profile_characters ------------------------------------------------------

PROFILE_SYSTEM = (
    "You are the acting coach for a stylised 3D animated film made with Seedance 2.0. "
    "Following the acting-system and stylized-3d-film-director skills, you write one "
    "acting profile per character before any shot is prompted. There is no web access "
    "and no user to ask: build each profile from the script and from what you know of "
    "how people of that age, role and circumstance really behave (first-person "
    "accounts, guides for actors), avoiding clichés. Reply only with the JSON object "
    "described in the user message."
)


def profile_request(script: str, speakers: List[str]) -> str:
    return f"""Write an acting profile for each of these speaking characters: {", ".join(speakers)}.
Add any other character who appears on screen in more than one scene.

For each character:
- "name": the name exactly as the script writes it (e.g. "MIRI").
- "master_profile": one 150-220 word paragraph following the acting-system master-profile template (section 6): body, psychological engine, vocal profile, tics with triggers, eye life, a named gait, at least one "However, when ..." crack, and an optional softening target. Behaviour only; no wardrobe, camera or colour.
- "caps_rules": 6-15 numbered, physical, testable rules in CAPS (stylized-3d-film-director section 0.3).
- "forbidden_readings": the wrong performances a video model would default to for this character.
- "voice": the locked Voice prompt (acting-system section 9), one or two sentences in double quotes.

Reply with JSON:
{{"characters": [{{"name": "MIRI", "master_profile": "...", "caps_rules": ["1. ..."], "forbidden_readings": ["..."], "voice": "\\"A 9-year-old ...\\""}}]}}

Script:
\"\"\"
{script}
\"\"\""""


# --- direct_prompts ----------------------------------------------------------

DIRECTOR_SYSTEM = (
    "You are the director who writes the final Seedance 2.0 video prompt for one clip "
    "of a stylised 3D animated film. Follow the cinedance-director skill for the "
    "prompt's structure, first frame, blocking, optics, physics, lighting and context "
    "isolation; the acting-system skill to adapt each character's master profile to "
    "this clip; and the stylized-3d-film-director skill's prompt-writing rules "
    "(sections 2, 5 and 8). Skip whatever those skills say about web research, asking "
    "the user, previz, drafts or finishing: none of that is available here. Reply only "
    "with the JSON object described in the user message."
)


def director_request(
    clip: Dict[str, Any], profiles: List[Dict[str, Any]], style_line: str
) -> str:
    references = "\n".join(f"- @Image {r['n']}: {r['role']}" for r in clip["references"])
    dialogue = "\n".join(
        f"- {line.get('speaker_tag') or line.get('character')}: {line['line']}"
        for shot in clip["shot_details"]
        for line in shot.get("dialogue", [])
    ) or "- none (no one speaks in this clip)"
    acting = json.dumps(profiles, ensure_ascii=False, indent=1) if profiles else "none"
    return f"""Write the final Seedance 2.0 prompt for {clip['id']} ({clip['duration_seconds']} s, {len(clip['shot_details'])} shot(s)).

Fixed facts; keep all of them:
- Reference images, with these exact tags. Use no other @Image, @Video or @Audio tags; voice references are attached automatically after you.
{references}
- If a reference is the "last frame of clip-NN", the clip opens exactly on that image: same positions, lighting, props and appearance.
- Style block, pasted word for word: {style_line}
- Spoken lines, each word for word, in this order, by these speakers, and nothing else spoken:
{dialogue}
- Duration, ratio and resolution are set by the API, so leave them out of the prompt.
- Keep the meaning of every constraint in the draft, as positive constraints or local locks.

Acting profiles of the characters in this clip (adapt them to this clip; never paste them unchanged). For each character who speaks, paste their "voice" text word for word into AUDIO:
{acting}

In AUDIO, include one line starting with "- Voices:" that names each speaker.

The draft below was built from the script by a template. It already has the clip's shots, camera and placement choices, audio and constraints. Rebuild it into the cinedance-director structure; keep its story, order and timing.

Draft:
\"\"\"
{clip['prompt']}
\"\"\"

Reply with JSON:
{{"prompt": "SCENE CONTEXT\\n..."}}"""
