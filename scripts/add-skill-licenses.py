#!/usr/bin/env python3
"""Add missing license fields to NetClaw skill SKILL.md files.

This script scans all SKILL.md files in the workspace/skills directory
and adds a 'license: Apache-2.0' field if missing from the YAML frontmatter.

Usage:
    python3 scripts/add-skill-licenses.py [--dry-run] [--license LICENSE]

Options:
    --dry-run    Show what would be changed without modifying files
    --license    License to add (default: Apache-2.0)
"""

import argparse
import re
import sys
from pathlib import Path


def parse_frontmatter(content: str) -> tuple[str | None, str]:
    """Extract YAML frontmatter from markdown content.

    Returns:
        Tuple of (frontmatter string or None, remaining content)
    """
    if not content.startswith("---"):
        return None, content

    # Find the closing ---
    match = re.match(r"^---\n(.*?)\n---\n?(.*)$", content, re.DOTALL)
    if not match:
        return None, content

    return match.group(1), match.group(2)


def has_license_field(frontmatter: str) -> bool:
    """Check if frontmatter already has a license field."""
    return bool(re.search(r"^license:", frontmatter, re.MULTILINE))


def add_license_field(frontmatter: str, license_id: str) -> str:
    """Add license field after version line in frontmatter."""
    lines = frontmatter.split("\n")
    new_lines = []
    license_added = False

    for line in lines:
        new_lines.append(line)
        # Add license after version line
        if line.startswith("version:") and not license_added:
            new_lines.append(f"license: {license_id}")
            license_added = True

    # If no version line found, add license after description
    if not license_added:
        new_lines = []
        for line in lines:
            new_lines.append(line)
            if line.startswith("description:") and not license_added:
                new_lines.append(f"license: {license_id}")
                license_added = True

    # Last resort: add at end of frontmatter
    if not license_added:
        new_lines.append(f"license: {license_id}")

    return "\n".join(new_lines)


def extract_name_and_description(content: str, skill_name: str) -> tuple[str, str]:
    """Extract name and description from markdown content without frontmatter."""
    lines = content.strip().split("\n")
    description = ""

    # Look for first heading and following paragraph
    for i, line in enumerate(lines):
        if line.startswith("# "):
            # Found heading, look for description in next non-empty line
            for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip() and not lines[j].startswith("#"):
                    description = lines[j].strip()
                    break
            break

    if not description:
        description = f"{skill_name.replace('-', ' ').title()} skill"

    return skill_name, description


def create_frontmatter(skill_name: str, description: str, license_id: str) -> str:
    """Create a new frontmatter block for a skill."""
    return f"""name: {skill_name}
description: "{description}"
version: 1.0.0
license: {license_id}
author: netclaw
tags: []"""


def process_skill_file(skill_path: Path, license_id: str, dry_run: bool, add_frontmatter: bool = False) -> bool:
    """Process a single SKILL.md file.

    Returns:
        True if file was modified (or would be in dry-run mode)
    """
    content = skill_path.read_text()
    skill_name = skill_path.parent.name
    frontmatter, body = parse_frontmatter(content)

    if frontmatter is None:
        if not add_frontmatter:
            print(f"  SKIP: {skill_name} - no frontmatter (use --add-frontmatter)")
            return False

        # Create new frontmatter
        name, description = extract_name_and_description(content, skill_name)
        new_frontmatter = create_frontmatter(name, description, license_id)
        new_content = f"---\n{new_frontmatter}\n---\n\n{content}"

        if dry_run:
            print(f"  WOULD CREATE: {skill_name} - new frontmatter with license: {license_id}")
        else:
            skill_path.write_text(new_content)
            print(f"  CREATED: {skill_name} - new frontmatter with license: {license_id}")
        return True

    if has_license_field(frontmatter):
        print(f"  OK: {skill_name} - already has license")
        return False

    # Add license field
    new_frontmatter = add_license_field(frontmatter, license_id)
    new_content = f"---\n{new_frontmatter}\n---\n{body}"

    if dry_run:
        print(f"  WOULD ADD: {skill_name} - license: {license_id}")
    else:
        skill_path.write_text(new_content)
        print(f"  ADDED: {skill_name} - license: {license_id}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Add missing license fields to skill files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change")
    parser.add_argument("--license", default="Apache-2.0", help="License identifier (default: Apache-2.0)")
    parser.add_argument("--path", default=None, help="Path to skills directory")
    parser.add_argument("--add-frontmatter", action="store_true", help="Add frontmatter to files without it")
    args = parser.parse_args()

    # Find skills directory
    if args.path:
        skills_dir = Path(args.path)
    else:
        # Try netclaw workspace first, then openclaw
        script_dir = Path(__file__).parent
        netclaw_skills = script_dir.parent / "workspace" / "skills"
        if netclaw_skills.exists():
            skills_dir = netclaw_skills
        else:
            # Fallback to user's openclaw workspace
            skills_dir = Path.home() / ".openclaw" / "workspace" / "skills"

    if not skills_dir.exists():
        print(f"ERROR: Skills directory not found: {skills_dir}")
        sys.exit(1)

    print(f"Scanning skills in: {skills_dir}")
    print(f"License to add: {args.license}")
    if args.dry_run:
        print("DRY RUN - no files will be modified\n")
    print()

    # Find all SKILL.md files
    skill_files = sorted(skills_dir.glob("*/SKILL.md"))

    if not skill_files:
        print("No SKILL.md files found")
        sys.exit(0)

    modified = 0
    skipped = 0
    already_ok = 0

    for skill_path in skill_files:
        result = process_skill_file(skill_path, args.license, args.dry_run, args.add_frontmatter)
        if result:
            modified += 1
        else:
            content = skill_path.read_text()
            frontmatter, _ = parse_frontmatter(content)
            if frontmatter and has_license_field(frontmatter):
                already_ok += 1
            else:
                skipped += 1

    print()
    print(f"Summary: {len(skill_files)} skills scanned")
    print(f"  {modified} {'would be modified' if args.dry_run else 'modified'}")
    print(f"  {already_ok} already have license")
    print(f"  {skipped} skipped (no frontmatter)")


if __name__ == "__main__":
    main()
