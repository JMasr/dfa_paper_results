"""Prove the active analysis runs with no cached contrasts or arm summaries."""
import csv
import json
import shutil
import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.stats import false_discovery_control
import repo_data
from build_paper_sota import main as generate
from inspect_manuscript import strip_comments

ROOT = Path(__file__).resolve().parents[1]


def test_comments_do_not_activate_archived_tables():
    source = r'''% \input{historical.tex}
Text at 10\%. % \input{also_historical.tex}
\input{current.tex}
'''
    active = strip_comments(source)
    assert 'historical.tex' not in active
    assert r'10\%' in active
    assert r'\input{current.tex}' in active
    assert strip_comments('row \\\\% comment') == 'row \\\\'


def test_current_snapshot_excludes_historical_inference():
    snapshot = json.loads((ROOT/'paper/current_artifacts.json').read_text())
    active = set().union(*(set(document['artifacts']) for document in snapshot['documents'].values()))
    assert len(active) == 19
    assert not any('supps_tab_all_' in path for path in active)


def test_all_current_performance_outputs_from_raw_exports_only(tmp_path, monkeypatch):
    # The two manifests in this fixture list only original run-level CSVs.
    # Every historical contrast, policy and arm-summary file is physically absent.
    for stage in ('screening_stage','extension_stage'):
        folder = tmp_path/stage;folder.mkdir()
        manifest = json.loads((ROOT/stage/'MANIFEST.json').read_text())
        wanted = ['runs.csv'] + (['bundle_runs.csv'] if stage == 'extension_stage' else [])
        for name in wanted:shutil.copyfile(ROOT/stage/name, folder/name)
        manifest['files'] = {name:manifest['files'][name] for name in wanted}
        (folder/'MANIFEST.json').write_text(json.dumps(manifest))
    monkeypatch.setattr(repo_data,'ROOT',tmp_path)
    out, figures, data = tmp_path/'generated',tmp_path/'figs',tmp_path/'data'
    monkeypatch.setattr(sys,'argv',['build_paper_sota.py','--from-runs','--out',str(out),'--figs',str(figures),'--data',str(data)])
    generate()
    assert not (out/'supps_tab_all_one.tex').exists()
    assert not (out/'supps_tab_all_two.tex').exists()
    assert (out/'sota_tab_perarm.tex').is_file()
    assert (out/'supps_tab_stats.tex').is_file()
    with (data/'paired_contrasts.csv').open() as stream:contrasts=list(csv.DictReader(stream))
    assert len(contrasts)==58
    # Check all family corrections independently with SciPy rather than the generator's BH.
    for family in {row['family'] for row in contrasts}:
        selected=[row for row in contrasts if row['family']==family]
        expected=false_discovery_control([float(row['p']) for row in selected])
        assert [float(row['q']) for row in selected] == pytest.approx(expected,abs=1e-14)
    with (data/'all_arms_by_rank.csv').open() as stream:inventory=list(csv.DictReader(stream))
    assert sum(int(row['runs']) for row in inventory)==2025
    assert len(inventory)==42
    for name in ('fig_blocks_data.csv','fig_rank_curve_data.csv'):
        assert (figures/name).read_bytes()==(ROOT/'paper/figs'/name).read_bytes()
