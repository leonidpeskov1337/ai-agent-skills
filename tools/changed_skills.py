"""Select skill tests from a git diff; unknown/shared paths conservatively select all."""

import argparse
import json
import subprocess
from pathlib import PurePosixPath

from tools.validate_repo import skills


def select(paths, names):
    selected = set()
    for path in paths:
        parts = PurePosixPath(path).parts
        if parts and parts[0] in names:
            selected.add(parts[0])
        elif path.endswith(".md") and (len(parts) == 1 or parts[0] == "docs"):
            continue
        else:
            return sorted(names)
    return sorted(selected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base")
    parser.add_argument("head")
    args = parser.parse_args()
    # NUL separators safely handle filenames with whitespace/newlines. Include both rename paths.
    result = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", "-z", args.base, args.head],
        check=True,
        capture_output=True,
    )
    paths = result.stdout.decode("utf-8").rstrip("\0").split("\0") if result.stdout else []
    print(json.dumps({"skill": select(paths, skills())}, separators=(",", ":")))


if __name__ == "__main__":
    main()
