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
ASSET_PROMPTS_JSON = DATA_DIR / "asset_prompts.json"
CLIP_PLANS_JSON = DATA_DIR / "clip_plans.json"  # plan_clips checkpoint, written after every scene
CLIP_PROMPTS_JSON = DATA_DIR / "clip_prompts.json"  # direct_prompts checkpoint, written after every call
PROMPT_JSON = DATA_DIR / "prompt.json"
CURL_JSON = PROJECT_ROOT / "curl" / "curl_commands.json"
CURL_REFERENCES_DIR = SKILLS_DIR / "seedance-curl" / "references"

# --- Which skills each LLM node loads (folder names under skills/) -----------

EXTRACT_SKILLS: Tuple[str, ...] = ()  # plain verbatim copying; no skill needed
PROFILE_SKILLS: Tuple[str, ...] = ("acting-system", "stylized-3d-film-director")
ASSET_SKILLS: Tuple[str, ...] = ("lira-image-prompts", "stylized-3d-film-director")
PLAN_SKILLS: Tuple[str, ...] = ("stylized-3d-film-director",)
DIRECTOR_SKILLS: Tuple[str, ...] = (
    "cinedance-director",
    "acting-system",
    "stylized-3d-film-director",
)
# build_curl is plain code: it follows seedance-curl/SKILL.md and reads the URL
# files in seedance-curl/references/.

# --- Run settings ------------------------------------------------------------

# Process only the first N scenes (useful for cheap test runs). None = all.
MAX_SCENES: Optional[int] = None
# How many times an LLM node is asked again when its reply fails its checks.
RETRIES = 1
# direct_prompts writes this many clips of one scene per LLM call; larger
# scenes are split evenly (10 clips -> 5 + 5).
DIRECTOR_CLIPS_PER_CALL = 8

# --- Project rules -----------------------------------------------------------

STYLE_LINE = (
    "Warm, stylized 3D storybook animation (feature-film CG), soft global "
    "illumination, gentle natural light, rich hand-crafted textures, HD, rich "
    "details, heartfelt tone with light comedy"
)

# Added to every clip's constraints; the director keeps their meaning in each prompt.
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
