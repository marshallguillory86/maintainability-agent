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

- Overall score: 4.2 / 5 (B)
- Files scanned: 91
- File failures: 1
- Function failures: 19
- Duplicate blocks: 79
- Risk findings: 0
- Hard gate failures: 0

Where this repo is worse than typical real-world code
(1.0x = the median of a mature open-source corpus; only elevated dimensions are listed):

- **declarations** at 1.73x — functions that are too long or too branchy to hold in your head at once

Start with `declarations`. It is the dimension costing this repo the most.

Function hotspots to inspect first:

- `src/components/AddWizard.tsx:34` `AddWizard` (470 lines, complexity 63, cognitive 72, fail).
- `src/components/LeafletMap.tsx:62` `LeafletMap` (333 lines, complexity 53, cognitive 110, fail).
- `src/components/PublicAddSheet.tsx:48` `PublicAddSheet` (290 lines, complexity 47, cognitive 55, fail).
- `src/TelegramApp.tsx:34` `TelegramApp` (477 lines, complexity 43, cognitive 41, fail).
- `src/components/PublicMap.tsx:56` `PublicMap` (353 lines, complexity 42, cognitive 82, fail).
- `src/services/submit-place.ts:157` `classifySubmitError` (56 lines, complexity 41, cognitive 58, fail).
- `src/components/PlaceSheet.tsx:31` `PlaceSheet` (162 lines, complexity 33, cognitive 25, fail).
- `src/services/api.ts:196` `createPlace` (102 lines, complexity 30, cognitive 24, fail).
- `src/components/map/MapLibreMap.tsx:76` `MapLibreMap` (236 lines, complexity 27, cognitive 51, fail).
- `src/utils/focusTrap.ts:10` `trapFocus` (29 lines, complexity 21, cognitive 16, fail).

Large files to inspect for responsibility splits:

- `src/styles.css` has 1680 lines (fail).
- `tests/contract/t2-roles-rls.contract.test.ts` has 650 lines (warn).
- `src/TelegramApp.tsx` has 510 lines (warn).
- `src/components/AddWizard.tsx` has 503 lines (warn).
- `src/components/PublicMap.test.tsx` has 441 lines (warn).
- `src/components/PublicMap.tsx` has 408 lines (warn).

Duplicate blocks to inspect:

- Repeated block appears 4 times near: src/components/PublicMap.test.tsx:13, src/components/PublicMap.test.tsx:288, src/components/PublicMap.test.tsx:340, src/components/map/MapLibreMap.test.tsx:106
- Repeated block appears 4 times near: src/components/PublicMap.test.tsx:14, src/components/PublicMap.test.tsx:289, src/components/PublicMap.test.tsx:341, src/components/map/MapLibreMap.test.tsx:107
- Repeated block appears 4 times near: src/components/PublicMap.test.tsx:15, src/components/PublicMap.test.tsx:290, src/components/PublicMap.test.tsx:342, src/components/map/MapLibreMap.test.tsx:108
- Repeated block appears 4 times near: src/components/PublicMap.test.tsx:16, src/components/PublicMap.test.tsx:291, src/components/PublicMap.test.tsx:343, src/components/map/MapLibreMap.test.tsx:109
- Repeated block appears 3 times near: docs/epoch3-inventory-maplibre.md:26, src/components/LeafletMap.tsx:45, src/components/map/types.ts:6

Deliverable:

1. Briefly restate which findings you will fix.
2. Make the smallest coherent patch.
3. Add or update tests when behavior changes or when the current code is hard to verify.
4. Report commands run and results.
5. Leave any larger architectural recommendations as follow-up items, not hidden extra changes.