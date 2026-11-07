"""Reject malformed/untrusted release tags before any publishing job is eligible."""

import os
import re
import subprocess

from tools.validate_repo import skills


def parse_tag(tag, names):
    match = re.fullmatch(r"([a-z0-9-]+)/v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", tag)
    if not match or match[1] not in names:
        raise ValueError(
            "Use an existing registered-skill/vMAJOR.MINOR.PATCH tag (no leading zeroes)"
        )
    return match[1]


def main():
    tag = os.environ["RELEASE_TAG"]
    skill = parse_tag(tag, skills())
    sha = subprocess.check_output(
        ["git", "rev-parse", f"refs/tags/{tag}^{{commit}}"], text=True
    ).strip()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if sha != head:
        raise SystemExit("Release tag must point at the selected default-branch workflow commit")
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"tag={tag}\nskill={skill}\nsha={sha}\n")


if __name__ == "__main__":
    main()
