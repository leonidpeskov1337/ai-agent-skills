"""Render the README catalog from discovered skill metadata; preserve surrounding prose."""

import argparse
import html
import re
from urllib.parse import quote

import yaml

from tools.validate_repo import ROOT, UniqueKeyLoader, skills

START = "<!-- skill-catalog:start -->"
END = "<!-- skill-catalog:end -->"


def cell(value):
    text = html.escape(" ".join(value.split()), quote=False)
    return re.sub(r"([\\`*_\[\]|])", r"\\\1", text)


def catalog(root):
    rows = [START, "", "| Skill | What it helps you do | Start here |", "| --- | --- | --- |"]
    for name in skills(root):
        path = root / name
        source = (path / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---", source, re.DOTALL)
        if not match:
            raise ValueError(f"{name}: missing frontmatter")
        metadata = yaml.load(match[1], Loader=UniqueKeyLoader)
        interface = {}
        if (path / "agents/openai.yaml").is_file():
            interface = yaml.load(
                (path / "agents/openai.yaml").read_text(encoding="utf-8"), Loader=UniqueKeyLoader
            ).get("interface", {})
        title = interface.get("display_name") or metadata["name"]
        description = interface.get("short_description") or metadata["description"]
        description = " ".join(description.split())
        if len(description) > 220:
            description = description[:217].rsplit(" ", 1)[0] + "…"
        guide = "README.md" if (path / "README.md").is_file() else "SKILL.md"
        prompt = (
            f"[Prompt template]({quote(name)}/prompt.md)"
            if (path / "prompt.md").is_file()
            else f"[Instructions]({quote(name)}/SKILL.md)"
        )
        rows.append(f"| [{cell(title)}]({quote(name)}/{guide}) | {cell(description)} | {prompt} |")
    return "\n".join([*rows, "", END])


def updated_readme(root):
    path = root / "README.md"
    source = path.read_text(encoding="utf-8")
    if (
        source.count(START) != 1
        or source.count(END) != 1
        or source.index(END) < source.index(START)
    ):
        raise ValueError("README must contain one ordered pair of skill-catalog markers")
    start = source.index(START)
    end = source.index(END) + len(END)
    return source[:start] + catalog(root) + source[end:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Fail when the committed catalog is stale"
    )
    args = parser.parse_args()
    expected = updated_readme(ROOT)
    path = ROOT / "README.md"
    if args.check:
        if path.read_text(encoding="utf-8") != expected:
            raise SystemExit("README catalog is stale. Run: python -m tools.update_catalog")
        print("README skill catalog is current")
    else:
        path.write_text(expected, encoding="utf-8", newline="\n")
        print("Updated README skill catalog")


if __name__ == "__main__":
    main()
