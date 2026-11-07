"""Execute the actual required-gate shell across skipped, failed and successful jobs."""

import os
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

from tools.validate_repo import ROOT


@pytest.mark.parametrize(
    "overrides,passed",
    [
        ({}, True),
        ({"TESTS": "skipped", "HAS_SKILLS": "false"}, True),
        ({"POLICY": "skipped", "EVENT_NAME": "push"}, True),
        ({"STRUCTURE": "failure"}, False),
        ({"QUALITY": "failure"}, False),
        ({"SECURITY": "cancelled"}, False),
        ({"POLICY": "skipped"}, False),
        ({"TESTS": "skipped"}, False),
        ({"TESTS": "failure"}, False),
        ({"HAS_SKILLS": "false"}, False),
    ],
)
def test_required_gate_outcomes(overrides, passed):
    bash = shutil.which("bash") if os.name != "nt" else "C:/Program Files/Git/bin/bash.exe"
    if not bash or not Path(bash).is_file():
        pytest.skip("Bash is required to test the actual GitHub gate script")
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    gate = workflow["jobs"]["gate"]
    assert gate["if"] == "always()"
    env = {
        **os.environ,
        "POLICY": "success",
        "STRUCTURE": "success",
        "TESTS": "success",
        "QUALITY": "success",
        "SECURITY": "success",
        "EVENT_NAME": "pull_request",
        "HAS_SKILLS": "true",
        **overrides,
    }
    result = subprocess.run(
        [bash, "-e", "-c", gate["steps"][0]["run"]], env=env, capture_output=True, text=True
    )
    assert (result.returncode == 0) is passed
