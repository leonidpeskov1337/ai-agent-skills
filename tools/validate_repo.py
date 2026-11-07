"""Official metadata validation plus narrowly scoped repository invariants."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

from jsonschema import Draft202012Validator
from markdown_it import MarkdownIt
import yaml

ROOT = Path(__file__).resolve().parents[1]
SKIP = {
    ".git",
    ".idea",
    ".venv",
    "node_modules",
    "__pycache__",
    "dist",
    ".pytest_cache",
    ".ruff_cache",
}


class UniqueKeyLoader(yaml.SafeLoader):
    """Fail duplicate YAML keys instead of silently discarding earlier values."""


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f"Duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def ignored(path):
    return any(p in SKIP or p.startswith(".ci-") or p.endswith("-workspace") for p in path.parts)


def load_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"{path}: duplicate JSON key {key}")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError(f"{path}: invalid JSON constant {value}")

    return json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=invalid
    )


def skills(root=ROOT):
    registered = load_json(root / "tools/skills.json")["skills"]
    discovered = {
        p.parent.name for p in root.glob("*/SKILL.md") if not ignored(p.relative_to(root))
    }
    if set(registered) != discovered:
        raise ValueError(f"Skill registry differs from discovery: {set(registered) ^ discovered}")
    return registered


def official_validator():
    vendor = ROOT / "tools/vendor/anthropic"
    for name, digest in load_json(vendor / "UPSTREAM.json")["files"].items():
        if hashlib.sha256((vendor / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Vendored upstream file modified: {name}")
    spec = importlib.util.spec_from_file_location(
        "anthropic_validator", vendor / "quick_validate.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_skill


def require_path(base, reference, boundary):
    target = (base / unquote(reference)).resolve()
    if not target.is_relative_to(boundary.resolve()) or not target.exists():
        raise ValueError(f"{base}: broken or escaping reference {reference}")
    return target


def validate_skill(path):
    valid, message = official_validator()(path)
    if not valid:
        raise ValueError(f"{path}: {message}")
    content = (path / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = yaml.load(
        re.match(r"^---\n(.*?)\n---", content, re.DOTALL)[1], Loader=UniqueKeyLoader
    )
    if frontmatter["name"] != path.name or not frontmatter["description"].strip():
        raise ValueError(f"{path}: name must match directory and description must be nonempty")
    if "metadata" in frontmatter and (
        not isinstance(frontmatter["metadata"], dict)
        or any(
            not isinstance(k, str) or not isinstance(v, str)
            for k, v in frontmatter["metadata"].items()
        )
    ):
        raise ValueError(f"{path}: metadata must map strings to strings")
    for key in ("license", "compatibility", "allowed-tools"):
        if key in frontmatter and not isinstance(frontmatter[key], str):
            raise ValueError(f"{path}: {key} must be a string")
    for fixture in (path / "evals").rglob("*.json"):
        data = load_json(fixture)
        schema = None
        if fixture.name == "evals.json" or fixture.name.endswith("-evals.json"):
            schema = "evals"
            if data.get("skill_name") != path.name:
                raise ValueError(f"{fixture}: wrong skill_name")
            ids = [case.get("id") for case in data.get("evals", [])]
            if len(ids) != len(set(ids)):
                raise ValueError(f"{fixture}: duplicate evaluation IDs")
            if "fixture_file" in data:
                companion = load_json(require_path(fixture.parent, data["fixture_file"], path))
                if not isinstance(companion, list):
                    raise ValueError(f"{fixture}: companion must be an incident array")
                companion_ids = [item.get("id") for item in companion]
                if set(ids) != set(companion_ids) or len(companion_ids) != len(set(companion_ids)):
                    raise ValueError(f"{fixture}: evaluation/companion IDs differ or duplicate")
            for case in data.get("evals", []):
                for name in case.get("files", []):
                    require_path(path, name, path)
        elif fixture.name.endswith("fixtures.json"):
            schema = "incidents"
        if schema:
            Draft202012Validator(load_json(ROOT / f"tools/schemas/{schema}.schema.json")).validate(
                data
            )


def validate_files(root):
    parser = MarkdownIt()
    for directory, folders, filenames in os.walk(root):
        folders[:] = [folder for folder in folders if not ignored(Path(folder))]
        for folder in folders:
            if (Path(directory) / folder).is_symlink():
                raise ValueError(f"Symlink directory: {Path(directory) / folder}")
        for filename in filenames:
            path = Path(directory) / filename
            if ignored(path.relative_to(root)):
                continue
            validate_file(root, path, parser)


def validate_file(root, path, parser):
    if path.is_symlink():
        raise ValueError(f"Symlinks are not allowed: {path}")
    if not path.is_file():
        return
    if path.suffix in {".pyc", ".skill", ".pem", ".key"} or path.name == ".env":
        raise ValueError(f"Unexpected generated or sensitive file: {path}")
    if path.suffix == ".json":
        load_json(path)
    elif path.suffix in {".yaml", ".yml"}:
        list(yaml.load_all(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader))
    elif path.suffix == ".md":
        text = path.read_text(encoding="utf-8")
        for block in parser.parse(text):
            for token in block.children or []:
                if token.type not in {"link_open", "image"}:
                    continue
                url = token.attrGet("href") if token.type == "link_open" else token.attrGet("src")
                parts = urlsplit(url)
                if parts.scheme or parts.netloc or not parts.path:
                    continue
                boundary = root
                relative = path.relative_to(root)
                if len(relative.parts) > 1 and (root / relative.parts[0] / "SKILL.md").exists():
                    boundary = root / relative.parts[0]
                require_path(path.parent, parts.path, boundary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", choices=load_json(ROOT / "tools/skills.json")["skills"])
    args = parser.parse_args()
    names = skills()
    for name in [args.skill] if args.skill else names:
        validate_skill(ROOT / name)
        print(f"{name}: official and supplementary validation passed")
    validate_files(ROOT)
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    for name in filter(None, tracked):
        path = Path(name)
        if (
            ignored(path)
            or path.suffix in {".pyc", ".skill", ".pem", ".key"}
            or path.name == ".env"
        ):
            raise ValueError(f"Generated/cache/sensitive path tracked in Git: {name}")
    print(
        "JSON, YAML and relative file references passed (anchors and external URLs are not checked)"
    )


if __name__ == "__main__":
    main()
