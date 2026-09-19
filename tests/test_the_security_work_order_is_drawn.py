"""The HTML report draws the delegate's work order rather than quoting it (D197).

`complete_html` wrapped the delegate's Markdown in `<pre>` — "the same
text, preformatted". So an operator who chose an HTML presentation got
raw Markdown inside it: `##` headings, asterisks for bold, backticks
around code, in a page where everything else was rendered.

The fix is not a Markdown parser. Prose is the one thing this tool cannot
re-present, and parsing another tool's prose to draw it is worse than the
symptom. `secure-code-agent` now emits the same work order as facts (its
D27) and this renders them.

What must not change is whose work order it is. ADR 007 §1 says this tool
does not re-rank, merge or reword security findings, so the data is drawn
in the delegate's own tiers, order and counts — a different presentation
of the same work, never a different opinion about it.
"""

from __future__ import annotations

from maintainability_audit._security_work_order import KEY, carried, complete_html


def _entry() -> dict:
    return {"delegated_to": "secure-code-agent", "producer_version": "0.12.8"}


def _data() -> dict:
    return {
        "schema_version": 1,
        "counts": {"fix": 2, "review": 1, "accept": 17},
        "fix": {
            "shown": [
                {
                    "rule_id": "B608",
                    "scanner": "bandit",
                    "title": "SQL injection",
                    "message": "Possible SQL injection",
                    "fix_hint": "Use a parameterised query.",
                    "severity": "high",
                    "confidence": "high",
                    "location": "src/app.py:12-14",
                    "code_snippet": "query = 'SELECT ' + name",
                    "standards": {"cwe": "CWE-89", "owasp_top10": "A03",
                                  "asvs_section": "V5.3", "nist_ssdf": "PW.5.1"},
                    "review_note": None,
                },
            ],
            "omitted": 3,
        },
        "review": {
            "shown": [
                {
                    "rule_id": "B105",
                    "scanner": "bandit",
                    "title": "Possible hardcoded password",
                    "message": "Possible hardcoded password",
                    "fix_hint": None,
                    "severity": "low",
                    "confidence": "low",
                    "location": "src/consts.py:3",
                    "code_snippet": None,
                    "standards": {"cwe": None, "owasp_top10": None,
                                  "asvs_section": None, "nist_ssdf": None},
                    "review_note": "the rule matches a name, not a value",
                },
            ],
            "omitted": 0,
        },
        "accept": {"summary": "17 in the test tree."},
    }


def _html(data: dict | None) -> str:
    order = carried("# Security work order\n\n## Hard constraints\n", _entry(), data)
    return "\n".join(complete_html({KEY: order}))


# --- drawn, not quoted -----------------------------------------------------


def test_markdown_syntax_does_not_reach_the_page() -> None:
    """The symptom, asserted directly.

    A `##` or a `**` in the rendered page means a reader is looking at
    source instead of a report.
    """
    html = _html(_data())

    assert "<pre># Security work order" not in html
    assert "## Hard constraints" not in html


def test_a_finding_is_rendered_as_elements() -> None:
    html = _html(_data())

    assert "<code>B608</code>" in html
    assert "SQL injection" in html
    assert "<code>src/app.py:12-14</code>" in html
    assert "Use a parameterised query." in html


def test_the_code_snippet_stays_preformatted() -> None:
    """`<pre>` is right for a quoted snippet and wrong for the whole order."""
    assert "<pre>query = &#x27;SELECT &#x27; + name</pre>" in _html(_data())


def test_the_citation_is_drawn() -> None:
    html = _html(_data())

    assert "CWE-89" in html
    assert "ASVS V5.3" in html
    assert "SSDF PW.5.1" in html
    assert "high/high via bandit" in html


# --- it is still the delegate's work order ---------------------------------


def test_the_delegate_is_named_as_the_author() -> None:
    """ADR 007 §1: this tool reproduces, it does not adopt."""
    html = _html(_data())

    assert "secure-code-agent 0.12.8" in html
    assert "not re-ranked" in html


def test_the_counts_are_the_delegate_s_own() -> None:
    html = _html(_data())

    assert "<strong>2</strong> to fix" in html
    assert "<strong>1</strong> to review" in html
    assert "<strong>17</strong> suppression candidates" in html


def test_a_capped_tier_says_how_many_are_missing() -> None:
    """The delegate capped the list; a reader must not think this is all."""
    assert "3 more not shown" in _html(_data())


def test_a_review_finding_shows_why_it_was_demoted() -> None:
    html = _html(_data())

    assert "Check first:" in html
    assert "the rule matches a name, not a value" in html


# --- an older delegate is still readable -----------------------------------


def test_without_data_the_markdown_is_still_carried() -> None:
    """A supported older release sends no data, and preformatted prose is
    the honest rendering of prose — better than a blank section."""
    html = _html(None)

    assert "<pre># Security work order" in html

