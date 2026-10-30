<!-- machine translation of README.md; the English README is the complete copy -->
# Maintainability Agent

[English](README.md) | [Español](README.es.md) | [Deutsch](README.de.md) | **Français** | [हिन्दी](README.hi.md) | [简体中文](README.zh-CN.md)

> Traduction automatique. Le [README en anglais](README.md) est la version complète et la seule tenue à jour.

## Ce que c'est

Un audit de maintenabilité déterministe et hors ligne dont le résultat est un
**ordre de travail borné** pour un agent de programmation IA : pour chaque
constat, un prompt prêt à copier qui dit *corrige exactement ceci et ne refactorise
rien d'autre*. Il n'utilise aucun modèle de langage et n'envoie votre code à aucun
service. Les notes sont calibrées sur des dépôts open source matures.

L'interface principale est le chat (un serveur MCP local pour votre assistant
IA) ; la CLI sert à la CI et aux scripts.

## Installation

```bash
pip install maintainability-agent
```

## Premier lancement

```bash
maintainability-agent --root . --output maintainability-report.md
```

La configuration chat/MCP, le mode « modifications seulement », les références
(baselines) et l'intégration CI sont décrits dans le [README en anglais](README.md).

## Licence

MIT.
