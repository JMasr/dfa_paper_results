#!/usr/bin/env python3
"""Fresh reconstruction, strict reference comparison and machine-readable evidence."""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from pypdf import PdfReader
import repo_data

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"
PAPER = ROOT / "paper"
GENERATORS = ["build_paper_sota.py", "build_cost_macros.py", "build_protocol_macros.py", "build_sensitivity_macros.py"]
MACRO = re.compile(r"^\\newcommand\{\\([A-Za-z]+)\}\{(.*)\}$")


def body(path: Path) -> list[str]:
    # One purely typographic equivalent occurs in the editorial manuscript.
    return [line.replace("×", r"$\times$") for line in path.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("%")]


def macro_definitions(path: Path) -> dict[str, str]:
    definitions = {}
    for line in body(path):
        if not line.startswith(r"\newcommand"):
            continue
        match = MACRO.fullmatch(line)
        if not match:
            raise ValueError(f"Unsupported macro syntax: {path.name}: {line}")
        name, value = match.groups()
        if name in definitions:
            raise ValueError(f"Duplicate macro: {path.name}: {name}")
        definitions[name] = value
    return definitions


def compare_tex(new: Path, reference: Path) -> str | None:
    if not new.is_file():
        return "missing output"
    expected, actual = macro_definitions(reference), macro_definitions(new)
    if expected:
        differences = [name for name, value in expected.items() if actual.get(name) != value]
        return f"macro values differ: {differences[:5]}" if differences else None
    return None if body(new) == body(reference) else "non-comment content differs"


def run(script: str, *arguments: str) -> None:
    process = subprocess.run([sys.executable, str(ROOT / "tools" / script), *map(str, arguments)], cwd=ROOT, capture_output=True, text=True, errors="replace")
    if process.returncode:
        raise RuntimeError(f"{script} failed:\n{process.stdout}\n{process.stderr}")
    print(f"ok generator {script}", flush=True)


def verify_inputs() -> dict[str, str]:
    recorded = json.loads((ROOT / "inputs.sha256.json").read_text())
    if not recorded:
        raise ValueError("Empty input manifest")
    for name, digest in recorded.items():
        path = ROOT / name
        if Path(name).is_absolute() or ".." in Path(name).parts or path.is_symlink():
            raise ValueError(f"Unsafe input: {name}")
        if repo_data.sha256(path) != digest:
            raise ValueError(f"Input hash mismatch: {name}")
    for number in (1, 2):
        repo_data.stage(number)
    return recorded


def reconstruct(target: Path, profile: str = "current") -> dict:
    inputs = verify_inputs()
    if profile == "historical":
        run("audit_engine.py", "--out", target / "audit")
        engine_audit = json.loads((target / "audit/engine-reconstruction.json").read_text())
    else:
        from audit_engine import audit_sensitivity
        audit_sensitivity()
        engine_audit = None
    for script in GENERATORS:
        arguments = ["--out", target / "generated"]
        if script == GENERATORS[0]:
            arguments += ["--figs", target / "figs", "--data", target / "data"]
            if profile == "current": arguments += ["--from-runs"]
        run(script, *arguments)
    run("build_metadata.py", "--out", target / "generated")
    run("build_editorial_views.py", "--root", target)
    run("build_readable_figures.py", "--root", target)
    run("check_splits.py", "--table", target / "generated/tab_splits.tex")
    checks = []
    for folder in ("generated", "layout"):
        references = sorted((PAPER / folder).glob("*.tex"))
        if profile == "current": references = [path for path in references if path.name not in {"supps_tab_all_one.tex", "supps_tab_all_two.tex"}]
        if {p.name for p in references} != {p.name for p in (target / folder).glob("*.tex")}:
            raise ValueError(f"Unexpected or missing {folder} outputs")
        for reference in references:
            error = compare_tex(target / folder / reference.name, reference)
            if error:
                raise ValueError(f"{folder}/{reference.name}: {error}")
            checks.append({"artifact": f"{folder}/{reference.name}", "comparison": "macro values" if macro_definitions(reference) else "non-comment TeX", "provenance": "released aggregate metadata" if reference.stem in {p.stem for p in (ROOT / 'metadata').glob('*.csv')} else ("rendered published sensitivity aggregates" if reference.name == "sensitivity_macros.tex" else ("mixed: independently verified effects and medians; archived q displayed" if reference.name in {"supps_tab_all_one.tex", "supps_tab_all_two.tex"} else "computed from run aggregates/configuration"))})
    for name in ("fig_blocks_data.csv", "fig_rank_curve_data.csv"):
        if (target / "figs" / name).read_bytes() != (PAPER / "figs" / name).read_bytes():
            raise ValueError(f"Plotted values differ: {name}")
        checks.append({"artifact": f"figs/{name}", "comparison": "exact CSV bytes", "provenance": "computed from run aggregates"})
    expected = set(json.loads((PAPER / "used_macros.json").read_text()))
    definitions = {}
    for path in (target / "generated").glob("*.tex"):
        for name, value in macro_definitions(path).items():
            if name in definitions:
                raise ValueError(f"Macro defined in multiple files: {name}")
            definitions[name] = value
    missing = sorted(expected - definitions.keys())
    if missing:
        raise ValueError(f"Missing manuscript scientific macros: {missing}")
    snapshot = json.loads((PAPER / "current_artifacts.json").read_text())
    active = sorted(set().union(*(set(value["artifacts"]) for value in snapshot["documents"].values())))
    active_figures = sorted(set().union(*(set(value["figures"]) for value in snapshot["documents"].values())))
    for name in active + active_figures:
        if not (target / name).is_file(): raise ValueError(f"Missing active manuscript artifact: {name}")
    historical_tables = {"generated/supps_tab_all_one.tex", "generated/supps_tab_all_two.tex"}
    if historical_tables.intersection(active): raise ValueError("Historical q tables became active; reassess the release scope")
    with (target/"data/paired_contrasts.csv").open(newline="") as stream:
        import csv
        numeric_contrasts = list(csv.DictReader(stream))
    coverage = {"active_tex_inputs": active, "active_figures": active_figures, "historical_q_values_used": 0, "unrounded_paired_contrasts": len(numeric_contrasts), "scope": "Performance/statistics from per-run exports; sensitivity from block differences; five descriptor files from declared aggregate metadata CSV", "source_snapshot_sha256": repo_data.sha256(PAPER/"current_artifacts.json")}
    (target/"coverage.json").write_text(json.dumps(coverage,indent=2)+"\n")
    figure_pages = {}
    for path in sorted((target / "figs").glob("*.pdf")):
        count = len(PdfReader(path).pages)
        if count != 1:
            raise ValueError(f"Expected one figure page: {path.name}: {count}")
        figure_pages[path.name] = count
    if inputs != verify_inputs():
        raise ValueError("Inputs changed during reconstruction")
    hashes = {p.relative_to(target).as_posix(): repo_data.sha256(p) for p in sorted(target.rglob("*")) if p.is_file()}
    sources = {p.relative_to(ROOT).as_posix(): repo_data.sha256(p) for p in sorted((ROOT / "tools").glob("*.py"))}
    return {"status": "passed", "scope": "Post-training analysis from released run-level aggregates; not retraining or independent demographic remeasurement", "profile": profile, "current_manuscript": coverage, "checks": checks, "historical_engine_audit": ({"stages": engine_audit["stages"], "unresolved_q_count": len(engine_audit["unresolved_q"]), "status": "outside the active manuscript"} if engine_audit else {"status": "not required for current manuscript; archived q not consumed"}), "scientific_macros_used": len(expected), "generated_macro_definitions": len(definitions), "figure_pages": figure_pages, "input_sha256": inputs, "source_sha256": sources, "uv_lock_sha256": repo_data.sha256(ROOT / "uv.lock"), "python": platform.python_version(), "uv": subprocess.check_output(["uv", "--version"],text=True).strip(), "bootstrap": {"resamples": 5000, "seed": 0, "rng": "numpy.random.default_rng", "percentiles": [2.5, 97.5]}, "packages": {name: importlib.metadata.version(name) for name in ["numpy", "scipy", "matplotlib", "pillow", "playwright", "pypdf"]}, "artifact_sha256": hashes, "rendering_contract": "Exact scientific values; current HTML vector PDFs validated as single pages. Pixel identity across Chromium/font versions is not asserted."}


def main() -> int:
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=["current", "historical"], default="current")
    parser.add_argument("--manuscript-dir", type=Path, help="Optionally verify that the manuscript snapshot is current")
    args = parser.parse_args()
    OUT = ROOT / "outputs" / args.profile
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        # A fresh staging directory prevents stale output from satisfying any check.
        with tempfile.TemporaryDirectory(prefix=".reconstruction-", dir=ROOT) as directory:
            target = Path(directory)
            if args.manuscript_dir:
                from inspect_manuscript import inspect
                if inspect(args.manuscript_dir) != json.loads((PAPER/"current_artifacts.json").read_text()):
                    raise ValueError("Manuscript changed after dependency snapshot; run inspect_manuscript.py")
            report = reconstruct(target, args.profile)
            for path in sorted(target.rglob("*")):
                if path.is_file():
                    destination = OUT / path.relative_to(target)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, destination)
        (OUT / "reproduction-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        print(f"PASS: {len(report['checks'])} reference comparisons; {report['scientific_macros_used']} manuscript macros; {len(report['figure_pages'])} single-page PDFs.")
        print("CURRENT MANUSCRIPT: 19 TeX inputs, four figures; no archived q values consumed." if args.profile == "current" else "HISTORICAL PROFILE: archived q are rendered for forensic comparison only.")
        return 0
    except Exception as error:
        (OUT / "reproduction-report.json").write_text(json.dumps({"status": "failed", "error": str(error)}, indent=2) + "\n")
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
