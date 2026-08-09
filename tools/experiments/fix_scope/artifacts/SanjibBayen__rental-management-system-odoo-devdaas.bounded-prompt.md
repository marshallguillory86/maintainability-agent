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
- Files scanned: 122
- File failures: 0
- Function failures: 23
- Duplicate blocks: 50
- Risk findings: 0
- Hard gate failures: 0

Where this repo is worse than typical real-world code
(1.0x = the median of a mature open-source corpus; only elevated dimensions are listed):

- **declarations** at 2.29x — functions that are too long or too branchy to hold in your head at once

Start with `declarations`. It is the dimension costing this repo the most.

- Grade capped: no test evidence found: A-grades require it

Function hotspots to inspect first:

- `services/server/src/controllers/user.controller.ts:15` `UserController` (class) (555 lines, fail).
- `services/server/src/controllers/auth.controller.ts:24` `AuthController` (class) (399 lines, fail).
- `services/client/src/App.tsx:27` `App` (47 lines, complexity 29, cognitive 42, fail).
- `services/client/src/components/Navbar.tsx:11` `Navbar` (202 lines, complexity 19, cognitive 14, fail).
- `services/server/src/controllers/user.controller.ts:134` `updateEmail` (94 lines, complexity 18, cognitive 18, fail).
- `services/server/src/controllers/auth.controller.ts:28` `register` (104 lines, complexity 13, cognitive 21, fail).
- `services/client/src/pages/delivery/DeliveryDashboard.tsx:10` `DeliveryDashboard` (109 lines, complexity 11, cognitive 11, fail).
- `services/server/src/middleware/auth.middleware.ts:22` `authMiddleware` (88 lines, complexity 11, cognitive 19, fail).
- `services/client/src/pages/admin/Inventory.tsx:6` `Inventory` (172 lines, complexity 10, cognitive 1, fail).
- `services/client/src/pages/public/Login.tsx:5` `Login` (195 lines, complexity 9, cognitive 6, fail).

Large files to inspect for responsibility splits:

- `services/server/src/controllers/user.controller.ts` has 571 lines (warn).
- `services/server/src/controllers/auth.controller.ts` has 422 lines (warn).

Duplicate blocks to inspect:

- Repeated block appears 5 times near: services/server/src/controllers/user.controller.ts:115, services/server/src/controllers/user.controller.ts:13, services/server/src/controllers/user.controller.ts:198, services/server/src/controllers/user.controller.ts:448, services/server/src/controllers/user.controller.ts:51
- Repeated block appears 5 times near: services/server/src/controllers/user.controller.ts:116, services/server/src/controllers/user.controller.ts:14, services/server/src/controllers/user.controller.ts:199, services/server/src/controllers/user.controller.ts:449, services/server/src/controllers/user.controller.ts:52
- Repeated block appears 5 times near: services/server/src/controllers/user.controller.ts:117, services/server/src/controllers/user.controller.ts:15, services/server/src/controllers/user.controller.ts:200, services/server/src/controllers/user.controller.ts:450, services/server/src/controllers/user.controller.ts:53
- Repeated block appears 5 times near: services/server/src/controllers/user.controller.ts:118, services/server/src/controllers/user.controller.ts:16, services/server/src/controllers/user.controller.ts:201, services/server/src/controllers/user.controller.ts:451, services/server/src/controllers/user.controller.ts:54
- Repeated block appears 3 times near: services/server/src/controllers/user.controller.ts:162, services/server/src/controllers/user.controller.ts:305, services/server/src/controllers/user.controller.ts:81

Near-duplicate logic — prefer reusing the existing declaration over keeping both:

- `services/server/src/controllers/pickup.controller.ts:21` `getPickupById` is 100% identical to `getById` at `services/server/src/controllers/pricelist.controller.ts:26` (different file — likely written without knowing the first existed)
- `services/server/src/controllers/pickup.controller.ts:21` `getPickupById` is 100% identical to `getById` at `services/server/src/controllers/rental.controller.ts:18` (different file — likely written without knowing the first existed)
- `services/server/src/controllers/pickup.controller.ts:21` `getPickupById` is 100% identical to `getReturnById` at `services/server/src/controllers/return.controller.ts:16` (different file — likely written without knowing the first existed)
- `services/server/src/controllers/pricelist.controller.ts:49` `update` is 100% identical to `update` at `services/server/src/controllers/product.controller.ts:52` (different file — likely written without knowing the first existed)
- `services/server/src/controllers/quotation.controller.ts:20` `getQuotation` is 100% identical to `getInvoice` at `services/server/src/controllers/rental.controller.ts:100` (different file — likely written without knowing the first existed)
- `services/server/src/middleware/auth.middleware.ts:22` `authMiddleware` is 100% identical to `authMiddleware` at `services/server/src/middleware/rbac.middleware.ts:32` (different file — likely written without knowing the first existed)

Collapse a pair only when both copies genuinely represent the same responsibility. Two functions that merely look alike today, and would need to change for different reasons tomorrow, should stay separate — say so rather than merging them.

Deliverable:

1. Briefly restate which findings you will fix.
2. Make the smallest coherent patch.
3. Add or update tests when behavior changes or when the current code is hard to verify.
4. Report commands run and results.
5. Leave any larger architectural recommendations as follow-up items, not hidden extra changes.