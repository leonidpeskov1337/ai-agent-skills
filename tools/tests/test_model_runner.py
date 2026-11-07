"""Exercise the paid-evaluation adapter without contacting any model provider."""

import json
import subprocess

import pytest

from tools.run_model_evals import evaluate


def test_model_runner_isolates_baseline_and_limits_tools(tmp_path, monkeypatch):
    calls = []

    def run(command, **kwargs):
        work = kwargs["cwd"]
        assert (work / "evidence.json").is_file()
        assert command[command.index("--tools") + 1] == "Read"
        assert command[command.index("--max-budget-usd") + 1] == "1.00"
        assert "--bare" in command
        assert "KUBECONFIG" not in kwargs["env"]
        assert "GITHUB_TOKEN" not in kwargs["env"]
        calls.append((work / "skill/SKILL.md").is_file())
        event = {"type": "result", "is_error": False, "total_cost_usd": 0.02, "result": "Report"}
        return subprocess.CompletedProcess(command, 0, json.dumps(event))

    monkeypatch.setenv("KUBECONFIG", "/private/config")
    monkeypatch.setenv("GITHUB_TOKEN", "synthetic-should-not-inherit")
    monkeypatch.setattr(subprocess, "run", run)
    evaluate("kubernetes-troubleshooter", tmp_path / "unused", tmp_path / "reports")
    assert calls == [False, True]
    data = json.loads((tmp_path / "reports/kubernetes-troubleshooter.json").read_text())
    assert all(item["status"] == "needs-human-review" for item in data["results"])


def test_model_provider_failure_is_saved_and_fails_job(tmp_path, monkeypatch):
    def run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 240)

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(SystemExit, match="infrastructure/provider"):
        evaluate("gitlab-security-policies", tmp_path / "unused", tmp_path / "reports")
    data = json.loads((tmp_path / "reports/gitlab-security-policies.json").read_text())
    assert all(item["status"] == "infrastructure-or-provider-error" for item in data["results"])
