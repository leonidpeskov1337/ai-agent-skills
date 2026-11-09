"""Catalog discovery and safe, bounded updates of the root README."""

import pytest

from tools.update_catalog import END, START, catalog, updated_readme


def add_skill(root, name, description="Useful capability"):
    skill = root / name
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n", encoding="utf-8"
    )
    return skill


def test_new_skill_appears_without_registration(tmp_path):
    add_skill(tmp_path, "z-skill")
    add_skill(tmp_path, "a-skill")
    text = catalog(tmp_path)
    assert text.index("a-skill") < text.index("z-skill")
    assert "[a-skill](a-skill/SKILL.md)" in text
    assert "[Instructions](a-skill/SKILL.md)" in text
    assert text == catalog(tmp_path)


def test_display_metadata_and_optional_links(tmp_path):
    skill = add_skill(tmp_path, "example-skill")
    (skill / "agents").mkdir()
    (skill / "agents/openai.yaml").write_text(
        'interface:\n  display_name: "Friendly name"\n  short_description: "Brief purpose"\n'
    )
    (skill / "README.md").write_text("guide")
    (skill / "prompt.md").write_text("prompt")
    text = catalog(tmp_path)
    assert "[Friendly name](example-skill/README.md)" in text
    assert "Brief purpose" in text
    assert "[Prompt template](example-skill/prompt.md)" in text


def test_surrounding_content_is_preserved(tmp_path):
    add_skill(tmp_path, "example-skill")
    path = tmp_path / "README.md"
    path.write_text(f"Introduction\n{START}\nstale\n{END}\nManual guide\n")
    expected = updated_readme(tmp_path)
    assert expected.startswith("Introduction\n") and expected.endswith("\nManual guide\n")
    assert "stale" not in expected
    path.write_text(expected)
    assert updated_readme(tmp_path) == expected


def test_metadata_cannot_inject_table_rows_or_html(tmp_path):
    add_skill(tmp_path, "example-skill", "'one | two <script> [link](https://evil.invalid)' ")
    text = catalog(tmp_path)
    assert r"one \| two &lt;script&gt; \[link\]" in text
    assert "<script>" not in text


@pytest.mark.parametrize("text", ["no markers", f"{END}\n{START}", f"{START}{START}{END}"])
def test_ambiguous_markers_fail(tmp_path, text):
    (tmp_path / "README.md").write_text(text)
    with pytest.raises(ValueError, match="markers"):
        updated_readme(tmp_path)


def test_check_fails_on_stale_catalog_with_actionable_command(tmp_path, monkeypatch):
    import sys
    from tools import update_catalog

    add_skill(tmp_path, "new-skill")
    (tmp_path / "README.md").write_text(f"{START}\nstale\n{END}\n")
    monkeypatch.setattr(update_catalog, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["update_catalog", "--check"])
    with pytest.raises(SystemExit, match="python -m tools.update_catalog"):
        update_catalog.main()
