"""Build Seedance API requests and curl commands for clips.

Follows skills/seedance-curl/SKILL.md:
- images: one image_url per @Image N, in @Image order;
- labels are matched to NAMEs in references/image_urls (full label, then
  subject, then a unique word match);
- "last frame of clip-NN" comes from references/last_frames;
- voices: speakers in order of their first line, at most 3;
- a reference with no URL is sent as <missing: label> and listed in `missing`.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.config import SeedanceSettings
from agent.helpers.clips import clip_speakers

URL_LINE = re.compile(r"^(?P<name>.+?)\s*:\s+(?P<url>\S+)\s*$")
LAST_FRAME = re.compile(r"last frame of (clip-\d+)", re.IGNORECASE)
LABEL_SUFFIXES = (
    "character reference",
    "scene reference",
    "group reference",
    "continuity reference",
    "reference",
)
STOPWORDS = {"the", "a", "an", "of", "in", "and", "with", "within", "around", "reference",
             "character", "scene", "group", "image", "shown", "alone", "sitting", "who"}


# --- URL files ---------------------------------------------------------------


def read_url_file(path: Path) -> Dict[str, str]:
    """`NAME : url` per line -> {NAME: url}. Blank and # lines are skipped."""
    if not path.is_file():
        return {}
    urls = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            match = URL_LINE.match(line.strip())
            if match:
                urls[match["name"].strip()] = match["url"]
    return urls


def _key(text: str) -> str:
    """Compare names ignoring case, '_', "'s" and punctuation."""
    text = text.lower().replace("’", "'").replace("'s", "").replace("_", " ")
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", text).split())


def match_url(label: str, urls: Dict[str, str]) -> Optional[str]:
    """Full label, then the label without its 'reference' suffix, then a unique word."""
    by_key = {_key(name): url for name, url in urls.items()}
    full = _key(label)
    if full in by_key:
        return by_key[full]

    subject = full
    for suffix in LABEL_SUFFIXES:
        if subject.endswith(suffix):
            subject = subject[: -len(suffix)].strip()
            break
    if subject in by_key:
        return by_key[subject]

    words = set(subject.split()) - STOPWORDS
    candidates = [url for key, url in by_key.items() if words & set(key.split())]
    return candidates[0] if len(candidates) == 1 else None


# --- Requests ----------------------------------------------------------------


def build_request(
    clip: Dict[str, Any],
    image_urls: Dict[str, str],
    audio_urls: Dict[str, str],
    last_frames: Dict[str, str],
    settings: SeedanceSettings,
) -> Dict[str, Any]:
    missing: List[str] = []
    content: List[Dict[str, Any]] = []

    for ref in sorted(clip["references"], key=lambda r: r["n"]):
        label = ref["role"]
        frame = LAST_FRAME.search(label)
        url = last_frames.get(frame.group(1)) if frame else match_url(label, image_urls)
        if not url:
            missing.append(label)
            url = f"<missing: {label}>"
        content.append(
            {"type": "image_url", "image_url": {"url": url}, "role": "reference_image"}
        )

    voices = []
    for speaker in clip_speakers(clip)[: settings.max_voices]:
        url = match_url(speaker, audio_urls)
        if url:
            voices.append(speaker)
            content.append(
                {"type": "audio_url", "audio_url": {"url": url}, "role": "reference_audio"}
            )

    text = _add_voice_line(clip["prompt"], voices)
    body = {
        "model": settings.model,
        "content": [{"type": "text", "text": text}] + content,
        "ratio": settings.ratio,
        "duration": clip["duration_seconds"],
        "resolution": settings.resolution,
        "generate_audio": settings.generate_audio,
        "return_last_frame": settings.return_last_frame,
        "watermark": settings.watermark,
    }
    return {
        "scene": clip["scene"],
        "duration_seconds": clip["duration_seconds"],
        "previous_clip": clip.get("continuity", {}).get("previous_clip"),
        "missing": missing,
        "request": body,
        "curl": to_curl(body, settings.endpoint),
    }


def to_curl(body: Dict[str, Any], endpoint: str) -> str:
    data = json.dumps(body, ensure_ascii=False, indent=2).replace("'", "'\\''")
    return (
        f"curl --location --request POST '{endpoint}' \\\n"
        '--header "Authorization: Bearer $ARK_API_KEY" \\\n'
        "--header 'Content-Type: application/json' \\\n"
        f"--data-raw '{data}'"
    )


def _add_voice_line(prompt: str, voices: List[str]) -> str:
    """Add '- Voice references: @Audio 1 is Saba's voice, ...' under '- Voices:'."""
    if not voices:
        return prompt
    note = "- Voice references: " + ", ".join(
        f"@Audio {i} is {name.title()}'s voice" for i, name in enumerate(voices, start=1)
    )
    lines = prompt.split("\n")
    # Under the "- Voices:" line, else right under the AUDIO heading, else in a new AUDIO block.
    for prefix in ("- Voices:", "AUDIO"):
        for index, line in enumerate(lines):
            if line.strip().startswith(prefix):
                lines.insert(index + 1, note)
                return "\n".join(lines)
    return f"{prompt}\n\nAUDIO:\n{note}"
