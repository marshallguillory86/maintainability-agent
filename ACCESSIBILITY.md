# Accessibility

Maintainability Agent is a command-line tool and a local MCP server. Everything
it produces is text first: a chat or terminal report, a Markdown file, JSON,
SARIF, and an optional single-file HTML report. This page says what that means
for people using assistive technology, what is known not to work well, and how
to report a barrier.

## Commitment

Every finding, score and work-order item is available as plain text. No
information exists only in a chart, a colour or an image: the Markdown, chat
and JSON outputs carry the same report dictionary as the HTML page, so a reader
who cannot use one presentation can choose another (`--format`, or the
presentation question at first run).

## Supported environments

- **Operating systems:** macOS and Linux. Windows is not tested
  ([Decision 18](docs/decisions.md#decision-18-windows-is-not-tested-in-ci)).
- **Terminal output** is plain text with no colour codes, so it reads the same
  in a screen reader, a braille display or a log file.
- **The HTML report** is one self-contained page with no scripts loaded from
  elsewhere. It declares its language (`lang="en"`), and its data sits in HTML
  tables with header cells.
- **Language:** reports are in English. The README has short machine-translated
  summaries in Spanish, German, French, Hindi and Simplified Chinese.

## Known limitations

- **Trend charts in the HTML report** are SVG images with `role="img"` but no
  accessible name of their own; each data point carries a text tooltip. The
  numbers they plot are in the report's tables and in the Markdown and JSON
  outputs.
- **Chart series are told apart by colour and a legend.** There is no pattern
  or shape to separate them for readers who cannot distinguish the colours.
- **Reports are long.** A full report lists every finding; the chat view is
  bounded and points to the full report rather than reading all of it out.

## Reporting a barrier

Open an issue at
<https://github.com/marshallguillory86/maintainability-agent/issues> and say
which output you were using (chat, terminal, Markdown, HTML or JSON), the
assistive technology involved if any, and what you could not do. Barriers are
treated as defects.
