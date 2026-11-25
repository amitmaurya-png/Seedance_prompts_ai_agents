"""Paths, per-node skills, and settings, in one place."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple

# --- Paths -------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = PROJECT_ROOT / "skills"
DATA_DIR = PROJECT_ROOT / "data"

SKIT_PDF = DATA_DIR / "TSL.pdf"
BREAKDOWN_JSON = DATA_DIR / "breakdown.json"
CHARACTERS_JSON = DATA_DIR / "characters.json"
PROMPT_JSON = DATA_DIR / "prompt.json"
CURL_JSON = PROJECT_ROOT / "curl" / "curl_commands.json"
CURL_REFERENCES_DIR = SKILLS_DIR / "seedance-curl" / "references"

# --- Which skills each LLM node loads (folder names under skills/) -----------

EXTRACT_SKILLS: Tuple[str, ...] = ("skit-to-prompt-json",)
CLIP_SKILLS: Tuple[str, ...] = ("skit-to-prompt-json", "seedance-prompting")
CAMERA_SKILLS: Tuple[str, ...] = ("camera-knowledge",)
PROFILE_SKILLS: Tuple[str, ...] = ("acting-system", "stylized-3d-film-director")
DIRECTOR_SKILLS: Tuple[str, ...] = (
    "cinedance-director",
    "acting-system",
    "stylized-3d-film-director",
)
# render_prompts and build_curl are plain code: they follow the template in
# skit-to-prompt-json/references/prompt_json_rules.md and the rules in
# seedance-curl/SKILL.md, and read the URL files in seedance-curl/references/.

# --- Run settings ------------------------------------------------------------

# Process only the first N scenes (useful for cheap test runs). None = all.
MAX_SCENES: Optional[int] = None
# How many times an LLM node is asked again when its output fails the
# verbatim check.
VERBATIM_RETRIES = 1

# --- Project rules -----------------------------------------------------------

STYLE_LINE = (
    "Warm, stylized 3D storybook animation (feature-film CG), soft global "
    "illumination, gentle natural light, rich hand-crafted textures, HD, rich "
    "details, heartfelt tone with light comedy"
)

# Added to every clip's CONSTRAINTS (skit-to-prompt-json rules).
BASE_CONSTRAINTS: Tuple[str, ...] = (
    "One camera move per shot",
    "Render everything in stylized 3D animation; use the reference images for "
    "character design only, not for their 2D drawing style",
    "Faces and body proportions stay stable without deformation; movements are "
    "slow, natural, and smooth, with no stutter or flicker",
    "Each character appears only once; no duplicate or twin characters",
    "End on a calm, held frame with no new action in the final second",
    "Keep it subtitle-free; avoid generating any text or subtitles; do not "
    "generate a logo; do not generate a watermark",
)


@dataclass(frozen=True)
class SeedanceSettings:
    endpoint: str = "https://ark.ap-southeast.bytepluses.com/api/v3/contents/generations/tasks"
    model: str = "dreamina-seedance-2-0-260128"
    ratio: str = "16:9"
    resolution: str = "720p"
    generate_audio: bool = True
    return_last_frame: bool = True
    watermark: bool = False
    max_voices: int = 3


SEEDANCE = SeedanceSettings()


# --- LLM ---------------------------------------------------------------------


@dataclass(frozen=True)
class LLMConfig:
    # Override with OPENAI_MODEL in .env.
    model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-5.5"))
    max_completion_tokens: int = 32000
    # For reasoning models: "low" | "medium" | "high". None uses the model default.
    reasoning_effort: Optional[str] = None
    system_prompt: str = "You are a helpful assistant."
    skills_dir: Path = SKILLS_DIR
    # Names of the skills to load. () loads none; None loads every skill.
    skills: Optional[Tuple[str, ...]] = ()
    # Also load each skill's references/*.md files.
    include_references: bool = True
