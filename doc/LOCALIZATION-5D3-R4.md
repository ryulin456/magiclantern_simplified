# File-backed language switching: 5D3 r4

This extends `review/localization-v2` while retaining the original upstream
history. English remains the default. Press SET on `Prefs -> Language` to
cycle immediately through English, Simplified Chinese, German and Polish.
Catalogs and optional fonts are loaded from the card through the same API.

## Camera and review scope

The maintainer reports successful testing of the r4 package on a Canon EOS
5D Mark III with Canon firmware **1.2.3**. Other models have not been validated
with this revision. No claim is made that every recording/module combination
has been exercised. Translation wording still needs native-language review.

This is a localization proposal. It does not add the separate r21 AF module
or recover the missing historical r9 core sources. Per-camera Makefiles and
module selection lists remain identical to the upstream review base
`ed3e7c0dfacfdeaf3349dee73edf9e3621217462`.

Follow-up changes are split into module-build portability, standalone tools,
immediate language switching/font snapshots, display-path fixes, resources,
and tests/documentation. This is a logical review series from preserved source,
not a reconstruction of the original development chronology.

## What r4 fixes

* Immutable per-boot catalog/font caches preserve returned pointer lifetimes.
  Switching is serialized; failed loads preserve the active resources.
* Resource IDs fit portable 8.3 filenames; German and Polish share `lat_ext.bfn`.
  A failed load exposes an error number and resource path in the Language item.
* Menu labels/choices can recover the original static key when a display
  buffer truncated it before lookup. Grid labels retain complete UTF-8 glyphs.
* Choice-specific help needs individual line keys, not just the whole block.
* Module information values now translate Name, Summary, Description and help
  pages. Credits, versions, license identifiers and URLs retain their values.
* Exact generated module text, including blank lines, is supplied in catalogs.

Chinese has 2264 messages; German and Polish each have 2297. A binary-backed
inventory of this 5D3 core and the 19 packaged modules covers 1733 static UI
keys, all present in the three catalogs. This excludes computed messages and
raster documentation; matching the inventory is not proof of full coverage.
Existing draft translations also received an English-residue/terminology pass.
Translation provenance and remaining proofreading needs are in
`data/localization/TRANSLATION-STATUS.md`.

## Build and resource inputs

Use the upstream build prerequisites, GNU make, ARM none-eabi GCC 12.2.1,
Python 3 and docutils. Pillow is needed only when regenerating fonts. From the
repository root, compile catalogs deterministically:

```sh
python tools/localization/catalog.py data/localization/zh_cn.json --output data/lang/zh_cn.lng
python tools/localization/catalog.py data/localization/de.json --output data/lang/de.lng
python tools/localization/catalog.py data/localization/pl.json --output data/lang/pl.lng
python tools/localization/generate_latin_font.py data/fonts/source/NotoSans-Regular.ttf data/fonts/lat_ext.bfn data/localization/de.json data/localization/pl.json
python tools/localization/extend_chinese_font.py
```

Exact licensed font inputs for the new glyphs are in `data/fonts/source/`.
The Chinese extension script retains existing BFNT records and adds missing
glyphs; it does not regenerate the preserved historical base font from scratch.
SIL OFL texts are in `doc/OFL-NotoSans*.txt`.

Build the core in a POSIX shell, setting ARM_BINPATH to your toolchain bin:

```sh
cd platform/5D3.123
make -j4 build-lang4-r4/autoexec.bin build-lang4-r4/5D3_123.sym \
  BUILD_DIR=build-lang4-r4 ZIP_DIR=build-lang4-r4/zip \
  VERSION=2026-10-27.5D3.123.LANG4-LIVE-r4-TEST-ONLY \
  ARM_BINPATH="$ARM_BINPATH" \
  INCLUDE_ARGS='-I. -Iinclude -Ibuild-lang4-r4 -I../../src -Wa,-Ibuild-lang4-r4'
```

The assembler include path must use the selected build directory so the boot
image embeds that core. Build matching modules from this source using the
upstream module targets. The distributed card package contains 19 modules and
its matching `5D3_123.sym`; modules initially have autoload disabled. It contains
no installer and is intended for an existing bootable ML test card. The package
version contains a fixed label, but normal build date/user/git metadata can
differ; a fresh build is not promised to be byte-identical to the ZIP.

## Automated validation

With Unicorn 2.1.4 available in Python and ARM_BINPATH set:

```sh
python tools/localization/test_catalog.py
python tools/localization/test_reader_arm.py "$ARM_BINPATH"
python tools/localization/test_four_languages_arm.py "$ARM_BINPATH"
# After building the 5D3 core and the 19 selected modules:
python tools/localization/audit_runtime_ui.py build-lang4-r4
python tools/localization/test_display_paths_arm.py "$ARM_BINPATH" build-lang4-r4
```

The r4 automated run passed 6858 actual catalog lookups, 100 SET selections,
saved-language restoration and resource-failure rollback. Production display
helpers passed 750 truncated-key cases, 231 selected help-line cases and 195
module-prose cases across the three languages. These execute real ARM C code
with mocked card I/O; they do not emulate camera drawing. All 19 packaged
modules passed undefined-symbol checks against the matching core symbol file.

The test package is published separately in `ryulin456/magiclantern-zh`.
Use its recorded SHA256 to identify the exact camera-tested artifact. The
automated reports intentionally record hardware_test:false; the maintainer's
separate real-camera report is documented above.
