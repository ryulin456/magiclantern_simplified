# File-backed localization review, revision 2

Base: `reticulatedpines/magiclantern_simplified`
`ed3e7c0dfacfdeaf3349dee73edf9e3621217462`.

This is a localization-only proposal revised on 2026-10-20. It combines the
preserved UTF-8 rendering/persistent I/O work with a new language-neutral loader.
It does not represent the original historical development commits or reproduce
the previously published firmware packages. The missing historical 5D3 r9 core
source remains missing.

## Scope and commit order

1. Standalone catalog compiler and conservative menu-string audit, with tests.
2. External Chinese catalog, optional font and font license.
3. A language-neutral validated catalog reader.
4. Persistent resource I/O without retaining temporary DMA/shoot buffers.
5. UTF-8 rendering and optional BFNT validation.
6. Language selection, display-time translation and resource packaging.
7. ARM execution tests and this review/validation note.

No AF implementation or AF registration changes, game behavior changes,
per-camera version overrides, personal build identities, or download/release
scripts are part of this branch. `modules/Makefile`, the per-camera Makefiles
and module selection lists remain identical to the base. The previously added
`src/zh_cn_modules.h` and `src/zh_cn_translations.h` are absent. They were unused
in the previous revision; this revision does not compile catalogs as C arrays.

## Selection and ownership

English is the default and needs no additional catalog or font allocation.
`Prefs -> Language` selects an entry from the external `ML/LANG/INDEX.TXT`.
Save the ML settings and restart to apply it. A stable identifier derived from
the language ID is saved, rather than an index that changes when files move.
Unknown language IDs, invalid/missing catalogs and required-font failures retain
English. The selector reports unavailable resources; unknown strings also use
their original English text.

Startup happens after configuration loading and before normal ML tasks start.
Only the selected catalog and its optional font are retained, in cacheable
memory. The index read and temporary file-I/O buffers are freed. Resource
pointers are immutable for the rest of the boot. Deferred switching is deliberate:
the existing menu/module callers may retain pointers, so this proposal does not
free or replace their backing storage while those tasks are running. Live
switching would require a separate ownership/synchronization design.

German, Polish or another language uses the same loader and compiler. Add a JSON
catalog, compile its `.lng`, add an index row and optionally supply a font. No
language-specific C function or static translated word list is required. The
small selector is bounded to 16 entries including English. The current renderer
supports one-, two- and three-byte UTF-8 glyph keys; valid four-byte characters
advance as one glyph but render as `?` because this BFNT representation lacks
those glyphs. Legacy single-byte RBF symbols are retained.

Translated formats are checked before variadic formatting. Unsupported or
changed printf directives use the original format. The file format stores both
the source and translation, so an FNV collision is resolved with a full source
comparison rather than returning an unrelated string.

## Catalog provenance and coverage

The preserved hash-only dictionary had 2052 entries. Original source keys were
recovered for 1979 by matching source literals/known translation pairs and
original English binary strings against their recorded FNV hashes. Six strings
with ambiguous literal percentage/printf syntax were conservatively held out.
The resulting catalog has 1981 messages including the added language-selector
and neutral UI labels. The remaining 73 unknown keys and six ambiguous labels
are kept in `data/localization/zh_cn-pending.json` for manual review. They are not
loaded into the camera or guessed from their hashes; affected text stays English.
This is not a claim of complete translation coverage on every camera.

Module metadata uses the same file lookup at display time. Module names/help
remain English in their source/build metadata; the core does not embed a Chinese
module-summary table. The original full font-generation input is still unavailable;
the preserved BFNT and its original Noto font license are included. No claim is
made that these tools regenerate that font without its original inputs.

## Validation on 2026-10-20

* Standard-library Python compiler tests: pass.
* Actual ARMv5 C reader under Unicorn 2.1.4: all 1981 compiled catalog lookups,
  missing strings, three language samples, FNV collision lookup, 75 truncations,
  invalid fields/UTF-8/printf directives and 500 deterministic mutations: pass.
* Actual ARM startup/catalog/BFNT loader with mocked file I/O: English/default
  allocation, deferred selection, Chinese/font, another language without a font,
  missing/invalid resources and invalid glyph offsets: pass. UTF-8 and legacy
  symbol iteration checked with fixed glyph widths.
* GCC 12.2.1-1.1 object builds for the nine affected C units on 5D3.123, 70D.112
  and 6D2.111: pass.
* 5D3.123 core linked to `magiclantern.bin` (477224 bytes): pass. Existing TCC
  preprocessor and linker RWX warnings remain. This is not an installable release
  or evidence of startup success on a camera.

No real-camera validation, all-camera clean build, pixel-layout validation,
historical-binary reproduction or upstream acceptance is claimed. Existing
downloadable firmware packages are not changed by this review branch.
