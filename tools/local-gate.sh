#!/usr/bin/env bash
# The local gate: lint and the whole suite under the coverage floor, before
# every push. It is how macOS is verified (Decision 18, 2026-10-15): CI runs
# the suite once, on Linux, and this runs it on the maintainer's Mac.
# Installed as the pre-push hook by tools/install-local-gate.sh.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

ruff check src tests tools
python3 -m pytest -n auto -q --cov=maintainability_audit --cov-fail-under=92
