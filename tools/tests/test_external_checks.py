"""Prove real linters reject representative broken code and unsafe workflows."""

from pathlib import Path
import shutil
import secrets
import string
import subprocess
import sys

import pytest

from tools.validate_repo import ROOT


def test_ruff_rejects_undefined_name(tmp_path):
    path = tmp_path / "broken.py"
    path.write_text("print(does_not_exist)\n")
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--isolated", str(path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "F821" in result.stdout


def test_actionlint_rejects_invalid_expression(tmp_path):
    filename = "actionlint.exe" if sys.platform == "win32" else "actionlint"
    binary = ROOT / ".ci-bin/actionlint" / filename
    if not binary.is_file():
        pytest.skip("Install the checksum-pinned actionlint binary first")
    path = tmp_path / "broken.yml"
    path.write_text(
        "name: broken\non: push\njobs:\n  test:\n    runs-on: ubuntu-24.04\n"
        "    steps:\n      - run: echo ${{ nonexistent.value }}\n"
    )
    result = subprocess.run([str(binary), str(path)], capture_output=True, text=True)
    assert result.returncode != 0
    assert "nonexistent" in result.stdout


def test_zizmor_rejects_pr_title_shell_injection(tmp_path):
    filename = "zizmor.exe" if sys.platform == "win32" else "zizmor"
    binary = shutil.which(filename) or str(Path(sys.executable).parent / filename)
    path = tmp_path / "unsafe.yml"
    path.write_text(
        "name: unsafe\non: pull_request\npermissions: read-all\njobs:\n  test:\n"
        "    runs-on: ubuntu-24.04\n    steps:\n"
        "      - run: echo '${{ github.event.pull_request.title }}'\n"
    )
    result = subprocess.run(
        [binary, "--offline", "--format", "json", str(path)], capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "template-injection" in result.stdout


def test_gitleaks_rejects_and_redacts_synthetic_token(tmp_path):
    filename = "gitleaks.exe" if sys.platform == "win32" else "gitleaks"
    binary = ROOT / ".ci-bin/gitleaks" / filename
    if not binary.is_file():
        pytest.skip("Install the checksum-pinned Gitleaks binary first")
    # A generated, nonfunctional token exercises detection without committing a matching secret.
    token = "ghp_" + "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(36)
    )
    (tmp_path / "synthetic.txt").write_text(f"github_token = {token}\n")
    result = subprocess.run(
        [str(binary), "dir", "--redact", "--no-banner", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert token not in result.stdout + result.stderr
