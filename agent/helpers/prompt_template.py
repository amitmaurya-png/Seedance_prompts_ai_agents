"""Render a clip's `prompt` text from its fields.

Follows the template in skills/skit-to-prompt-json/references/prompt_json_rules.md:
FORMAT -> STYLE -> REFERENCES -> SUBJECT -> SCENE -> SHOTS -> AUDIO -> CONSTRAINTS.
Lines that don't apply are left out; no empty labels.
"""

from typing import Any, Dict, List


def render_prompt(clip: Dict[str, Any]) -> str:
    blocks = [
        f"FORMAT: {clip['format']}",
        f"STYLE: {clip['style']}",
        _list_block("REFERENCES", [f"@Image {r['n']}: {r['role']}" for r in clip["references"]]),
        _list_block("SUBJECT", clip.get("subjects", [])),
        f"SCENE: {clip['scene_setting']}",
        _shots_block(clip["shot_details"]),
        _list_block("AUDIO", _audio_lines(clip.get("audio", {}))),
        _list_block("CONSTRAINTS", clip.get("constraints", [])),
    ]
    return "\n\n".join(b for b in blocks if b)


def _list_block(label: str, items: List[str]) -> str:
    items = [i for i in items if i]
    if not items:
        return ""
    return f"{label}:\n" + "\n".join(f"- {item}" for item in items)


def _shots_block(shots: List[Dict[str, Any]]) -> str:
    rendered = []
    for number, shot in enumerate(shots, start=1):
        lines = [f"Shot {number}: {shot.get('title', '')}".rstrip()]
        for label in ("continuity", "camera", "placement", "action", "eyeline"):
            if shot.get(label):
                lines.append(f"  {label.capitalize()}: {shot[label]}")
        for line in shot.get("dialogue", []):
            lines.append(f"  Dialogue: {_dialogue(line)}")
        rendered.append("\n".join(lines))
    return "SHOTS:\n" + "\n\n".join(rendered)


def _dialogue(line: Dict[str, Any]) -> str:
    speaker = line.get("speaker_tag") or line.get("character", "")
    if line.get("voice_over"):
        speaker += " (V.O.)"
    parts = [speaker]
    if line.get("delivery"):
        parts.append(line["delivery"])
    head = ", ".join(parts)
    if line.get("addressee"):
        head += f", to {line['addressee']}"
    return f"{head}: {{{line['line']}}}"


def _audio_lines(audio: Dict[str, Any]) -> List[str]:
    lines = []
    if audio.get("music"):
        lines.append(f"Music: （{audio['music'].strip('（）()')}）")
    if audio.get("ambience"):
        lines.append(f"Ambience: {audio['ambience']}")
    for sfx in audio.get("sfx", []):
        lines.append(f"SFX: <{sfx.strip('<>')}>")
    if audio.get("voices"):
        lines.append("Voices: " + "; ".join(audio["voices"]))
    return lines
