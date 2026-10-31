"""Create a deterministic, credential-free skill ZIP from an explicit resource list."""
import hashlib
from pathlib import Path
import zipfile


def main():
    repo = Path(__file__).resolve().parents[1]
    skill = repo / "kubernetes-troubleshooter"
    output = repo / "dist" / "kubernetes-troubleshooter.skill"
    output.parent.mkdir(exist_ok=True)
    included = [skill / "SKILL.md", skill / "README.md", skill / "prompt.md"]
    for folder, suffix in (("agents", ".yaml"), ("scripts", ".py"),
                           ("references", ".md"), ("playbooks", ".md"), ("examples", ".md"),
                           ("evals", ".json"), ("evals", ".md"), ("tests", ".py"),
                           ("ArgoCD", ".md")):
        included.extend(sorted((skill / folder).glob("*" + suffix)))
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in included:
            if path.is_symlink() or not path.is_file():
                raise ValueError("invalid package input")
            info = zipfile.ZipInfo(path.relative_to(repo).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".skill.sha256").write_text(digest + "  " + output.name + "\n", encoding="ascii")
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
    print(f"{output}\nSHA256 {digest}\n{len(included)} files; ZIP integrity verified")


if __name__ == "__main__":
    main()
