<!-- machine translation of README.md; the English README is the complete copy -->
# Maintainability Agent

[English](README.md) | [Español](README.es.md) | **Deutsch** | [Français](README.fr.md) | [हिन्दी](README.hi.md) | [简体中文](README.zh-CN.md)

> Maschinelle Übersetzung. Das [englische README](README.md) ist die vollständige und einzige laufend gepflegte Fassung.

## Was es ist

Ein deterministisches Offline-Audit der Wartbarkeit, dessen Ergebnis ein
**begrenzter Arbeitsauftrag** für einen KI-Coding-Agenten ist: für jeden Befund
ein kopierfertiger Prompt, der sagt: *Behebe genau dies und refaktoriere nichts
anderes*. Es verwendet kein Sprachmodell und sendet deinen Code an keinen Dienst.
Die Noten sind an ausgereiften Open-Source-Repositories kalibriert.

Die wichtigste Oberfläche ist der Chat (ein lokaler MCP-Server für deinen
KI-Assistenten); die CLI dient für CI und Skripte.

## Installation

```bash
pip install maintainability-agent
```

## Erster Lauf

```bash
maintainability-agent --root . --output maintainability-report.md
```

Chat-/MCP-Einrichtung, der Modus nur für Änderungen, Baselines und die
CI-Integration sind im [englischen README](README.md) beschrieben.

## Lizenz

MIT.
