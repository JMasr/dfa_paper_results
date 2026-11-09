#!/usr/bin/env python3
"""Render public aggregate descriptors from CSV; never infer private participant records."""
import csv,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

def generate(out=None):
    target=Path(out or ROOT/'outputs/generated');target.mkdir(parents=True,exist_ok=True)
    records=[]
    for src in sorted((ROOT/'metadata').glob('*.csv')):
        with src.open(newline='',encoding='utf-8') as f:
            reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
        name=src.stem+'.tex'
        if src.stem.endswith('_macros'):
            names=[r['macro'] for r in rows]
            if len(names)!=len(set(names)):raise ValueError(f'Duplicate metadata macro in {src.name}')
            content='%% GENERATED from released aggregate metadata CSV; not individual-level reanalysis.\n'
            content+=''.join('\\newcommand{\\'+r['macro']+'}{'+r['value']+'}\n' for r in rows)
        else:
            template=(ROOT/'metadata/templates'/name).read_text()
            body='\n'.join(' & '.join(r[k] for k in fields)+r' \\' for r in rows)
            content=template.replace('@@ROWS@@',body)
        (target/name).write_text(content,encoding='utf-8')
        records.append({'artifact':name,'input':src.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'provenance':'released aggregate descriptors; original measurement is not rerun'})
    return records

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--out');args=parser.parse_args()
    print(json.dumps(generate(args.out),indent=2))
