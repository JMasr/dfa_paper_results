#!/usr/bin/env python3
"""Snapshot active literal LaTeX inputs, excluding comments; no manuscript is redistributed."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

INPUT = re.compile(r'\\(?:input|include)\s*\{([^{}]+)\}')
FIGURE = re.compile(r'\\includegraphics(?:\[[^\]]*\])?\s*\{([^{}]+)\}')


def strip_comments(source: str) -> str:
    result = []
    for line in source.splitlines():
        for position, char in enumerate(line):
            if char == '%':
                preceding = len(line[:position]) - len(line[:position].rstrip('\\'))
                if preceding % 2 == 0:
                    line = line[:position]
                    break
        result.append(line)
    return '\n'.join(result)


def inspect(root: Path) -> dict:
    root = root.resolve()
    documents, sources, commented = {}, {}, set()
    for wrapper in ['elsarticle_template/main_elsevier.tex', 'elsarticle_template/supplement.tex']:
        working = (root / wrapper).parent
        visited, artifacts, figures = set(), set(), set()

        def visit(path: Path):
            path = path.resolve()
            if not path.is_relative_to(root) or path.suffix != '.tex':
                raise ValueError(f'Unsupported source path: {path}')
            if path in visited: return
            visited.add(path)
            relative = path.relative_to(root).as_posix()
            if relative.startswith(('generated/', 'layout/')):
                artifacts.add(relative)
                return
            text = path.read_text(encoding='utf-8')
            sources[relative] = hashlib.sha256(text.encode()).hexdigest()
            active = strip_comments(text)
            for match in INPUT.finditer(text):
                if match.group(1) not in {m.group(1) for m in INPUT.finditer(active)}:
                    commented.add(match.group(1))
            for match in INPUT.finditer(active):
                name = match.group(1)
                if not Path(name).suffix: name += '.tex'
                candidates = [working / name, path.parent / name]
                resolved = next((candidate for candidate in candidates if candidate.is_file()), None)
                if resolved is None: raise ValueError(f'Unresolved literal input: {relative}: {name}')
                visit(resolved)
            for match in FIGURE.finditer(active):
                name = Path(match.group(1)).name
                if not (root / 'figs' / name).is_file(): raise ValueError(f'Missing figure: {name}')
                figures.add('figs/' + name)

        visit(root / wrapper)
        documents[wrapper] = {'artifacts': sorted(artifacts), 'figures': sorted(figures)}
    active_artifacts = set().union(*(set(document['artifacts']) for document in documents.values()))
    artifact_hashes = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sorted(active_artifacts)}
    return {'artifact_sha256': artifact_hashes, 'scope': 'Literal inputs of the two Elsevier wrappers, with TeX comments excluded; not a general TeX interpreter', 'documents': documents, 'source_sha256': sources, 'commented_inputs': sorted(commented)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manuscript-dir', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parents[1]/'paper/current_artifacts.json')
    args = parser.parse_args()
    result = inspect(args.manuscript_dir)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
    all_artifacts = set().union(*(set(value['artifacts']) for value in result['documents'].values()))
    print(f'{len(all_artifacts)} active TeX inputs; {len(result["source_sha256"])} manuscript source hashes; no manuscript prose exported.')
