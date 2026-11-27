"""Every instruction the LLM nodes send, in one place.

Each LLM node has a SYSTEM prompt (its role; the node's skills are appended to
it automatically) and a request builder for the user message.
"""

import json
from typing import Any

# The skills are written for a person working with a user. Here each node runs
# unattended, so these parts are switched off.
UNATTENDED = (
    "You run as one step of an automated pipeline: there is no web access, no user "
    "to ask or show drafts to, and no previz or finishing stage. Skip those parts of "
    "the skills and reply only with the JSON object described in the user message."
)


def fix_request(problems: list[str]) -> str:
    """Follow-up message when a reply fails its checks."""
    listed = "\n- ".join(problems)
    return (
        f"These problems were found:\n- {listed}\nFix them and reply with the full corrected JSON."
    )


# --- extract_breakdown -------------------------------------------------------

EXTRACT_SYSTEM = (
    "You turn one scene of a skit into a verbatim breakdown. Every later step works "
    "from this breakdown, so copy every action and dialogue line word for word and in "
    "order. Reply only with the JSON object described in the user message."
)


def extract_request(scene: dict[str, Any]) -> str:
    return f"""Scene {scene["number"]}: {scene["heading"]}

Split the scene text below into shots. A shot is one action paragraph (or consecutive action paragraphs) followed by the dialogue spoken until the next action. Copy text exactly: rejoin lines broken by page wraps, but don't change, add, drop, or reorder any words. Character cue lines (e.g. "NIM") become `character`; parentheticals like "(whispering)" go in `parenthetical`; "(V.O.)" sets `voice_over` to true. If the scene opens with dialogue, the first shot's action is "".

Reply with JSON:
{{"shots": [{{"action": "...", "dialogue": [{{"character": "NIM", "line": "...", "parenthetical": "", "voice_over": false}}]}}]}}

Scene text:
\"\"\"
{scene["text"]}
\"\"\""""


# --- profile_characters ------------------------------------------------------

PROFILE_SYSTEM = (
    "You are the acting coach for a stylised 3D animated film made with Seedance 2.0. "
    "Following the acting-system and stylized-3d-film-director skills, you write one "
    "acting profile per character before any shot is prompted. Build each profile from "
    "the script and from what you know of how people of that age, role and "
    "circumstance really behave (first-person accounts, guides for actors), avoiding "
    "clichés. " + UNATTENDED
)


def profile_request(script: str, speakers: list[str]) -> str:
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


# --- asset_prompts -----------------------------------------------------------

ASSET_SYSTEM = (
    "You are Lira, writing the image prompts for the reference assets of a stylised 3D "
    "animated film: character sheets and location plates that Seedance 2.0 clips will "
    "use as @Image references. Follow the lira-image-prompts skill in BASIC mode for "
    "model routing, platform parameters and its anti-fail rules, and the "
    "stylized-3d-film-director skill (sections 2 and 3) for the locked style, the "
    "three-panel sheet layout and location plates. The film is stylised 3D, not "
    "photoreal: where Lira's templates assume photoreal (film stocks, camera bodies, "
    "photoreal anchors), use the project's style block instead. " + UNATTENDED
)


def asset_request(
    script: str,
    characters: list[str],
    places: list[str],
    image_names: list[str],
    style_line: str,
) -> str:
    return f"""Write one image prompt per reference asset for this film.

Characters (one character sheet each): {", ".join(characters) or "none"}
Locations (one plate each, from the scene headings): {", ".join(places) or "none"}
Add a separate asset for any prop the story depends on, and a separate state asset when a character's look changes in the story (wounded, wet, healed ...).

Rules:
- Style block, pasted word for word into every prompt: {style_line}
- Character sheets: three panels on a flat light-grey background (stylized-3d-film-director section 3). Describe the character's look from the script: age, build, face, hair, wardrobe, marks and props.
- Location plates: empty of people, with depth built in (dark foreground frame, clear midground, misty distance).
- Aspect ratio, resolution and Soul ID are platform settings: put them in "platform_settings", never in the prompt text.
- "name": the NAME this asset will have in the image URL file, in upper case. Reuse an existing NAME when the asset is one of these: {", ".join(image_names) or "none yet"}.

Reply with JSON:
{{"assets": [{{"name": "MIRI", "kind": "character", "model": "Higgsfield Soul 2.0", "platform_settings": "aspect 16:9, quality 2k", "prompt": "...", "notes": "what to watch, what to toggle"}}]}}
"kind" is one of: character, location, prop, state.

Script:
\"\"\"
{script}
\"\"\""""


# --- plan_clips --------------------------------------------------------------

PLAN_SYSTEM = (
    "You are the first assistant director of a stylised 3D animated film made with "
    "Seedance 2.0. You split one scene's verbatim breakdown into generation clips, "
    "following the stylized-3d-film-director skill: at most 4 shots per generation, at "
    "most 2 actions per shot, long beats with few actions, and continuity from one "
    "generation to the next. Camera, acting and the prompt text are written by a later "
    "step. " + UNATTENDED
)


def plan_request(scene: dict[str, Any], image_names: list[str]) -> str:
    shots = json.dumps(scene["shots"], ensure_ascii=False, indent=1)
    return f"""Scene {scene["number"]}: {scene["heading"]}

Group this scene's breakdown shots into Seedance 2.0 clips, in order.

Reference images that exist (NAME list): {", ".join(image_names) or "none"}
Name each reference's role after one of these when it fits (e.g. "Miri character reference", "Saba's courtyard scene reference", "Children group reference"). Characters without an image still get a reference.

Breakdown shots:
{shots}

Rules:
- Copy each action and dialogue line verbatim and in order; change, add or drop nothing. A long action paragraph may be split across shots, but only between sentences.
- Each clip: 4-15 s, 1-4 shots, about 28 spoken words, up to 4 characters. Give every shot its "seconds"; a clip's shots add up to its duration_seconds.
- References in order: characters, then groups and props, then the scene image. Don't list the previous clip's last frame; it is added automatically after your references.
- `continuity` on a shot is only for "still present" notes; the hand-off from the previous clip is added automatically.
- `audio`: the real sounds of the scene (ambience and sound effects); no music.
- `constraints`: clip-specific ones only (e.g. a face that is never shown).

Reply with JSON:
{{"clips": [{{
  "source": ["s{scene["number"]}-1"],
  "duration_seconds": 10,
  "references": [{{"n": 1, "role": "Miri character reference"}}],
  "scene_image": 2,
  "shot_details": [{{
    "title": "...", "seconds": 5, "continuity": "", "action": "...",
    "dialogue": [{{"character": "MIRI", "line": "...", "parenthetical": "", "voice_over": false}}]
  }}],
  "audio": {{"ambience": "", "sfx": []}},
  "constraints": []
}}]}}"""


# --- direct_prompts ----------------------------------------------------------

DIRECTOR_SYSTEM = (
    "You are the director who writes the final Seedance 2.0 video prompt for one clip "
    "of a stylised 3D animated film. Follow the cinedance-director skill for the "
    "prompt's structure, first frame, blocking, optics, camera, physics, lighting and "
    "context isolation; the acting-system skill to adapt each character's master "
    "profile to this clip; and the stylized-3d-film-director skill's prompt-writing "
    "rules (sections 2, 5 and 8). " + UNATTENDED
)


def director_request(
    clips: list[dict[str, Any]], profiles: list[dict[str, Any]], style_line: str
) -> str:
    """One request for several clips of the same scene."""
    sections = "\n\n".join(_clip_section(clip) for clip in clips)
    ids = ", ".join(clip["id"] for clip in clips)
    acting = json.dumps(profiles, ensure_ascii=False, indent=1) if profiles else "none"
    return f"""Write the final Seedance 2.0 prompt for each of these clips of one scene: {ids}.

Each prompt is generated on its own, so each one must stand alone: never refer to another clip's prompt ("as before", "same as clip-03"). Keep the scene's geography, screen direction, lighting and acting consistent from one clip to the next.

Rules for every clip:
- Use that clip's reference images with their exact tags, and name each character by their tag, e.g. "Miri (@Image 1)". Use no other @Image, @Video or @Audio tags; voice references are attached automatically after you.
- If a reference is the "last frame of clip-NN", the clip opens exactly on that image: same positions, lighting, props and appearance.
- Style block, pasted word for word: {style_line}
- Speak only that clip's lines, each word for word, in order, by its speaker.
- Keep the clip's shots, their order and their seconds. Duration, ratio and resolution are set by the API, so leave them out of the prompt.
- Keep the meaning of every constraint, as positive constraints or local locks.
- In AUDIO, include one line starting with "- Voices:" that names each speaker, and exactly one "no background music" line. For each character who speaks, paste their "voice" text word for word into AUDIO.

Acting profiles of the characters in these clips (adapt them to each clip; never paste them unchanged):
{acting}

The clips, as planned from the script (actions and dialogue are verbatim):

{sections}

Reply with JSON, one prompt per clip id:
{{"prompts": {{"{clips[0]["id"]}": "SCENE CONTEXT\\n..."}}}}"""


def _clip_section(clip: dict[str, Any]) -> str:
    references = "\n".join(f"  - @Image {r['n']}: {r['role']}" for r in clip["references"])
    dialogue = (
        "\n".join(
            f"  - {line.get('character')}: {line['line']}"
            for shot in clip["shot_details"]
            for line in shot.get("dialogue", [])
        )
        or "  - none (no one speaks in this clip)"
    )
    brief = {
        "scene": clip["scene_setting"],
        "duration_seconds": clip["duration_seconds"],
        "shots": clip["shot_details"],
        "audio": clip.get("audio", {}),
        "constraints": clip["constraints"],
    }
    return f"""=== {clip["id"]} ({clip["duration_seconds"]} s, {len(clip["shot_details"])} shot(s))
Reference images:
{references}
Spoken lines, in order:
{dialogue}
Plan:
{json.dumps(brief, ensure_ascii=False, indent=1)}"""


# --- enhance_prompts ---------------------------------------------------------

ENHANCER_SYSTEM = (
    "You are the prompt enhancer for a stylised 3D animated film made with Seedance "
    "2.0. You receive finished director prompts and rewrite each one following the "
    "enhancer-prompt skill: replace vague wording with deterministic locks (entities, "
    "screen geography, first frame, shot timing, FOV and camera speed, prop states, "
    "eye-lines, physics, lighting, timestamped audio) and finish with its credibility "
    "lint. You sharpen the prompt; you never change the story. " + UNATTENDED
)


def enhancer_request(clips: list[dict[str, Any]], style_line: str) -> str:
    """One request to enhance several finished prompts of the same scene."""
    sections = "\n\n".join(_enhance_section(clip) for clip in clips)
    ids = ", ".join(clip["id"] for clip in clips)
    return f"""Enhance the Seedance 2.0 prompt of each of these clips of one scene: {ids}.

Apply the enhancer-prompt skill, with these project rules taking priority over it:
- Each prompt is sent to Seedance on its own, so each must stay complete and stand alone. Skill 02 (scene inheritance) does not apply: keep the STYLE, ACTIVE REFERENCES, LOCATION MAP, LIGHTING and AUDIO blocks inside every prompt, never replace them with IDs like char_miri, and never refer to another clip.
- The numbers in the skill (4200K, frame-right sun, 15% haze ...) are examples. Keep the directions, positions and lighting this prompt already sets, and make them exact; never contradict them.
- Story: add no new characters, actions, props or lines. Only sharpen what is there.
- Shots: keep the same shots, in the same order, with the same seconds; the total stays the clip's duration. You may add exact second offsets inside a shot.
- Dialogue: every listed line word for word, in order, by its speaker; no other speech or narration. The skill-11 format `2.7s — SPEAKER (delivery): "Exact words."` is welcome.
- References: use only the clip's own @Image tags, unchanged; no @Audio or @Video tags. If a reference is the last frame of the previous clip, the clip still opens exactly on it.
- Style block, word for word: {style_line}
- AUDIO keeps its "- Voices:" line, each speaker's voice text word for word, and exactly one "no background music" line (no score cues).
- Keep the meaning of every constraint already in the prompt; end with POSITIVE LOCKS and NEGATIVE / AVOID blocks (skill 12).

The clips:

{sections}

Reply with JSON, one enhanced prompt per clip id:
{{"prompts": {{"{clips[0]["id"]}": "SCENE CONTEXT\\n..."}}}}"""


def _enhance_section(clip: dict[str, Any]) -> str:
    references = "\n".join(f"  - @Image {r['n']}: {r['role']}" for r in clip["references"])
    shots = "\n".join(
        f"  {number}. {shot.get('title', '')} ({shot.get('seconds')} s)"
        for number, shot in enumerate(clip["shot_details"], start=1)
    )
    dialogue = (
        "\n".join(
            f"  - {line.get('character')}: {line['line']}"
            for shot in clip["shot_details"]
            for line in shot.get("dialogue", [])
        )
        or "  - none (no one speaks in this clip)"
    )
    return f"""=== {clip["id"]} ({clip["duration_seconds"]} s)
Reference images:
{references}
Shots:
{shots}
Spoken lines, in order:
{dialogue}
Prompt to enhance:
\"\"\"
{clip["prompt"]}
\"\"\""""


def prompts_fix_request(problems: dict[str, list[str]]) -> str:
    """Ask again only for the clips whose prompts failed a check (director and enhancer)."""
    listed = "\n".join(
        f"{clip_id}:\n" + "\n".join(f"- {p}" for p in found) for clip_id, found in problems.items()
    )
    return f"""These prompts have problems:
{listed}

Fix them. Reply with JSON holding only the corrected prompts, in full: {{"prompts": {{"<clip id>": "..."}}}} for {", ".join(problems)}."""
