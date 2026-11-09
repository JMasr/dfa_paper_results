#!/usr/bin/env python3
"""Audit text integrity and automatic attribution; never infer authorship or edit files."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import subprocess
import unicodedata

EXCLUDED = {'.git', '.venv', '__pycache__', '.pytest_cache', 'node_modules', '.cache'}
SUFFIXES = {'.tex', '.bib', '.py', '.md', '.txt', '.json', '.csv', '.tsv', '.html', '.svg',
            '.css', '.sh', '.toml', '.lock', '.yml', '.yaml', '.cff', '.sty', '.cls', '.bst'}
INVISIBLE = {0x00AD, 0x180E, 0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF}
BIDI = set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A)) | {0x200E, 0x200F, 0x061C}
TYPOGRAPHY = {0x00A0, 0x202F, 0x2009, 0x200A, 0x2018, 0x2019, 0x201C, 0x201D,
              0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015, 0x2212, 0xFB01, 0xFB02}
SIGNATURE = re.compile(
    r'(?im)^\s*(?:[%#>*]\s*)?(?:(?:co-authored-by|signed-off-by):\s*.*(?:codex|claude|chatgpt|copilot|openai|anthropic|\[bot\])'
    r'|(?:generated|written|authored|created)\s+(?:by|with)\s+(?:codex|claude|chatgpt|copilot|an?\s+ai\b)'
    r'|(?:generado|escrito|creado)\s+por\s+(?:codex|claude|chatgpt|copilot|(?:un\s+)?agente\b))')
MARKER = re.compile(r'<\/?(?:oai-mem-citation|citation_entries|rollout_ids)>|'
                    r':{1,2}codex-(?:file-citation|followup|code-comment)\{|'
                    r'\[?(?:turn\d+(?:search|view|fetch)\d+)\]?|'
                    r'<\|(?:im_start|im_end|assistant|system|user)\|>|'
                    r'\b(?:BEGIN|END)\s+(?:SYSTEM|ASSISTANT)\s+(?:PROMPT|MESSAGE)\b', re.I)
MOJIBAKE = re.compile(r'\u00c3[\u0080-\u00bf]|\u00e2\u20ac|\u00ef\u00bb\u00bf|\u00c2\u00a0')
DISCLOSURE = re.compile(r'(?i)(?:AI-assisted|generative AI|AI system is an author|'
                        r'Claude, Anthropic|Codex, OpenAI)')


def audit_string(text: str, location: str) -> list[dict]:
    findings = []
    for number, line in enumerate(text.split('\n'), 1):
        for rule, expression in [('automatic_attribution', SIGNATURE), ('tool_marker', MARKER),
                                 ('encoding_damage', MOJIBAKE)]:
            for match in expression.finditer(line):
                findings.append({'file': location, 'line': number, 'column': match.start()+1,
                                 'severity': 'error', 'rule': rule, 'match': match.group(0)})
        if DISCLOSURE.search(line):
            findings.append({'file': location, 'line': number, 'severity': 'info',
                             'rule': 'editorial_disclosure',
                             'note': 'Disclosure of tool use; not an authorship signature.'})
        for column, char in enumerate(line, 1):
            point = ord(char)
            category = unicodedata.category(char)
            if point in BIDI:
                severity, rule = 'error', 'bidirectional_control'
            elif point in INVISIBLE or point == 0xFFFD or (category == 'Cc' and char != '\t' and
                                                          not (char == '\r' and column == len(line))):
                severity, rule = 'error', 'invisible_or_invalid_character'
            elif category in {'Zl', 'Zp'}:
                severity, rule = 'warning', 'unicode_line_separator'
            elif category == 'Cf':
                severity, rule = 'warning', 'format_character'
            elif point in TYPOGRAPHY:
                severity, rule = 'info', 'typographic_character'
            else:
                continue
            findings.append({'file': location, 'line': number, 'column': column,
                             'severity': severity, 'rule': rule,
                             'codepoint': f'U+{point:04X}', 'name': unicodedata.name(char, 'UNNAMED')})
    if unicodedata.normalize('NFC', text) != text:
        findings.append({'file': location, 'severity': 'warning', 'rule': 'non_nfc_text',
                         'note': 'Canonically equivalent Unicode spellings differ; review before normalization.'})
    return findings


def is_excluded(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    return bool(EXCLUDED.intersection(relative.parts) or path.name.startswith('.env') or
                path.name == 'gitlab.env' or path.suffix.lower() in {'.key', '.pem', '.p12'})


def audit_paths(paths: list[Path], pdf: bool = False) -> tuple[list[dict], int]:
    findings, scanned, seen = [], 0, set()
    for root in paths:
        root = root.absolute()
        candidates = [root] if root.is_file() else root.rglob('*')
        for path in sorted(candidates):
            if path.is_symlink() or not path.is_file() or path in seen:
                continue
            if is_excluded(path, root.parent if root.is_file() else root):
                continue
            suffix = path.suffix.lower()
            if suffix not in SUFFIXES and not (pdf and suffix == '.pdf') and path.name not in {'LICENSE', 'LICENSE-DATA', 'Makefile'}:
                continue
            seen.add(path)
            scanned += 1
            if suffix == '.pdf':
                try:
                    from pypdf import PdfReader
                except ImportError as error:
                    raise RuntimeError('--pdf requires pypdf; run in the locked project environment') from error
                reader = PdfReader(path)
                findings += audit_string(json.dumps(dict(reader.metadata or {}), ensure_ascii=False), str(path)+':metadata')
                for page_number, page in enumerate(reader.pages, 1):
                    findings += audit_string(page.extract_text() or '', str(path)+f':page:{page_number}')
            else:
                try:
                    text = path.read_text(encoding='utf-8')
                except UnicodeDecodeError:
                    findings.append({'file': str(path), 'severity': 'error', 'rule': 'invalid_utf8'})
                    continue
                findings += audit_string(text, str(path))
    return findings, scanned


def audit_git(root: Path) -> list[dict]:
    process = subprocess.run(['git', 'log', '--all', '--format=%H%x00%an <%ae>%x00%B%x00'],
                             cwd=root, capture_output=True, text=True, check=True)
    tokens = process.stdout.split('\x00')
    findings = []
    for offset in range(0, len(tokens)-2, 3):
        revision, author, message = tokens[offset:offset+3]
        revision = revision.strip()
        findings += audit_string(message, f'git:{revision}')
        if re.search(r'(?i)\b(codex|claude|chatgpt|copilot)\b|\[bot\]', author):
            findings.append({'file': f'git:{revision}', 'severity': 'error', 'rule': 'automatic_commit_author'})
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', type=Path, nargs='+')
    parser.add_argument('--json', type=Path, dest='report')
    parser.add_argument('--pdf', action='store_true')
    parser.add_argument('--git', action='store_true')
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()
    for path in args.paths:
        if not path.exists():
            parser.error(f'Path does not exist: {path}')
    findings, scanned = audit_paths(args.paths, args.pdf)
    if args.git:
        findings += audit_git(args.paths[0])
    counts = {level: sum(item['severity'] == level for item in findings) for level in ['error', 'warning', 'info']}
    report = {'scope': 'Text integrity and attribution audit; not an AI authorship detector',
              'files_scanned': scanned, 'counts': counts, 'findings': findings}
    if args.report:
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps({'files_scanned': scanned, **counts}))
    if not args.report:
        for item in findings:
            if item['severity'] != 'info':
                print(json.dumps(item, ensure_ascii=False))
    return int(counts['error'] > 0 or (args.strict and counts['warning'] > 0))


if __name__ == '__main__':
    raise SystemExit(main())
