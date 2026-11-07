"""Thin Claude Code execution adapter: paired offline tasks, artifacts and human rubrics.

This deliberately does not reimplement a model grader. Agent Skills' existing
assertion-based human review remains the acceptance authority for behavior.
"""

import argparse
import json
import os
from pathlib import Path
import shutil
import platform
import subprocess
import tempfile
import time

from tools.validate_repo import ROOT, load_json, skills


def evaluate(skill, cli, output):
    cases = load_json(ROOT / "tools/model_cases.json")[skill]
    output.mkdir(parents=True, exist_ok=True)
    results = []
    failed = False
    for case in cases:
        for condition in ("baseline", "with-skill"):
            with tempfile.TemporaryDirectory(prefix="skills-eval-") as directory:
                work = Path(directory)
                (work / "evidence.json").write_text(json.dumps(case["evidence"]), encoding="utf-8")
                prompt = case["prompt"]
                if condition == "with-skill":
                    shutil.copytree(
                        ROOT / skill,
                        work / "skill",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests", "evals"),
                    )
                    prompt += (
                        " Read skill/SKILL.md first; load supporting resources only as needed."
                    )
                else:
                    prompt = prompt.replace(" and use the supplied skill", "")
                # A real agent executes Read calls against isolated synthetic files.
                # No shell, write, web, MCP, cloud or infrastructure tools are exposed.
                command = [
                    str(cli),
                    "-p",
                    prompt,
                    "--output-format",
                    "stream-json",
                    "--verbose",
                    "--bare",
                    "--model",
                    "claude-sonnet-4-6",
                    "--tools",
                    "Read",
                    "--allowedTools",
                    "Read(./**)",
                    "--setting-sources",
                    "",
                    "--disable-slash-commands",
                    "--no-session-persistence",
                    "--max-turns",
                    "8",
                    "--max-budget-usd",
                    "1.00",
                ]
                env = {
                    k: v
                    for k, v in os.environ.items()
                    if k in {"PATH", "HOME", "TMPDIR", "SYSTEMROOT", "ANTHROPIC_API_KEY"}
                }
                env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
                env["HOME"] = str(work / "home")
                env["CLAUDE_CONFIG_DIR"] = str(work / "home/.claude")
                started = time.monotonic()
                record = {
                    "id": case["id"],
                    "condition": condition,
                    "assertions": case["assertions"],
                }
                try:
                    completed = subprocess.run(
                        command, cwd=work, env=env, capture_output=True, text=True, timeout=240
                    )
                    events = [
                        json.loads(line) for line in completed.stdout.splitlines() if line.strip()
                    ]
                    response = next(
                        (event for event in reversed(events) if event.get("type") == "result"), None
                    )
                    record.update(transcript=events, response=response, status="needs-human-review")
                    if completed.returncode or response is None or response.get("is_error"):
                        record["status"] = "infrastructure-or-provider-error"
                        failed = True
                except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as error:
                    record.update(
                        status="infrastructure-or-provider-error", error=type(error).__name__
                    )
                    failed = True
                record["wall_seconds"] = round(time.monotonic() - started, 3)
                results.append(record)
    report = {
        "skill": skill,
        "model": "claude-sonnet-4-6",
        "budget_usd_per_call": 1.0,
        "commit": os.environ.get("GITHUB_SHA", "local"),
        "results": results,
        "limits": "Offline Read-only tasks. Human rubric grading required; no automatic semantic pass claimed.",
    }
    (output / f"{skill}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if failed:
        raise SystemExit(
            "Model infrastructure/provider error; see saved report. This is not a behavioral grade."
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill", choices=skills())
    parser.add_argument("--output", type=Path, default=ROOT / "model-results")
    args = parser.parse_args()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("Missing ANTHROPIC_API_KEY; paid model evaluation was not executed")
    system = platform.system()
    if platform.machine().lower() not in {"x86_64", "amd64"} or system not in {"Linux", "Windows"}:
        raise SystemExit("This evaluation adapter supports x86-64 Linux/Windows")
    suffix = "win32-x64/claude.exe" if system == "Windows" else "linux-x64/claude"
    cli = ROOT / f".github/model-evals/node_modules/@anthropic-ai/claude-code-{suffix}"
    if not cli.is_file():
        raise SystemExit("Run npm ci --ignore-scripts in .github/model-evals first")
    evaluate(args.skill, cli, args.output)


if __name__ == "__main__":
    main()
