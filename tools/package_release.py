#!/usr/bin/env python3
"""Build and verify a deterministic local archive; never contact publication APIs."""
from __future__ import annotations
import hashlib
import json
import sys
import tomllib
import zipfile
from pathlib import Path
from reproduce import verify_inputs
from repo_data import sha256

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = ("tools", "tests", "docs", "metadata", "screening_stage", "extension_stage", "paper", ".github/workflows")
FILES = ("README.md", "CONTRIBUTING.md", "DATA_DICTIONARY.md", "LICENSE", "LICENSE-DATA", "CITATION.cff", ".zenodo.json", ".python-version", ".gitignore", "pyproject.toml", "uv.lock", "requirements.txt", "Makefile", "inputs.sha256.json")
ALLOWED_SUFFIXES = {".py", ".json", ".csv", ".md", ".tex", ".html", ".css", ".sh", ".pdf", ".yml", ".yaml"}
FORBIDDEN = {".git", ".venv", "__pycache__", ".pytest_cache", ".env", "gitlab.env"}


def selected_sources(root=ROOT) -> list[Path]:
    selected = [root / name for name in FILES]
    for folder in FOLDERS:
        directory = root / folder
        if not directory.is_dir():
            raise ValueError(f"Missing release directory: {folder}")
        candidates = [p for p in directory.rglob("*") if p.is_file() and not FORBIDDEN.intersection(p.relative_to(root).parts) and p.suffix != ".pyc"]
        for path in candidates:
            if path.suffix not in ALLOWED_SUFFIXES or path.name.startswith(".env"):
                raise ValueError(f"Unexpected release input: {path.relative_to(root)}")
        selected += candidates
    for path in selected:
        if not path.is_file() or path.is_symlink() or FORBIDDEN.intersection(path.relative_to(root).parts):
            raise ValueError(f"Unsafe/missing release member: {path}")
    return sorted(set(selected))


def validate_report(root=ROOT, profile="current") -> dict:
    report = json.loads((root / "outputs" / profile / "reproduction-report.json").read_text())
    if report.get("status") != "passed":
        raise ValueError("A passing full reconstruction is required before packaging")
    if report["input_sha256"] != verify_inputs():
        raise ValueError("Inputs differ from the successful reconstruction")
    current = {p.relative_to(root).as_posix(): sha256(p) for p in sorted((root / "tools").glob("*.py"))}
    if current != report["source_sha256"] or sha256(root / "uv.lock") != report["uv_lock_sha256"]:
        raise ValueError("Code/dependency lock changed after reconstruction; rerun reproduce.py")
    for name, digest in report["artifact_sha256"].items():
        if sha256(root / "outputs" / profile / name) != digest:
            raise ValueError(f"Output changed after reconstruction: {name}")
    return report


def write_archive(destination: Path, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)


def verify_archive(path: Path) -> int:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archive members")
        for name in names:
            if Path(name).is_absolute() or ".." in Path(name).parts or FORBIDDEN.intersection(Path(name).parts):
                raise ValueError(f"Unsafe archive path: {name}")
        manifest = json.loads(archive.read("RELEASE-MANIFEST.json"))
        if set(names) != set(manifest["sha256"]) | {"RELEASE-MANIFEST.json"}:
            raise ValueError("Archive inventory does not match its manifest")
        for name, digest in manifest["sha256"].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError(f"Corrupt archive member: {name}")
    return len(names)


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=["current", "historical"], default="current")
    parser.add_argument("--verify", type=Path, help="Verify an existing archive without rebuilding")
    args = parser.parse_args()
    if args.verify:
        print(f"PASS: {verify_archive(args.verify)} archive members verified")
        return 0
    report = validate_report(profile=args.profile)
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    files = {p.relative_to(ROOT).as_posix(): p.read_bytes() for p in selected_sources()}
    for name in report["artifact_sha256"]:
        files["outputs/" + args.profile + "/" + name] = (ROOT / "outputs" / args.profile / name).read_bytes()
    files["outputs/" + args.profile + "/reproduction-report.json"] = (ROOT / "outputs" / args.profile / "reproduction-report.json").read_bytes()
    inventory = {"version": version, "scope": report["scope"], "profile": args.profile, "sha256": {name: hashlib.sha256(content).hexdigest() for name, content in sorted(files.items())}}
    files["RELEASE-MANIFEST.json"] = (json.dumps(inventory, indent=2, ensure_ascii=False) + "\n").encode()
    directory = ROOT / "dist";directory.mkdir(exist_ok=True)
    destination = directory / f"dfa-paper-results-{version}-{args.profile}.zip"
    write_archive(destination, files)
    count = verify_archive(destination)
    (directory / f"RELEASE-MANIFEST-{args.profile}.json").write_bytes(files["RELEASE-MANIFEST.json"])
    (directory / (destination.name + ".sha256")).write_text(f"{sha256(destination)}  {destination.name}\n")
    print(f"PASS: {count} verified members; local archive {destination}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
