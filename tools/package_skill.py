"""Build deterministic, independently installable skill ZIPs and SHA-256 checksums."""

import argparse
import hashlib
from pathlib import Path
import sys
import zipfile

# Retain the original `python tools/package_skill.py` invocation.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.validate_repo import ROOT, ignored, load_json, validate_skill

FOLDERS = {
    "agents",
    "scripts",
    "references",
    "playbooks",
    "examples",
    "evals",
    "tests",
    "ArgoCD",
    "assets",
}
SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".txt", ".svg", ".png", ".jpg"}


def package(skill, output):
    validate_skill(skill)
    included = []
    for path in sorted(skill.rglob("*")):
        relative = path.relative_to(skill)
        if path.is_symlink():
            raise ValueError(f"Symlink in package: {path}")
        if ignored(relative) or not path.is_file():
            continue
        if (
            len(relative.parts) > 1 and relative.parts[0] not in FOLDERS
        ) or path.suffix not in SUFFIXES:
            raise ValueError(f"Unexpected package input: {path}")
        if any(p.startswith(".") for p in relative.parts):
            raise ValueError(f"Hidden package input: {path}")
        included.append(path)
    output.mkdir(parents=True, exist_ok=True)
    archive_path = output / f"{skill.name}.skill"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in included:
            info = zipfile.ZipInfo(
                f"{skill.name}/{path.relative_to(skill).as_posix()}", (2026, 1, 1, 0, 0, 0)
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    verify(archive_path, skill)
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    archive_path.with_suffix(".skill.sha256").write_text(
        f"{digest}  {archive_path.name}\n", encoding="ascii"
    )
    print(f"{archive_path}: {len(included)} files; SHA256 {digest}")
    return archive_path


def verify(archive_path, skill):
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if archive.testzip() is not None or f"{skill.name}/SKILL.md" not in names:
            raise ValueError("Invalid archive or missing SKILL.md")
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archive entries")
        for name in names:
            path = Path(name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or path.parts[0] != skill.name
                or ignored(path)
            ):
                raise ValueError(f"Unsafe archive entry: {name}")
            source = skill.parent / path
            if archive.read(name) != source.read_bytes():
                raise ValueError(f"Archive contents differ: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "skill",
        nargs="?",
        default="kubernetes-troubleshooter",
        choices=load_json(ROOT / "tools/skills.json")["skills"],
    )
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    package(ROOT / args.skill, args.output)


if __name__ == "__main__":
    main()
