# Four-language local camera test, r4

English is the built-in original and the first-start default. The existing
Chinese catalog is preserved. German and Polish include every source key in
that catalog, plus the previously reviewed extra menu keys. This is catalog
coverage parity, not a claim of 100% coverage of every possible camera state.

The initial 381 German/Polish menu rows were retained. Additional prose was
drafted locally with the Argos/OpenNMT OPUS-MT English-to-German v1.3 and
English-to-Polish v1.9 models. Long paragraphs were translated with paragraph
context, rewrapped, and camera terminology/format strings received additional
edits. Native-language proofreading is still pending. Source and translation
keys remain explicit in the three JSON catalogs.

r4 supplements that catalog parity check with an inventory of literal UI
strings present in the built 5D3.123 core and the 19 packaged modules. It adds
selected help lines, submenu choices and exact generated module metadata
(including embedded blank lines). The inventory contains 1733 keys, all
present in the three catalogs. Current totals: Chinese 2264, German 2297,
Polish 2297. Technical units, identifiers, credits and URLs can remain unchanged.
An additional pass revised 109 existing German and 102 existing Polish draft
entries, including entries whose translation had remained English. Proper
feature names and words shared by the languages are not automatically errors.

The information view now translates module prose values as well as labels.
Menu rendering recovers an original static key when a display buffer has
truncated it, and the grid view clips translated text at UTF-8 boundaries.
The ARM regression suite executes these display helpers with real catalogs
and mocked card I/O. This static inventory excludes computed strings and
raster documentation, and does not prove every camera state is translated.

No online translation service received the firmware source or strings.
English printf argument types, order and widths are validated when compiling.
Literal percent prose can be explicitly marked format:false; the runtime
printf compatibility guard remains enabled at formatting call sites.
Language resources remain external to the executable. The maintainer reports successful r4 testing on a 5D3 with Canon firmware
1.2.3. This report does not establish coverage or compatibility on other models.
