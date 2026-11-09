#!/usr/bin/env python3
"""Independently reconstruct historical engine effects; expose unresolved q provenance."""
from __future__ import annotations
import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy import stats
import repo_data
from build_paper_sota import bh


def engine_contrast(runs, candidate, rival, metric, stage):
    paired = defaultdict(dict)
    for row in runs:
        if row['adapter'] in {candidate, rival}:
            key = tuple(row[name] for name in ['bloque', 'dataset', 'seed', 'split_seed', 'rank'])
            if row['adapter'] in paired[key]:
                raise ValueError(f'Duplicate engine observation: {key}')
            paired[key][row['adapter']] = float(row[metric])
    blocks = defaultdict(list)
    for key, values in paired.items():
        if candidate in values and rival in values:
            # The archived engine groups the higher ranks into one extra band.
            block = key[0] + ('/low' if key[-1] == '8' else '/high') if stage == 2 else key[0]
            blocks[block].append(values[candidate] - values[rival])
    deltas = [statistics.mean(values) for block, values in sorted(blocks.items())]
    p = float(stats.wilcoxon(deltas, zero_method='wilcox', alternative='two-sided', method='auto').pvalue)
    return dict(delta=statistics.median(deltas), p=p, n_bloques=len(deltas), n_pares=sum(map(len, blocks.values())))



def audit_sensitivity():
    source = json.loads((repo_data.stage(2)/'sensitivity_readout.json').read_text())
    tests = []
    for analysis, endpoints in source['analyses'].items():
        for endpoint, values in endpoints.items():
            blocks = list(values['by_block'].values())
            reported = values['all']
            expected = dict(blocks=len(blocks), favourable=sum(value>0 for value in blocks), min=min(blocks), max=max(blocks), median=statistics.median(blocks))
            for field, value in expected.items():
                if not math.isclose(value, reported[field], abs_tol=.00500001, rel_tol=0):
                    raise ValueError(f'Sensitivity summary mismatch: {analysis}/{endpoint}/{field}')
            nonzero = sum(value != 0 for value in blocks)
            if nonzero < 6:
                if reported['p'] is not None: raise ValueError('Sensitivity reporting rule mismatch')
            else:
                p = float(stats.wilcoxon(blocks, zero_method='wilcox', method='auto').pvalue)
                if round(p,4) != reported['p']: raise ValueError(f'Sensitivity p mismatch: {analysis}/{endpoint}')
                tests.append((reported['p'],reported['q']))
    if len(tests) != source['family']['n_tests']: raise ValueError('Sensitivity family size mismatch')
    for (_, reported), value in zip(tests, bh([p for p,_ in tests])):
        if round(value,4) != reported: raise ValueError('Sensitivity q mismatch at published precision')
    return {'summaries':6, 'tests':len(tests), 'precision':'Rounded published by-block differences reproduce summaries and p; BH of published four-decimal p reproduces q. Does not rerun representation interventions.'}


def audit():
    report = {'scope':'Independent check of archived effects/p and pooled arm medians; q discrepancies are reported, not repaired', 'stages':[], 'unresolved_q':[], 'sensitivity':audit_sensitivity()}
    for stage in (1, 2):
        runs = repo_data.rows(stage, 'runs.csv')
        record = {'stage':stage, 'contrast_rows':0, 'confirmatory_policy_rows':0, 'arm_endpoint_medians':0}
        for filename, counter in [('contrasts.csv', 'contrast_rows'), ('analysis_policies.csv', 'confirmatory_policy_rows')]:
            rows = repo_data.rows(stage, filename)
            if filename == 'analysis_policies.csv': rows = [row for row in rows if row['estatus'] == 'CONFIRMATORIA']
            for row in rows:
                result = engine_contrast(runs, row['brazo'], row['rival'], row['metrica'], stage)
                for field in ['delta', 'p', 'n_bloques', 'n_pares']:
                    if not math.isclose(result[field], float(row[field]), abs_tol=1e-12, rel_tol=0):
                        raise ValueError(f'Archived {filename} mismatch: stage {stage}, {row["brazo"]}/{row["rival"]}/{row["metrica"]}, {field}')
                record[counter] += 1
            # Both a matching effect and p can coexist with a q provenance gap.
            groups = defaultdict(list)
            for row in rows:
                groups[row['metrica'] if filename == 'contrasts.csv' else 'all'].append(row)
            for family, members in groups.items():
                adjusted = bh([float(row['p']) for row in members])
                for row, value in zip(members, adjusted):
                    if not math.isclose(value, float(row['q']), abs_tol=1e-12, rel_tol=0):
                        report['unresolved_q'].append(dict(stage=stage, file=filename, family=family, candidate=row['brazo'], rival=row['rival'], endpoint=row['metrica'], p=float(row['p']), archived_q=float(row['q']), standard_bh_q=value, stated_family_m=int(row['familia_m'])))
        for row in repo_data.rows(stage, 'arm_summary.csv'):
            for metric in ['speaker_auroc', 'speaker_macro_f1']:
                groups = defaultdict(list)
                for run in runs:
                    if run['adapter'] == row['brazo']: groups[run['bloque']].append(float(run[metric]))
                median = statistics.median(statistics.mean(values) for values in groups.values())
                if f'{median:.6f}' != f'{float(row[metric+"__bloque_mediana"]):.6f}':
                    raise ValueError(f'Archived pooled median mismatch: stage {stage}, {row["brazo"]}, {metric}')
                record['arm_endpoint_medians'] += 1
        report['stages'].append(record)
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=repo_data.ROOT/'outputs/audit');args=parser.parse_args()
    result=audit();args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'engine-reconstruction.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'Archived effects/p and pooled medians verified; {len(result["unresolved_q"])} archived q values differ from standard BH; outside the current manuscript.')
