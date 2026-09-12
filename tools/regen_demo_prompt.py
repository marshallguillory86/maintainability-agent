#!/usr/bin/env python3
"""Regenerate `examples/demo/expected-prompt.md`.

Run this when a renderer change legitimately moves the demo's work order,
then **read the diff before committing it**. That diff is the blast radius
of the change on every work order this tool produces, which is the reason
the file is checked in rather than computed in the test.

    python3 tools/regen_demo_prompt.py

The root label is normalised to `.` so the checked-in text is about the
work order and not about where the repository sits on disk.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "demo"

sys.path.insert(0, str(ROOT / "src"))

from maintainability_audit._work_order_view import work_order_markdown  # noqa: E402
from maintainability_audit.config import load_config  # noqa: E402
from maintainability_audit.report import build_report  # noqa: E402


def main() -> int:
    report = build_report(DEMO, load_config(DEMO / "maintainability-agent.json"))
    if not report["work_order"]:
        print("refusing to write an empty work order: the demo found nothing",
              file=sys.stderr)
        return 1
    text = "\n".join(
        work_order_markdown(report["work_order"], complete=True, root_label=".")
    ) + "\n"
    target = DEMO / "expected-prompt.md"
    target.write_text(text, encoding="utf-8")
    print(f"wrote {target.relative_to(ROOT)} — {len(text.splitlines())} lines, "
          f"{len(report['work_order'])} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
