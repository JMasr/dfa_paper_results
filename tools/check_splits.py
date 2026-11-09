#!/usr/bin/env python3
"""Check the speaker columns of the article's partition table against the released protocol logs.

The partition table (paper/generated/tab_splits.tex, Supplementary Table S11) is a recorded output: its
recording and window columns come from the corpus metadata. Its three speaker columns, however, are the
partition as executed, and every log of both stages records it. This script reads them from
{screening,extension}_stage/protocol_logs.csv and stops if any row of the table disagrees.

    python3 tools/check_splits.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import repo_data  # noqa: E402

DISPLAY = {"adress_dementia": "ADReSS", "visia": "VISIA", "neurovoz_vowels": "NeuroVoz", "parcz_vowels": "PARCZ",
           "coperia_cough": "COPERIA cough", "coperia_a": "COPERIA /a/", "coswara": "Coswara"}


def main() -> int:
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument("--table",type=Path,default=repo_data.ROOT/"paper/generated/tab_splits.tex");args=parser.parse_args()
    executed: dict[str, set] = {}
    for r in repo_data.both_stages("protocol_logs.csv"):
        train, val = (int(x) for x in r["final_train_val_speakers"].split("|"))
        executed.setdefault(r["corpus"], set()).add((train, val, int(r["test_speakers"])))
    table = {}
    for line in args.table.read_text().splitlines():
        cells = [c.strip() for c in line.rstrip("\\ ").split("&")]
        if len(cells) == 7 and cells[1].isdigit():
            table[cells[0]] = tuple(int(c) for c in cells[1:4])
    failures = 0
    for corpus, disp in DISPLAY.items():
        ex = executed.get(corpus, set())
        if len(ex) != 1:
            print(f"FAIL {disp}: the logs do not hold one partition: {sorted(ex)}"); failures += 1; continue
        want = next(iter(ex)); got = table.get(disp)
        ok = got == want
        print(f"{'ok  ' if ok else 'FAIL'} {disp}: table {got}, logs {want} (train, validation, test speakers)")
        failures += not ok
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
