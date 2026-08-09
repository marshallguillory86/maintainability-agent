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
- Files scanned: 218
- File failures: 1
- Function failures: 15
- Duplicate blocks: 606
- Risk findings: 0
- Hard gate failures: 0

Where this repo is worse than typical real-world code
(1.0x = the median of a mature open-source corpus; only elevated dimensions are listed):

- **declarations** at 2.57x — functions that are too long or too branchy to hold in your head at once

Start with `declarations`. It is the dimension costing this repo the most.

- Grade capped: no test evidence found: A-grades require it

Function hotspots to inspect first:

- `frontend/src/pages/Dashboard.tsx:262` `Dashboard` (115 lines, complexity 51, cognitive 14, fail).
- `frontend/src/pages/Coach.tsx:310` `Coach` (337 lines, complexity 35, cognitive 45, fail).
- `frontend/src/pages/MealLog.tsx:110` `FoodItemForm` (207 lines, complexity 30, cognitive 39, fail).
- `frontend/src/pages/Dashboard.tsx:85` `GoalForm` (133 lines, complexity 26, cognitive 12, fail).
- `frontend/src/pages/Profile.tsx:12` `Profile` (218 lines, complexity 23, cognitive 30, fail).
- `frontend/src/pages/Foods.tsx:29` `FoodRow` (132 lines, complexity 18, cognitive 13, fail).
- `frontend/src/lib/api.ts:48` `request` (56 lines, complexity 17, cognitive 28, fail).
- `frontend/src/pages/LoginPage.tsx:14` `LoginPage` (260 lines, complexity 15, cognitive 24, fail).
- `frontend/src/pages/MealLog.tsx:331` `MealLogCard` (147 lines, complexity 13, cognitive 17, fail).
- `frontend/src/pages/MealLog.tsx:662` `TemplatesTab` (151 lines, complexity 12, cognitive 12, fail).

Large files to inspect for responsibility splits:

- `frontend/src/pages/MealLog.tsx` has 908 lines (fail).
- `frontend/src/pages/Coach.tsx` has 646 lines (warn).

Duplicate blocks to inspect:

- Repeated block appears 6 times near: frontend/src/components/Layout.tsx:20, frontend/src/components/Layout.tsx:32, frontend/src/components/Layout.tsx:44, frontend/src/components/Layout.tsx:56, frontend/src/components/Layout.tsx:68
- Repeated block appears 3 times near: frontend/src/pages/Coach.tsx:106, frontend/src/pages/Coach.tsx:155, frontend/src/pages/MealLog.tsx:538
- Repeated block appears 3 times near: frontend/src/pages/Coach.tsx:107, frontend/src/pages/Coach.tsx:156, frontend/src/pages/MealLog.tsx:539
- Repeated block appears 3 times near: frontend/src/pages/Coach.tsx:108, frontend/src/pages/Coach.tsx:157, frontend/src/pages/MealLog.tsx:540
- Repeated block appears 3 times near: frontend/src/pages/Coach.tsx:109, frontend/src/pages/Coach.tsx:158, frontend/src/pages/MealLog.tsx:541

Near-duplicate logic — prefer reusing the existing declaration over keeping both:

- `frontend/src/pages/Coach.tsx:115` `DayNavDatePicker` is 84% identical to `WeekNavDatePicker` at `frontend/src/pages/Coach.tsx:167`

Collapse a pair only when both copies genuinely represent the same responsibility. Two functions that merely look alike today, and would need to change for different reasons tomorrow, should stay separate — say so rather than merging them.

Deliverable:

1. Briefly restate which findings you will fix.
2. Make the smallest coherent patch.
3. Add or update tests when behavior changes or when the current code is hard to verify.
4. Report commands run and results.
5. Leave any larger architectural recommendations as follow-up items, not hidden extra changes.