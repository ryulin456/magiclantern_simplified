# Localization tools (review before the firmware integration)

Python 3, standard library only. No downloads, firmware extraction, release
packaging, AF experiments or historical workspace paths are needed.

* `python tools/localization/test_catalog.py` checks language-neutral compilation
  and rejection of duplicate keys and changed printf arguments.
* `python tools/localization/catalog.py data/localization/zh_cn.json --output data/lang/zh_cn.lng`
  validates and compiles the human-readable catalog deterministically.
* `python tools/localization/audit_strings.py src data/localization/zh_cn.json`
  reports untranslated literal `.name`, `.help` and `.help2` fields. Optional
  `--binary path/to/magiclantern.bin` limits this to strings in one camera build.
  Computed strings/macros are outside this conservative scanner's coverage.

Add another language with the same JSON schema; no new C translation function or
static word list is required. `language` and optional `font` are ASCII identifiers
(lowercase letters, digits, underscores, at most 15 characters). `name` is the
ASCII rescue label displayed before that language's font is available. `messages`
contains English `source` and UTF-8 `translation`. Empty translations use English.

`data/lang/INDEX.TXT` lists `id<TAB>display name<TAB>font id`, one language per line.
Leave the font id empty to use the camera's existing fonts. An optional BFNT goes
in `data/fonts/<font id>.bfn`; several languages may share a font. Copy language
files to `ML/LANG` and fonts to `ML/FONTS` when testing on a camera.

The MLLG v2 format is little endian: `magic[4], version, count, pool_offset,
pool_size`, followed by `count` rows of `hash, source_offset, value_offset`, then
NUL-terminated UTF-8 strings. Hash is FNV-1a over the source UTF-8 bytes. Rows are
sorted by hash; full source comparison resolves hash collisions. All offsets are
relative to the string pool. Limits: 8192 entries, 1 MiB per catalog. The firmware
validates sizes, offsets, ordering, string termination, UTF-8 and source hashes.

Translated printf formats must preserve the exact directives and argument order.
The formatter falls back to the original format for unsupported directives or
mismatches. `%n`, positional arguments and dynamic width/precision are unsupported.
