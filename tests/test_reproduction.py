"""Scientific regression tests and corruption tests independent of reference copying."""
import csv
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import repo_data
from build_paper_sota import bh, boot_ci, contrast, Z
from reproduce import compare_tex, macro_definitions, verify_inputs


def test_original_bootstrap_draws_and_percentiles_are_preserved():
    for values in ([.1, .1, .3, .4], np.linspace(-.7, .8, 18)):
        rng = np.random.default_rng(0)
        original = [np.median(rng.choice(values, size=len(values), replace=True)) for _ in range(5000)]
        assert boot_ci(values) == tuple(np.percentile(original, [2.5, 97.5]))


def observations():
    result = []
    # Two tasks share each corpus/backbone block; they must not double the test n.
    for block in range(6):
        for task in ("a", "cough"):
            for partition in (7, 8, 9):
                for method, value in [("dfa", .5 + block * .01), ("lora", .5)]:
                    result.append(dict(bloque=f"corpus{block}/encoder", dataset=task, split_seed=str(partition), adapter=method, rank="8", speaker_auroc=str(value)))
    return result


def evaluate(rows):
    return contrast(rows, "dfa", "8", "lora", "8", "speaker_auroc")


def test_pairing_blocks_zero_differences_and_mde():
    result = evaluate(observations())
    assert result["n"] == 6
    assert all(len(values) == 6 for values in result["cells"].values())
    assert result["p"] == .0625  # Five nonzero blocks; exact two-sided test.
    assert math.isinf(result["mde"])  # Six-nonzero reporting threshold is not met.
    rows = observations()
    for row in rows:
        if row["adapter"] == "dfa":
            row["speaker_auroc"] = str(float(row["speaker_auroc"]) + .01)
    result = evaluate(rows)
    assert result["mde"] == pytest.approx(Z * statistics.stdev(result["deltas"]) / math.sqrt(6))


@pytest.mark.parametrize("damage", ["duplicate", "missing", "nan"])
def test_invalid_pairing_fails_closed(damage):
    rows = observations()
    if damage == "duplicate": rows.append(rows[0].copy())
    elif damage == "missing": rows.pop(0)
    else: rows[0]["speaker_auroc"] = "nan"
    with pytest.raises(ValueError): evaluate(rows)


def test_bh_adjustment():
    assert bh([.04, .001, .03, .5]) == pytest.approx([.0533333333333, .004, .0533333333333, .5])


def test_duplicate_macros_cannot_hide_a_wrong_value(tmp_path):
    reference = tmp_path / "reference.tex"; output = tmp_path / "new.tex"
    reference.write_text('\\newcommand{\\Result}{0.5}\n')
    output.write_text('\\newcommand{\\Result}{0.5}\n\\newcommand{\\Result}{0.9}\n')
    with pytest.raises(ValueError, match="Duplicate macro"): compare_tex(output, reference)
    output.write_text('\\newcommand{\\Result}{0.6}\n')
    assert compare_tex(output, reference) is not None


def test_integrity_cannot_be_bypassed_by_a_previous_check(tmp_path):
    data = tmp_path / "runs.csv";data.write_text("metric\n0.5\n")
    manifest = tmp_path / "MANIFEST.json"
    manifest.write_text(json.dumps({"files": {"runs.csv": {"sha256": hashlib.sha256(data.read_bytes()).hexdigest()}}}))
    repo_data.verify_manifest(tmp_path)
    data.write_text("metric\n0.9\n")
    with pytest.raises(ValueError, match="Hash mismatch"): repo_data.verify_manifest(tmp_path)


@pytest.mark.parametrize("name", ["../outside.csv", "/outside.csv", "sub/file.csv"])
def test_unsafe_manifest_paths_are_rejected(tmp_path, name):
    (tmp_path / "MANIFEST.json").write_text(json.dumps({"files": {name: {"sha256": "0" * 64}}}))
    with pytest.raises(ValueError, match="Unsafe"): repo_data.verify_manifest(tmp_path)


def test_empty_or_unlisted_inputs_are_rejected(tmp_path):
    manifest = tmp_path / "MANIFEST.json";manifest.write_text('{"files": {}}')
    with pytest.raises(ValueError): repo_data.verify_manifest(tmp_path)
    data=tmp_path/'runs.csv';data.write_text('x\n1\n')
    manifest.write_text(json.dumps({'files':{'runs.csv':{'sha256':repo_data.sha256(data)}}}))
    (tmp_path/'extra.csv').write_text('x\n2\n')
    with pytest.raises(ValueError,match='Unlisted'):repo_data.verify_manifest(tmp_path)


def test_released_policy_keeps_all_runs_and_matches_engine_anchor():
    verify_inputs()
    for stage, count in [(1, 828), (2, 1197)]:
        runs = repo_data.rows(stage, "runs.csv")
        assert len(runs) == count
        assert any(row["speaker_above_floor"] == "0" for row in runs)
        tested = 0
        for reference in repo_data.rows(stage, "contrasts.csv"):
            # The common DFA/LoRA anchor is the declared generator cross-check.
            # Other cached exploratory engine rows can pool ranks or use a different test convention.
            if (reference["brazo"], reference["rival"]) != ("dfa", "lora"): continue
            result = contrast(runs, reference["brazo"], "8", reference["rival"], "8", reference["metrica"])
            assert result["delta"] == pytest.approx(float(reference["delta"]), abs=1e-12)
            if math.isfinite(result["p"]): assert result["p"] == pytest.approx(float(reference["p"]), abs=1e-12)
            assert result["fav"] == int(reference["bloques_a_favor"])
            assert result["n"] == int(reference["n_bloques"])
            tested += 1
        assert tested > 0


def test_historical_rank_bands_and_test_convention():
    from audit_engine import engine_contrast
    rows=observations()
    # Each higher rank is paired only with its matching rank; high ranks share a band.
    for row in list(rows):
        for rank in ('256','512'):
            copy=row.copy();copy['rank']=rank;rows.append(copy)
    for row in rows:row['seed']='54'
    result=engine_contrast(rows,'dfa','lora','speaker_auroc',2)
    assert result['n_bloques']==12
    assert result['n_pares']==108


def test_sensitivity_statistics_from_released_block_differences():
    from audit_engine import audit_sensitivity
    result=audit_sensitivity()
    assert result['summaries']==6
    assert result['tests']==4
