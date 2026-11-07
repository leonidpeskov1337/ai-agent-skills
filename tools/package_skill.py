"""Build deterministic skill ZIPs with generic resources and an exclusion policy."""

import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tempfile
import zipfile

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.validate_repo import ROOT, relative_references, require_path, skills, validate_skill

CACHE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".tox",
    ".nox",
    "dist",
    "build",
    "tmp",
    "temp",
    ".cache",
    ".idea",
    ".vscode",
    ".codex",
    ".claude",
}
SENSITIVE_DIRS = {".aws", ".azure", ".kube", ".ssh", ".gnupg", ".terraform", ".docker"}
SENSITIVE_FILES = {
    ".env",
    ".envrc",
    ".npmrc",
    ".netrc",
    ".pypirc",
    "credentials",
    "credentials.json",
    "kubeconfig",
    "id_rsa",
    "id_ed25519",
    "terraform.tfstate",
    "terraform.tfstate.backup",
}
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
MAX_FILES = 10000


def excluded(relative, include_dev=False):
    parts = relative.parts
    lower = [p.lower() for p in parts]
    if any(p in SENSITIVE_DIRS for p in lower) or any(
        p in SENSITIVE_FILES
        or p.startswith(".env.")
        or p.endswith(
            (".pem", ".key", ".p12", ".pfx", ".tfstate", ".tfstate.backup", ".kubeconfig")
        )
        for p in lower
    ):
        raise ValueError(f"Sensitive package input: {relative}")
    if any(p in CACHE_DIRS or p.startswith(".ci-") or p.endswith("-workspace") for p in lower):
        return True
    if relative.name in {".DS_Store", "Thumbs.db", "desktop.ini", ".coverage"}:
        return True
    if relative.name.endswith((".pyc", ".pyo", ".skill", ".skill.sha256", ".tmp", ".swp", "~")):
        return True
    return not include_dev and parts[0] in {"tests", "evals"}


def package_files(skill, include_dev=False):
    if skill.is_symlink():
        raise ValueError("Skill directory must not be a symlink")
    included, omitted, total = [], [], 0
    for directory, folders, filenames in os.walk(skill, followlinks=False):
        for name in folders[:] + filenames:
            path = Path(directory) / name
            relative = path.relative_to(skill)
            if path.is_symlink():
                raise ValueError(f"Symlink in package: {relative}")
            skip = excluded(relative, include_dev)
            if name in folders:
                if skip:
                    folders.remove(name)
                    omitted.append(relative)
                continue
            if skip:
                omitted.append(relative)
                continue
            info = path.stat()
            if not stat.S_ISREG(info.st_mode):
                raise ValueError(f"Non-regular resource: {relative}")
            total += info.st_size
            if (
                info.st_size > MAX_FILE_BYTES
                or total > MAX_TOTAL_BYTES
                or len(included) >= MAX_FILES
            ):
                raise ValueError(f"Package resource limit exceeded: {relative}")
            included.append(path)
    return sorted(included), omitted


def check_references(skill, included):
    names = {p.relative_to(skill).as_posix() for p in included}
    for source in included:
        if source.suffix.lower() != ".md":
            continue
        for reference in relative_references(source):
            target = require_path(source.parent, reference, skill)
            relative = target.relative_to(skill.resolve()).as_posix()
            present = (
                relative in names
                if target.is_file()
                else any(name.startswith(relative.rstrip("/") + "/") for name in names)
            )
            if not present:
                raise ValueError(
                    f"{source}: reference excluded from package: {reference}; "
                    "use --include-dev for required development resources"
                )


def scan(included, skill):
    filename = "gitleaks.exe" if os.name == "nt" else "gitleaks"
    binary = ROOT / ".ci-bin/gitleaks" / filename
    if not binary.is_file():
        raise ValueError("Install Gitleaks with python -m tools.install_binary gitleaks")
    # Scan the exact archive payload; caches excluded from it cannot suppress a runtime file.
    with tempfile.TemporaryDirectory(prefix="skill-package-scan-") as directory:
        for source in included:
            target = Path(directory) / source.relative_to(skill)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(resource_bytes(source))
        subprocess.run(
            [
                str(binary),
                "dir",
                "--redact",
                "--no-banner",
                "--config",
                str(ROOT / ".gitleaks.toml"),
                str(directory),
            ],
            check=True,
            cwd=directory,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def resource_bytes(path):
    with path.open("rb") as stream:
        data = stream.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"Resource changed beyond size limit: {path}")
    return data


def package(skill, output, include_dev=False, scan_secrets=False):
    if skill.is_symlink():
        raise ValueError("Skill directory must not be a symlink")
    skill = skill.resolve()
    if output.resolve().is_relative_to(skill):
        raise ValueError("Package output must be outside the skill directory")
    validate_skill(skill)
    included, omitted = package_files(skill, include_dev)
    for relative in omitted:
        print(f"Excluded from runtime package: {str(relative)!r}")
    check_references(skill, included)
    if scan_secrets:
        scan(included, skill)
    output.mkdir(parents=True, exist_ok=True)
    archive_path = output / f"{skill.name}.skill"
    written = 0
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in included:
            data = resource_bytes(path)
            written += len(data)
            if written > MAX_TOTAL_BYTES:
                raise ValueError("Resource changed beyond size limit while packaging")
            info = zipfile.ZipInfo(
                f"{skill.name}/{path.relative_to(skill).as_posix()}", (2026, 1, 1, 0, 0, 0)
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    verify(archive_path, skill, include_dev)
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    archive_path.with_suffix(".skill.sha256").write_text(
        f"{digest}  {archive_path.name}\n", encoding="ascii"
    )
    print(f"{archive_path}: {len(included)} files; {len(omitted)} excluded paths; SHA256 {digest}")
    return archive_path


def verify(archive_path, skill, include_dev=False):
    expected, _ = package_files(skill, include_dev)
    expected_names = {f"{skill.name}/{p.relative_to(skill).as_posix()}" for p in expected}
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != expected_names:
            raise ValueError("Unexpected, missing or duplicate archive entries")
        total = 0
        for entry in archive.infolist():
            name = entry.filename
            path = PurePosixPath(name)
            if (
                "\\" in name
                or path.is_absolute()
                or ".." in path.parts
                or ":" in name
                or path.parts[0] != skill.name
            ):
                raise ValueError(f"Unsafe archive entry: {name}")
            if stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError("Symlink archive entry")
            total += entry.file_size
            if entry.file_size > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                raise ValueError("Archive resource limit exceeded")
            if archive.read(name) != (skill.parent / name).read_bytes():
                raise ValueError(f"Archive contents differ: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill", nargs="?", choices=skills())
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--include-dev", action="store_true")
    parser.add_argument("--scan-secrets", action="store_true")
    args = parser.parse_args()
    for name in [args.skill] if args.skill else skills():
        package(ROOT / name, args.output, args.include_dev, args.scan_secrets)


if __name__ == "__main__":
    main()
