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

- Overall score: 3.7 / 5 (C)
- Files scanned: 67
- File failures: 1
- Function failures: 32
- Duplicate blocks: 92
- Risk findings: 0
- Hard gate failures: 0

Where this repo is worse than typical real-world code
(1.0x = the median of a mature open-source corpus; only elevated dimensions are listed):

- **declarations** at 3.75x — functions that are too long or too branchy to hold in your head at once

Start with `declarations`. It is the dimension costing this repo the most.

- Grade capped: no test evidence found: A-grades require it

Function hotspots to inspect first:

- `components/venue/RetreatVenue.tsx:20` `RetreatVenue` (366 lines, complexity 88, cognitive 44, fail).
- `components/venue/WellnessVenue.tsx:20` `WellnessVenue` (297 lines, complexity 78, cognitive 33, fail).
- `app/api/apply/route.ts:28` `POST` (124 lines, complexity 65, cognitive 49, fail).
- `components/VenueApplication.tsx:69` `VenueApplication` (346 lines, complexity 63, cognitive 38, fail).
- `app/api/contact/route.ts:24` `POST` (70 lines, complexity 59, cognitive 20, fail).
- `app/api/enquiry/route.ts:15` `POST` (69 lines, complexity 53, cognitive 22, fail).
- `components/VenueFilters.tsx:19` `VenueFilters` (145 lines, complexity 35, cognitive 12, fail).
- `app/the-wellness-edit/[slug]/page.tsx:40` `ArticlePage` (121 lines, complexity 35, cognitive 14, fail).
- `app/the-wellness-edit/page.tsx:47` `WellnessEdit` (144 lines, complexity 31, cognitive 23, fail).
- `components/PricingTable.tsx:32` `PricingTable` (126 lines, complexity 31, cognitive 22, fail).

Large files to inspect for responsibility splits:

- `app/globals.css` has 2465 lines (fail).
- `components/venue/RetreatVenue.tsx` has 442 lines (warn).
- `components/VenueApplication.tsx` has 414 lines (warn).

Duplicate blocks to inspect:

- Repeated block appears 3 times near: components/VenueCard.tsx:113, components/VenueCard.tsx:69, components/VenueCard.tsx:91
- Repeated block appears 2 times near: app/api/contact/route.ts:7, app/api/enquiry/route.ts:3
- Repeated block appears 2 times near: app/api/contact/route.ts:8, app/api/enquiry/route.ts:4
- Repeated block appears 2 times near: app/api/enquiry/route.ts:44, app/api/journal/route.ts:29
- Repeated block appears 2 times near: app/api/enquiry/route.ts:45, app/api/journal/route.ts:30

Deliverable:

1. Briefly restate which findings you will fix.
2. Make the smallest coherent patch.
3. Add or update tests when behavior changes or when the current code is hard to verify.
4. Report commands run and results.
5. Leave any larger architectural recommendations as follow-up items, not hidden extra changes.