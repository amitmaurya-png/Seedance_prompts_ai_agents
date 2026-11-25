"""Load SKILL.md files (and their reference files) and turn them into instructions.

Layout:
    skills/
      <skill-name>/
        SKILL.md
        references/*.md      (optional, loaded with the skill)

SKILL.md format:
    ---
    name: seedance-prompting
    description: One line saying when to use this skill.
    ---
    Markdown instructions the agent should follow.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

SKILL_FILENAME = "SKILL.md"
REFERENCES_DIRNAME = "references"
FRONTMATTER_DELIMITER = "---"


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    instructions: str
    # (file name, text) for each references/*.md file.
    references: Tuple[Tuple[str, str], ...] = ()


def load_skills(
    skills_dir: Path,
    names: Optional[Iterable[str]] = None,
    include_references: bool = False,
) -> List[Skill]:
    """Load skills from skills_dir.

    names=None loads every skills/<name>/SKILL.md (sorted by folder name);
    otherwise only the named skills are loaded, in the order given.
    """
    if names is not None:
        return [load_skill_by_name(skills_dir, n, include_references) for n in names]
    if not skills_dir.is_dir():
        return []
    paths = sorted(skills_dir.glob(f"*/{SKILL_FILENAME}"))
    return [load_skill(p, include_references) for p in paths]


def load_skill_by_name(
    skills_dir: Path, name: str, include_references: bool = False
) -> Skill:
    """Load skills/<name>/SKILL.md. Raises FileNotFoundError if it doesn't exist."""
    path = skills_dir / name / SKILL_FILENAME
    if not path.is_file():
        available = sorted(p.parent.name for p in skills_dir.glob(f"*/{SKILL_FILENAME}"))
        raise FileNotFoundError(f"Skill '{name}' not found at {path}. Available: {available}")
    return load_skill(path, include_references)


def load_skill(path: Path, include_references: bool = False) -> Skill:
    """Load a single SKILL.md from an explicit file path."""
    metadata, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    if not body:
        raise ValueError(f"{path} has no instructions after the frontmatter")
    references = _load_references(path.parent) if include_references else ()
    return Skill(
        name=metadata.get("name") or path.parent.name,
        description=metadata.get("description", "").strip('"'),
        instructions=body,
        references=references,
    )


def render_skills(skills: List[Skill]) -> str:
    """Format skills (and their references) as a section of the system prompt."""
    if not skills:
        return ""
    return "# Skills\n\n" + "\n\n".join(_render_skill(s) for s in skills)


def _render_skill(skill: Skill) -> str:
    parts = [f"## Skill: {skill.name}\nUse when: {skill.description}\n\n{skill.instructions}"]
    for filename, text in skill.references:
        parts.append(f"### Reference file: {skill.name}/references/{filename}\n\n{text}")
    return "\n\n".join(parts)


def _load_references(skill_dir: Path) -> Tuple[Tuple[str, str], ...]:
    ref_dir = skill_dir / REFERENCES_DIRNAME
    if not ref_dir.is_dir():
        return ()
    return tuple(
        (p.name, p.read_text(encoding="utf-8").strip()) for p in sorted(ref_dir.glob("*.md"))
    )


def _split_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    """Split '---' key: value '---' frontmatter from the markdown body."""
    lines = text.strip().splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIMITER:
        return {}, text.strip()

    metadata: Dict[str, str] = {}
    folding_key = None  # key whose value is a `>` or `|` block on the lines below
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == FRONTMATTER_DELIMITER:
            body = "\n".join(lines[index + 1 :]).strip()
            return metadata, body
        # Indented lines continue a multi-line `key: >` value.
        if folding_key and (line.startswith((" ", "\t")) or not line.strip()):
            metadata[folding_key] = f"{metadata[folding_key]} {line.strip()}".strip()
            continue
        folding_key = None
        key, _, value = line.partition(":")
        if key.strip():
            value = value.strip()
            if value in (">", "|", ">-", "|-"):
                folding_key, value = key.strip(), ""
            metadata[key.strip()] = value

    raise ValueError("Frontmatter starts with '---' but is never closed")
