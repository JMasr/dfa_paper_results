"""Read immutable aggregate inputs after validating their complete stage manifest."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGES = {1: "screening_stage", 2: "extension_stage"}


def die(message: str):
    raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(directory: Path) -> dict:
    """Reject missing, altered, unlisted or unsafe scientific inputs; never cache."""
    manifest_path = directory / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("files")
    if not isinstance(entries, dict) or not entries:
        raise ValueError(f"{directory.name}: missing or empty files manifest")
    for name, metadata in entries.items():
        relative = Path(name)
        if relative.is_absolute() or len(relative.parts) != 1 or relative.name != name:
            raise ValueError(f"Unsafe manifest path: {name}")
        path = directory / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Missing file or symlink: {directory.name}/{name}")
        if sha256(path) != metadata.get("sha256"):
            raise ValueError(f"Hash mismatch: {directory.name}/{name}")
    scientific = {p.name for p in directory.iterdir() if p.suffix in {".csv", ".json"} and p.name != "MANIFEST.json"}
    if scientific != set(entries):
        raise ValueError(f"Unlisted scientific inputs: {sorted(scientific - set(entries))}")
    return manifest


def stage(n: int) -> Path:
    directory = ROOT / STAGES[n]
    verify_manifest(directory)
    return directory


def manifest(n: int) -> dict:
    return verify_manifest(ROOT / STAGES[n])


def rows(n: int, name: str) -> list[dict]:
    directory = stage(n)
    if name not in json.loads((directory / "MANIFEST.json").read_text())["files"]:
        raise ValueError(f"Unlisted requested input: {name}")
    with (directory / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def both_stages(name: str) -> list[dict]:
    return rows(1, name) + rows(2, name)
