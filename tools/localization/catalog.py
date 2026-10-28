#!/usr/bin/env python3
"""Compile a UTF-8 JSON translation catalog; no binary extraction or downloads."""
import argparse
import json
import re
import struct
from pathlib import Path

MAGIC = b'MLLG'
VERSION = 2
MAX_ENTRIES = 8192
MAX_SIZE = 1024 * 1024
ID_RE = re.compile(r'[a-z][a-z0-9_]{0,7}\Z')  # portable 8.3 resource filenames
DIRECTIVE = re.compile(r'%[-+ #0]*[0-9]*(?:\.[0-9]*)?(?:hh|ll|[hljztL])?[diouxXfFeEgGaAcsp%]')


def fnv1a(text):
    value = 0x811c9dc5
    for byte in text.encode('utf-8'):
        value = ((value ^ byte) * 0x01000193) & 0xffffffff
    return value


def format_tokens(text):
    """Preserve printf directives exactly, including width and precision.

    Positional arguments, dynamic width/precision and %n are intentionally not
    supported by the translation formatter. Ordinary labels need not be formats.
    """
    tokens = []
    index = 0
    while index < len(text):
        if text[index] != '%':
            index += 1
            continue
        match = DIRECTIVE.match(text, index)
        if not match:
            raise ValueError('unsupported printf directive')
        tokens.append(match.group())
        index = match.end()
    return tokens


def load_catalog(path):
    catalog = json.loads(Path(path).read_text(encoding='utf-8'))
    for key in ('language', 'font'):
        value = catalog.get(key, '')
        if (key == 'language' or value) and not ID_RE.fullmatch(value):
            raise ValueError('invalid ' + key)
    name = catalog['name']
    if not name or len(name) > 47 or any(ord(c) < 32 or ord(c) > 126 for c in name):
        raise ValueError('language display name must be 1..47 printable ASCII characters')
    seen = set()
    for row in catalog['messages']:
        source, value = row['source'], row['translation']
        for text in (source, value):
            if not isinstance(text, str) or '\0' in text or len(text.encode('utf-8')) > 8191:
                raise ValueError('invalid message string')
        if not source or source in seen:
            raise ValueError('empty or duplicate source message: ' + repr(source))
        seen.add(source)
        if 'format' in row and not isinstance(row['format'], bool):
            raise ValueError('format must be a boolean')
        # Plain help text may contain e.g. "2% discharge", which resembles
        # a printf %d with a space flag. The runtime formatter still verifies
        # argument compatibility independently before calling vsnprintf.
        if '%' in source and row.get('format', True):
            try:
                original = format_tokens(source)
            except ValueError:
                continue  # a label may contain an ordinary percentage sign
            if value and original != format_tokens(value):
                raise ValueError('printf mismatch: ' + repr(source))
    return catalog


def compile_catalog(catalog):
    pool = bytearray()
    offsets = {}
    def intern(text):
        if text not in offsets:
            offsets[text] = len(pool)
            pool.extend(text.encode('utf-8') + b'\0')
        return offsets[text]
    entries = []
    for row in sorted(catalog['messages'], key=lambda r: (fnv1a(r['source']), r['source'])):
        if row['translation']:
            entries.append((fnv1a(row['source']), intern(row['source']), intern(row['translation'])))
    if len(entries) > MAX_ENTRIES:
        raise ValueError('too many translations')
    result = struct.pack('<4s4I', MAGIC, VERSION, len(entries), 20 + len(entries) * 12, len(pool))
    result += b''.join(struct.pack('<3I', *entry) for entry in entries) + pool
    if len(result) > MAX_SIZE:
        raise ValueError('catalog exceeds 1 MiB')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('catalog', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    catalog = load_catalog(args.catalog)
    data = compile_catalog(catalog)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(data)
    print(f"{catalog['language']}: {len(catalog['messages'])} messages, {len(data)} bytes")


if __name__ == '__main__':
    main()
