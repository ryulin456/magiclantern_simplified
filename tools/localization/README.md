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
(lowercase letters, digits, underscores, at most 8 characters, for portable
8.3 resource filenames). `name` is the
ASCII rescue label displayed before that language's font is available. `messages`
contains English `source` and UTF-8 `translation`. Empty translations use English.

`data/lang/INDEX.TXT` lists `id<TAB>display name<TAB>font id`, one language per line.
Leave the font id empty to use the camera's existing fonts. An optional BFNT goes
in `data/fonts/<font id>.bfn`; several languages may share a font. Copy language
files to `ML/LANG` and fonts to `ML/FONTS` when testing on a camera.
For example, German and Polish share `lat_ext.bfn` (font id `lat_ext`).
Avoid longer resource basenames such as `latin_ext`, even if a host filesystem
or newer camera happens to accept them.

On a failed switch the current language stays active. The Language item shows
an error code and the failing resource path: E2 stat/path, E3 size, E4 read or
allocation, E5 catalog validation, E7 font stat/size, E8 font read/allocation,
E9 font header, E10 glyph validation. E1 means the saved/requested id is absent
from the current index; E11 means the language semaphore could not be created.

The MLLG v2 format is little endian: `magic[4], version, count, pool_offset,
pool_size`, followed by `count` rows of `hash, source_offset, value_offset`, then
NUL-terminated UTF-8 strings. Hash is FNV-1a over the source UTF-8 bytes. Rows are
sorted by hash; full source comparison resolves hash collisions. All offsets are
relative to the string pool. Limits: 8192 entries, 1 MiB per catalog. The firmware
validates sizes, offsets, ordering, string termination, UTF-8 and source hashes.

Translated printf formats must preserve the exact directives and argument order.
The formatter falls back to the original format for unsupported directives or
mismatches. `%n`, positional arguments and dynamic width/precision are unsupported.

## Optional ARM execution tests

Install `unicorn==2.1.4` in a test environment, and use ARM none-eabi GCC 12.2.1:

```
python tools/localization/test_reader_arm.py /path/to/toolchain/bin
python tools/localization/test_startup_arm.py /path/to/toolchain/bin
```

These compile the actual C reader/startup/font code and execute ARM instructions.
The reader tests include guarded input buffers, truncated files, invalid UTF-8,
FNV collisions, changed printf directives, all catalog entries and mutations.
Startup tests mock the card I/O and menu registration, not the language reader
or BFNT validator. They cover English, immediate SET selection, 100 repeated
round trips without allocations, old-pointer lifetimes, serialized switches,
shared fonts, a second language without a font, allocation/read failures, and
corrupt/missing resources.
RBF UTF-8 iteration is tested with fixed glyph widths; this is not pixel or
real-camera validation. Temporary test builds are outside the source tree.

## Four-language 5D3 r4 follow-up

See `doc/LOCALIZATION-5D3-R4.md` for source inputs, build commands, camera-test
status and coverage boundaries. `test_four_languages_arm.py` tests all supplied
catalogs. `audit_runtime_ui.py` inventories the built 5D3 core and 19 modules,
including selected help lines and exact generated metadata.
`test_display_paths_arm.py` executes production menu-key recovery and module
prose helpers; it requires those built artifacts. These helpers are independent
of the historical workspace and create ARM test outputs in a temporary directory.

`format:false` marks literal percentage prose in a catalog. Its type must be
boolean. Formatting call sites still enforce printf compatibility at runtime;
this annotation does not disable the runtime guard.
