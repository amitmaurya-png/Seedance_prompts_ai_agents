"""Load SKILL.md files and turn them into agent instructions.

Layout:
    skills/
      <skill-name>/
        SKILL.md

SKILL.md format:
    ---
    name: seedance-prompt-writer
    description: One line saying when to use this skill.
    ---
    Markdown instructions the agent should follow.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

SKILL_FILENAME = "SKILL.md"
FRONTMATTER_DELIMITER = "---"


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    instructions: str


def load_skills(skills_dir: Path, names: Optional[Iterable[str]] = None) -> List[Skill]:
    """Load skills from skills_dir.

    names=None loads every skills/<name>/SKILL.md (sorted by folder name);
    otherwise only the named skills are loaded, in the order given.
    """
    if names is not None:
        return [load_skill_by_name(skills_dir, name) for name in names]
    if not skills_dir.is_dir():
        return []
    return [load_skill(path) for path in sorted(skills_dir.glob(f"*/{SKILL_FILENAME}"))]


def load_skill_by_name(skills_dir: Path, name: str) -> Skill:
    """Load skills/<name>/SKILL.md. Raises FileNotFoundError if it doesn't exist."""
    path = skills_dir / name / SKILL_FILENAME
    if not path.is_file():
        available = sorted(p.parent.name for p in skills_dir.glob(f"*/{SKILL_FILENAME}"))
        raise FileNotFoundError(f"Skill '{name}' not found at {path}. Available: {available}")
    return load_skill(path)


def load_skill(path: Path) -> Skill:
    """Load a single SKILL.md from an explicit file path."""
    metadata, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    name = metadata.get("name") or path.parent.name
    description = metadata.get("description", "")
    if not body:
        raise ValueError(f"{path} has no instructions after the frontmatter")
    return Skill(name=name, description=description, instructions=body)


def render_skills(skills: List[Skill]) -> str:
    """Format skills as a section to append to the system prompt."""
    if not skills:
        return ""
    sections = [
        f"## Skill: {skill.name}\nUse when: {skill.description}\n\n{skill.instructions}"
        for skill in skills
    ]
    return "# Skills\nApply a skill when the request matches its 'Use when'.\n\n" + "\n\n".join(
        sections
    )


def _split_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    """Split '---' key: value '---' frontmatter from the markdown body."""
    lines = text.strip().splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIMITER:
        return {}, text.strip()

    metadata: Dict[str, str] = {}
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == FRONTMATTER_DELIMITER:
            body = "\n".join(lines[index + 1 :]).strip()
            return metadata, body
        key, _, value = line.partition(":")
        if key.strip():
            metadata[key.strip()] = value.strip()

    raise ValueError("Frontmatter starts with '---' but is never closed")
