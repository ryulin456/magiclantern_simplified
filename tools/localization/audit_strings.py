#!/usr/bin/env python3
"""Report literal menu labels/help absent from a catalog, optionally filtering by a built binary.

This is a conservative source audit, not a complete C preprocessor: macros and
computed strings require review. A binary filter reduces camera-specific noise.
"""
import argparse
import ast
import json
import re
from pathlib import Path
from catalog import load_catalog

STRING = r'"(?:\\.|[^"\\])*"'
FIELD = re.compile(r'\.(?:name|help|help2)\s*=\s*((?:' + STRING + r'\s*)+)', re.S)


def find_messages(root):
    found = {}
    for path in sorted(Path(root).rglob('*.c')):
        text = path.read_text(encoding='utf-8', errors='replace')
        for match in FIELD.finditer(text):
            try:
                value = ''.join(ast.literal_eval(token) for token in re.findall(STRING, match.group(1)))
            except (SyntaxError, ValueError):
                continue
            if re.search('[A-Za-z]{2}', value):
                line = text.count('\n', 0, match.start()) + 1
                found.setdefault(value, []).append(f'{path}:{line}')
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_root', type=Path)
    parser.add_argument('catalog', type=Path)
    parser.add_argument('--binary', type=Path)
    args = parser.parse_args()
    catalog = load_catalog(args.catalog)
    translated = {row['source'] for row in catalog['messages'] if row['translation']}
    binary = args.binary.read_bytes() if args.binary else None
    candidates = find_messages(args.source_root)
    missing = {s: paths for s, paths in candidates.items()
               if s not in translated and (binary is None or s.encode('utf-8') + b'\0' in binary)}
    print(json.dumps({'candidate_count': len(candidates), 'missing': missing}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
