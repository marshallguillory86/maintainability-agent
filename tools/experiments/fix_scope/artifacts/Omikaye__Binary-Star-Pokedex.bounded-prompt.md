# AI Remediation Prompt

You are working in a git repository that has just produced a maintainability audit.

Your task is to fix the highest-value maintainability issues in a small, reviewable change.

Rules:

- Do not rewrite the whole codebase.
- Do not change public behavior unless a finding explicitly requires it.
- Prefer existing architecture, naming, and local patterns.
- Add or update tests for meaningful behavior before changing production code where practical.
- Keep unrelated refactors out of scope.
- If a finding is a false positive, explain why and leave the code unchanged.
- After changes, run the repo's native tests/lints and this maintainability audit again.

Audit summary:

- Overall score: 2.7 / 5 (D)
- Files scanned: 87
- File failures: 7
- Function failures: 61
- Duplicate blocks: 3126
- Risk findings: 7
- Hard gate failures: 0

Where this repo is worse than typical real-world code
(1.0x = the median of a mature open-source corpus; only elevated dimensions are listed):

- **duplication** at 9.62x — repeated blocks — consolidate only where the copies represent the same responsibility
- **declarations** at 4.4x — functions that are too long or too branchy to hold in your head at once
- **file_size** at 2.18x — files carrying too many responsibilities — split along a real boundary, never by line count
- **risk** at 1.11x — configured risk patterns that need a human decision, not a blanket rewrite

Start with `duplication`. It is the dimension costing this repo the most.

- Grade capped: no test evidence found: A-grades require it

Function hotspots to inspect first:

- `ts/battle-dex-search.ts:177` `DexSearch` (class) (564 lines, fail).
- `ts/battle-dex-search.ts:365` `textSearch` (279 lines, complexity 80, cognitive 163, fail).
- `scripts/import-moves.js:16` `parseMovesTxt` (192 lines, complexity 53, cognitive 169, fail).
- `scripts/import-trainers.js:17` `parse` (148 lines, complexity 50, cognitive 108, fail).
- `scripts/sync-google-sheets-locations.js:259` `convertSheetToLocations` (107 lines, complexity 39, cognitive 101, fail).
- `scripts/test-battle-parsing.js:180` `convertSheetToLocations` (95 lines, complexity 39, cognitive 101, fail).
- `scripts/test-sheets-parsing.js:158` `convertSheetToLocations` (86 lines, complexity 36, cognitive 86, fail).
- `ts/battle-dex-search.ts:922` `getDefaultResults` (86 lines, complexity 33, cognitive 80, fail).
- `scripts/convert-evolutions.js:37` `parseEvolutionLine` (106 lines, complexity 32, cognitive 122, fail).
- `ts/battle-dex-search.ts:1067` `getDefaultResults` (80 lines, complexity 31, cognitive 77, fail).

Large files to inspect for responsibility splits:

- `data/BaseGameLearnsets.ts` has 94010 lines (fail).
- `theme/font-awesome.css` has 2337 lines (fail).
- `ts/battle-dex-search.ts` has 1524 lines (fail).
- `js/pokedex.js` has 1363 lines (fail).
- `js/search.js` has 1300 lines (fail).
- `js/panels.js` has 1026 lines (fail).
- `js/pokedex-locations.js` has 806 lines (fail).
- `js/pokedex-pokemon.js` has 789 lines (warn).
- `js/pokedex-pokeedit.js` has 776 lines (warn).
- `theme/pokedex.css` has 649 lines (warn).

Risk pattern findings to verify:

- `README.md:2` debt-marker: A Pokedex for the rom hack Pokemon Binary Star by Omikaye
- `js/panels.js:670` debt-marker: // TODO: all other panel animation
- `js/panels.js:901` debt-marker: // TODO: finish
- `js/panels.js:1010` debt-marker: // TODO
- `js/pokedex-home.js:21` debt-marker: buf += '<p class="resultsub">A comprehensive Pokédex for the Pokémon Binary Star ROM hack by Omikaye</p>';
- `js/pokedex-home.js:25` debt-marker: buf += '<h2>About the ROM Hack</h2>';
- `js/pokedex-home.js:26` debt-marker: buf += '<p>Pokémon Binary Star is a custom ROM hack featuring new adventures, expanded Pokédex entries, custom encounters, and a reimagined region. Explore new locations, battle un

Duplicate blocks to inspect:

- Repeated block appears 9 times near: scripts/sync-google-sheets-encounter-locations.js:46, scripts/sync-google-sheets-item-locations.js:51, scripts/sync-google-sheets-locations.js:46, scripts/sync-google-sheets-shop-tables.js:46, scripts/test-battle-parsing.js:12
- Repeated block appears 9 times near: scripts/sync-google-sheets-encounter-locations.js:47, scripts/sync-google-sheets-item-locations.js:52, scripts/sync-google-sheets-locations.js:47, scripts/sync-google-sheets-shop-tables.js:47, scripts/test-battle-parsing.js:13
- Repeated block appears 9 times near: scripts/sync-google-sheets-encounter-locations.js:56, scripts/sync-google-sheets-item-locations.js:61, scripts/sync-google-sheets-locations.js:56, scripts/sync-google-sheets-shop-tables.js:56, scripts/test-battle-parsing.js:22
- Repeated block appears 9 times near: scripts/sync-google-sheets-encounter-locations.js:57, scripts/sync-google-sheets-item-locations.js:62, scripts/sync-google-sheets-locations.js:57, scripts/sync-google-sheets-shop-tables.js:57, scripts/test-battle-parsing.js:23
- Repeated block appears 9 times near: scripts/sync-google-sheets-encounter-locations.js:58, scripts/sync-google-sheets-item-locations.js:63, scripts/sync-google-sheets-locations.js:58, scripts/sync-google-sheets-shop-tables.js:58, scripts/test-battle-parsing.js:24

Near-duplicate logic — prefer reusing the existing declaration over keeping both:

- `scripts/sync-google-sheets-encounter-locations.js:122` `parseLevelRange` is 100% identical to `parseLevelRange` at `scripts/test-encounter-parsing.js:91` (different file — likely written without knowing the first existed)
- `scripts/sync-google-sheets-encounter-locations.js:159` `parseEncounterDataRow` is 100% identical to `parseEncounterDataRow` at `scripts/test-encounter-parsing.js:107` (different file — likely written without knowing the first existed)
- `scripts/sync-google-sheets-encounter-locations.js:207` `parseEncounterBlock` is 100% identical to `parseEncounterBlock` at `scripts/test-encounter-parsing.js:142` (different file — likely written without knowing the first existed)
- `scripts/sync-google-sheets-encounter-locations.js:22` `fetchCSV` is 100% identical to `fetchCSV` at `scripts/sync-google-sheets-item-locations.js:26` (different file — likely written without knowing the first existed)
- `scripts/sync-google-sheets-encounter-locations.js:22` `fetchCSV` is 100% identical to `fetchCSV` at `scripts/sync-google-sheets-locations.js:22` (different file — likely written without knowing the first existed)
- `scripts/sync-google-sheets-encounter-locations.js:22` `fetchCSV` is 100% identical to `fetchCSV` at `scripts/sync-google-sheets-shop-tables.js:28` (different file — likely written without knowing the first existed)
- `scripts/sync-google-sheets-encounter-locations.js:54` `parseCSV` is 100% identical to `parseCSV` at `scripts/sync-google-sheets-locations.js:55` (different file — likely written without knowing the first existed)
- `scripts/sync-google-sheets-encounter-locations.js:54` `parseCSV` is 100% identical to `parseCSV` at `scripts/test-battle-parsing.js:23` (different file — likely written without knowing the first existed)
- `scripts/sync-google-sheets-encounter-locations.js:54` `parseCSV` is 100% identical to `parseCSV` at `scripts/test-encounter-parsing.js:40` (different file — likely written without knowing the first existed)
- `scripts/sync-google-sheets-encounter-locations.js:54` `parseCSV` is 100% identical to `parseCSV` at `scripts/test-sheets-parsing.js:25` (different file — likely written without knowing the first existed)

Collapse a pair only when both copies genuinely represent the same responsibility. Two functions that merely look alike today, and would need to change for different reasons tomorrow, should stay separate — say so rather than merging them.

Deliverable:

1. Briefly restate which findings you will fix.
2. Make the smallest coherent patch.
3. Add or update tests when behavior changes or when the current code is hard to verify.
4. Report commands run and results.
5. Leave any larger architectural recommendations as follow-up items, not hidden extra changes.