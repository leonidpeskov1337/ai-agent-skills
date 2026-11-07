"""Generic resources, exclusion boundaries and zero-configuration onboarding."""

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest

from tools.package_skill import package
from tools.validate_repo import ROOT, skills, validate_files, validate_skill


@pytest.fixture
def runtime_skill(tmp_path):
    skill = tmp_path / "third-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: third-skill\ndescription: Diagnose synthetic issues when requested.\n---\n\n[Guide](references/guide.md)\n"
    )
    resources = [
        "scripts/check.py",
        "references/guide.md",
        "templates/policy.yaml",
        "assets/diagram.svg",
        "assets/example.pdf",
        "queries/diagnostic.sql",
        "terraform/main.tf",
        "schemas/config.proto",
        "nested/custom/resource.dat",
    ]
    for name in resources:
        path = skill / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            b"synthetic resource\x00" if name.endswith(".dat") else b"synthetic resource\n"
        )
    (skill / "templates/policy.yaml").write_text("mode: synthetic\n")
    return skill


def test_arbitrary_resources_and_reproducibility(runtime_skill, tmp_path):
    expected = {
        p.relative_to(runtime_skill).as_posix() for p in runtime_skill.rglob("*") if p.is_file()
    }
    first = package(runtime_skill, tmp_path / "one")
    second = package(runtime_skill, tmp_path / "two")
    assert (
        hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(second.read_bytes()).digest()
    )
    with zipfile.ZipFile(first) as archive:
        assert {p.removeprefix("third-skill/") for p in archive.namelist()} == expected


@pytest.mark.parametrize(
    "name",
    [
        ".env",
        ".env.production",
        ".aws/credentials",
        ".kube/config",
        "keys/client.pem",
        ".npmrc",
        "terraform.tfstate",
    ],
)
def test_sensitive_inputs_rejected(runtime_skill, tmp_path, name):
    path = runtime_skill / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("synthetic credential container")
    with pytest.raises(ValueError, match="Sensitive"):
        package(runtime_skill, tmp_path / "out")


def test_cache_and_generated_inputs_excluded(runtime_skill, tmp_path):
    for name in [".venv/site.py", "custom/__pycache__/x.pyc", "build/output.bin", "scratch.tmp"]:
        path = runtime_skill / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("development only")
    archive = package(runtime_skill, tmp_path / "out")
    with zipfile.ZipFile(archive) as packaged:
        assert not any(
            p.endswith(("site.py", "x.pyc", "output.bin", ".tmp")) for p in packaged.namelist()
        )


def test_referenced_excluded_resource_fails_loudly(runtime_skill, tmp_path):
    path = runtime_skill / "tests/fixture.txt"
    path.parent.mkdir()
    path.write_text("required data")
    (runtime_skill / "references/guide.md").write_text("[Required](../tests/fixture.txt)\n")
    with pytest.raises(ValueError, match="reference excluded"):
        package(runtime_skill, tmp_path / "out")
    package(runtime_skill, tmp_path / "dev", include_dev=True)


def test_symlink_rejected(runtime_skill, tmp_path):
    try:
        (runtime_skill / "link").symlink_to(runtime_skill / "SKILL.md")
    except OSError:
        pytest.skip("Host does not grant symlink creation; Linux CI exercises this case")
    with pytest.raises(ValueError, match="Symlink"):
        package(runtime_skill, tmp_path / "out")


def test_escaping_reference_and_oversized_resource_rejected(runtime_skill, tmp_path, monkeypatch):
    (runtime_skill / "references/guide.md").write_text("[Escape](../../outside.txt)")
    with pytest.raises(ValueError, match="reference"):
        package(runtime_skill, tmp_path / "out")
    (runtime_skill / "references/guide.md").write_text("guide")
    monkeypatch.setattr("tools.package_skill.MAX_FILE_BYTES", 16)
    with pytest.raises(ValueError, match="limit"):
        package(runtime_skill, tmp_path / "out")


def test_exact_payload_secret_scan_rejects_token(runtime_skill, tmp_path):
    import secrets
    import string

    binary = ROOT / ".ci-bin/gitleaks" / ("gitleaks.exe" if os.name == "nt" else "gitleaks")
    if not binary.exists():
        pytest.skip("Install Gitleaks to exercise payload scanning")
    token = "ghp_" + "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(36)
    )
    (runtime_skill / "nested/token.dat").write_text(token)
    with pytest.raises(subprocess.CalledProcessError):
        package(runtime_skill, tmp_path / "out", scan_secrets=True)


def test_new_skill_normal_commands_without_configuration_edits(runtime_skill, tmp_path):
    # Disposable repository with the actual shared tools and pytest configuration.
    shutil.copytree(
        ROOT / "tools", tmp_path / "tools", ignore=shutil.ignore_patterns("__pycache__")
    )
    shutil.copy(ROOT / "pyproject.toml", tmp_path)
    tests = runtime_skill / "tests"
    tests.mkdir()
    (tests / "test_example.py").write_text("def test_third_skill():\n    assert 2 + 2 == 4\n")
    assert skills(tmp_path) == ["third-skill"]
    validate_skill(runtime_skill)
    validate_files(runtime_skill)
    git = shutil.which("git") or "C:/Program Files/Git/cmd/git.exe"
    subprocess.run([git, "init", str(tmp_path)], check=True, capture_output=True)
    env = {
        **os.environ,
        "PYTHONPATH": str(tmp_path),
        "PATH": str(Path(git).parent) + os.pathsep + os.environ["PATH"],
    }
    for command in [
        [sys.executable, "-m", "tools.validate_repo"],
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        [sys.executable, "-m", "tools.package_skill", "third-skill"],
    ]:
        result = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        if "pytest" in command:
            assert "third-skill/tests/test_example.py::test_third_skill" in result.stdout.replace(
                "\\", "/"
            )
