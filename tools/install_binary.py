"""Download a reviewed, SHA256-pinned linter binary; never execute downloaded scripts."""

import argparse
import hashlib
import io
from pathlib import Path
import platform
import tarfile
from urllib.request import urlopen
import zipfile

from tools.validate_repo import ROOT, load_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", choices=["actionlint", "gitleaks"])
    args = parser.parse_args()
    system = platform.system().lower()
    if platform.machine().lower() not in {"x86_64", "amd64"} or system not in {"linux", "windows"}:
        raise SystemExit(
            "Pinned binaries support x86-64 Linux/Windows; see upstream for other platforms"
        )
    entry = load_json(ROOT / "tools/binaries.json")[args.name][system]
    with urlopen(entry["url"], timeout=60) as response:
        data = response.read(64 * 1024 * 1024 + 1)
    if hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise SystemExit("Binary archive checksum mismatch")
    filename = args.name + (".exe" if system == "windows" else "")
    if system == "windows":
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            binary = archive.read(filename)
    else:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            binary = archive.extractfile(filename).read()
    target = ROOT / ".ci-bin" / args.name / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(binary)
    target.chmod(0o755)
    print(Path(target).relative_to(ROOT))


if __name__ == "__main__":
    main()
