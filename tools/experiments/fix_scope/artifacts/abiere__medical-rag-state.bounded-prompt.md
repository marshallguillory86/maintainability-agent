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

- Overall score: 3.0 / 5 (C)
- Files scanned: 71
- File failures: 8
- Function failures: 82
- Duplicate blocks: 415
- Risk findings: 0
- Hard gate failures: 1

Where this repo is worse than typical real-world code
(1.0x = the median of a mature open-source corpus; only elevated dimensions are listed):

- **declarations** at 2.89x — functions that are too long or too branchy to hold in your head at once
- **file_size** at 2.62x — files carrying too many responsibilities — split along a real boundary, never by line count
- **duplication** at 1.56x — repeated blocks — consolidate only where the copies represent the same responsibility

Start with `declarations`. It is the dimension costing this repo the most.

- Grade capped: no test evidence found: A-grades require it

Start with these hard gates:

- A README is required but none was found.

Function hotspots to inspect first:

- `scripts/nightly_maintenance.py:151` `MaintenanceRunner` (class) (1334 lines, fail).
- `web/app.py:2566` `library_page` (1246 lines, complexity 253, cognitive 9, fail).
- `web/app.py:5302` `settings_page` (1114 lines, complexity 204, fail).
- `scripts/run_tests.py:669` `IntegrationTests` (class) (400 lines, fail).
- `web/app.py:4582` `library_ingest_page` (296 lines, complexity 64, fail).
- `web/app.py:6926` `images_page` (429 lines, complexity 63, cognitive 48, fail).
- `web/app.py:7577` `search_page` (335 lines, complexity 62, cognitive 2, fail).
- `scripts/book_metadata_vision.py:559` `_fetch_isbnsearch` (126 lines, complexity 46, cognitive 61, fail).
- `scripts/nightly_maintenance.py:434` `_phase_consistency` (138 lines, complexity 41, cognitive 68, fail).
- `web/app.py:3817` `api_library_items` (159 lines, complexity 40, cognitive 98, fail).

Large files to inspect for responsibility splits:

- `web/app.py` has 8960 lines (fail).
- `scripts/nightly_maintenance.py` has 1494 lines (fail).
- `scripts/ingest_books.py` has 1291 lines (fail).
- `scripts/parse_pdf.py` has 1279 lines (fail).
- `scripts/book_metadata_vision.py` has 1188 lines (fail).
- `scripts/book_ingest_queue.py` has 1150 lines (fail).
- `scripts/run_tests.py` has 1127 lines (fail).
- `scripts/generate_protocol.py` has 854 lines (fail).
- `scripts/fetch_book_metadata.py` has 776 lines (warn).
- `scripts/parse_epub.py` has 562 lines (warn).

Duplicate blocks to inspect:

- Repeated block appears 4 times near: scripts/book_metadata_vision.py:785, scripts/book_metadata_vision.py:820, web/app.py:1897, web/app.py:4127
- Repeated block appears 4 times near: scripts/book_metadata_vision.py:786, scripts/book_metadata_vision.py:821, web/app.py:1898, web/app.py:4128
- Repeated block appears 4 times near: web/app.py:3459, web/app.py:3564, web/app.py:3618, web/app.py:3678
- Repeated block appears 3 times near: scripts/book_metadata_vision.py:784, scripts/book_metadata_vision.py:819, web/app.py:1816
- Repeated block appears 3 times near: scripts/book_metadata_vision.py:787, web/app.py:1899, web/app.py:4129

Near-duplicate logic — prefer reusing the existing declaration over keeping both:

- `scripts/fetch_book_metadata.py:388` `_format_apa_authors` is 92% identical to `_format_apa_authors` at `scripts/ingest_books.py:267` (different file — likely written without knowing the first existed)
- `scripts/fetch_book_metadata.py:411` `_format_vancouver_authors` is 92% identical to `_format_vancouver_authors` at `scripts/ingest_books.py:291` (different file — likely written without knowing the first existed)
- `scripts/nightly_stats.py:37` `record_retroaudit` is 100% identical to `record_image_screening` at `scripts/nightly_stats.py:62`
- `scripts/run_tests.py:824` `test_status_snapshot_endpoint` is 82% identical to `test_logs_transcription_queue_endpoint` at `scripts/run_tests.py:838`

Collapse a pair only when both copies genuinely represent the same responsibility. Two functions that merely look alike today, and would need to change for different reasons tomorrow, should stay separate — say so rather than merging them.

Unreferenced private declarations — candidates for deletion:

- `scripts/parse_pdf.py:332` `_parse_docling` (58 lines) is private and referenced nowhere in the repository
- `web/app.py:2030` `_usability_dots` (24 lines) is private and referenced nowhere in the repository
- `scripts/ingest_books.py:147` `_get_ollama_vision_model` (21 lines) is private and referenced nowhere in the repository
- `scripts/transcription_queue.py:264` `_transcribe_segment` (16 lines) is private and referenced nowhere in the repository
- `web/app.py:2015` `_book_hash_for_file` (13 lines) is private and referenced nowhere in the repository
- `web/app.py:7563` `_score_bar` (11 lines) is private and referenced nowhere in the repository
- `scripts/fetch_book_metadata.py:513` `_merge` (7 lines) is private and referenced nowhere in the repository
- `web/app.py:7555` `_tag_badge` (7 lines) is private and referenced nowhere in the repository

Confirm each one before deleting. A name reached only through dynamic dispatch — `getattr`, a string-keyed lookup table, a framework that resolves by convention — is indistinguishable from a dead one here. If a finding is reachable that way, say so and leave it.

Deliverable:

1. Briefly restate which findings you will fix.
2. Make the smallest coherent patch.
3. Add or update tests when behavior changes or when the current code is hard to verify.
4. Report commands run and results.
5. Leave any larger architectural recommendations as follow-up items, not hidden extra changes.