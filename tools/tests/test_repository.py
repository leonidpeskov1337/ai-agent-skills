"""Acceptance tests for invariants the upstream metadata validator doesn't cover."""

import hashlib
import json
import zipfile

import pytest
from jsonschema import ValidationError

from tools.changed_skills import select
from tools.package_skill import package, verify
from tools.release_target import parse_tag
from tools.validate_repo import load_json, skills, validate_files, validate_skill


@pytest.fixture
def skill(tmp_path):
    path = tmp_path / "example-skill"
    path.mkdir()
    (path / "SKILL.md").write_text(
        "---\nname: example-skill\ndescription: Diagnose synthetic incidents when asked.\n---\n\nInstructions.\n",
        encoding="utf-8",
    )
    return path


def test_valid_minimal_skill(skill):
    validate_skill(skill)


@pytest.mark.parametrize(
    "text",
    [
        "# No metadata",
        "---\nname: [bad\n---\n",
        "---\nname: example-skill\n---\n",
        "---\nname: Other\ndescription: Test\n---\n",
        "---\nname: wrong-folder\ndescription: Test\n---\n",
        "---\nname: example-skill\ndescription: ''\n---\n",
    ],
)
def test_invalid_metadata(skill, text):
    (skill / "SKILL.md").write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        validate_skill(skill)


def test_missing_skill(skill):
    (skill / "SKILL.md").unlink()
    with pytest.raises(ValueError, match="not found"):
        validate_skill(skill)


def test_deleted_registered_skill(tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools/skills.json").write_text('{"skills":["missing-skill"]}')
    with pytest.raises(ValueError, match="registry"):
        skills(tmp_path)


def test_file_links_and_code_examples(skill):
    (skill / "guide.md").write_text("[Missing](missing.md)\n", encoding="utf-8")
    with pytest.raises(ValueError, match="reference"):
        validate_files(skill)
    (skill / "guide.md").write_text("```md\n[Example](missing.md)\n```\n", encoding="utf-8")
    validate_files(skill)
    (skill / "guide.md").write_text("[Escape](../outside.md)\n", encoding="utf-8")
    with pytest.raises(ValueError):
        validate_files(skill)


@pytest.mark.parametrize("data", ['{"bad":', '{"key":1,"key":2}', '{"nan":NaN}'])
def test_invalid_json(skill, data):
    path = skill / "bad.json"
    path.write_text(data)
    with pytest.raises(ValueError):
        load_json(path)


def test_invalid_yaml(skill):
    (skill / "bad.yaml").write_text("bad: [unclosed")
    with pytest.raises(Exception):
        validate_files(skill)


def test_duplicate_yaml_keys(skill):
    (skill / "bad.yaml").write_text("key: first\nkey: discarded\n")
    with pytest.raises(ValueError, match="Duplicate YAML"):
        validate_files(skill)


def test_duplicate_frontmatter_keys(skill):
    (skill / "SKILL.md").write_text(
        "---\nname: example-skill\nname: example-skill\ndescription: Synthetic task\n---\n"
    )
    with pytest.raises(ValueError, match="Duplicate YAML"):
        validate_skill(skill)


def test_eval_schema_and_references(skill):
    folder = skill / "evals"
    folder.mkdir()
    path = folder / "evals.json"
    case = {
        "id": 1,
        "prompt": "Diagnose",
        "expected_output": "Qualified assessment",
        "assertions": ["No mutation"],
    }
    data = {"skill_name": skill.name, "evals": [case]}
    path.write_text(json.dumps(data))
    validate_skill(skill)
    case["files"] = ["evals/missing.json"]
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="reference"):
        validate_skill(skill)
    del case["files"]
    del case["assertions"]
    path.write_text(json.dumps(data))
    with pytest.raises(ValidationError):
        validate_skill(skill)


def test_package_is_reproducible_and_includes_nested_fixture(skill, tmp_path):
    fixture = skill / "tests/fixtures/good.json"
    fixture.parent.mkdir(parents=True)
    fixture.write_text('{"safe":true}')
    cache = skill / "scripts/__pycache__/ignored.pyc"
    cache.parent.mkdir(parents=True)
    cache.write_bytes(b"cache")
    first = package(skill, tmp_path / "one")
    second = package(skill, tmp_path / "two")
    assert first.read_bytes() == second.read_bytes()
    digest = hashlib.sha256(first.read_bytes()).hexdigest()
    assert first.with_suffix(".skill.sha256").read_text().startswith(digest)
    with zipfile.ZipFile(first) as archive:
        assert f"{skill.name}/tests/fixtures/good.json" in archive.namelist()
        assert not any("__pycache__" in name for name in archive.namelist())
    with zipfile.ZipFile(first, "a") as archive:
        archive.writestr("../escape", "bad")
    with pytest.raises(ValueError):
        verify(first, skill)


def test_package_rejects_unknown_and_sensitive_inputs(skill, tmp_path):
    (skill / ".env").write_text("TOKEN=example")
    with pytest.raises(ValueError):
        package(skill, tmp_path / "out")


def test_change_detection():
    names = ["a-skill", "b-skill"]
    assert select(["README.md", "docs/ci.md"], names) == []
    assert select(["a-skill/scripts/check.py"], names) == ["a-skill"]
    assert select(["tools/shared.py"], names) == names
    assert select([".github/workflows/ci.yml"], names) == names
    assert select(["a-skill/README.md"], names) == ["a-skill"]
    assert select(["new-skill/SKILL.md"], names) == names


@pytest.mark.parametrize("tag", ["a-skill/v1.2.3", "a-skill/v0.0.1"])
def test_release_tag_accepts_registered_skill(tag):
    assert parse_tag(tag, ["a-skill"]) == "a-skill"


@pytest.mark.parametrize(
    "tag", ["other/v1.2.3", "a-skill/v01.2.3", "a-skill/v1.2", "$(touch bad)", "--help"]
)
def test_release_tag_rejects_untrusted_input(tag):
    with pytest.raises(ValueError):
        parse_tag(tag, ["a-skill"])
