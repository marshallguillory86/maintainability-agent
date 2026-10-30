<!-- machine translation of README.md; the English README is the complete copy -->
# Maintainability Agent

[English](README.md) | **Español** | [Deutsch](README.de.md) | [Français](README.fr.md) | [हिन्दी](README.hi.md) | [简体中文](README.zh-CN.md)

> Traducción automática. El [README en inglés](README.md) es la versión completa y la única que se mantiene al día.

## Qué es

Una auditoría de mantenibilidad determinista y sin conexión cuyo resultado es una
**orden de trabajo acotada** para un agente de programación con IA: para cada
hallazgo, un prompt listo para copiar que dice *corrige exactamente esto y no
refactorices nada más*. No usa modelos de lenguaje ni envía tu código a ningún
servicio. Las calificaciones están calibradas con repositorios de código abierto
maduros.

La interfaz principal es el chat (un servidor MCP local para tu asistente de IA);
la CLI sirve para CI y scripts.

## Instalación

```bash
pip install maintainability-agent
```

## Primer uso

```bash
maintainability-agent --root . --output maintainability-report.md
```

La configuración del chat/MCP, el modo de solo cambios, las líneas base y la
integración con CI se describen en el [README en inglés](README.md).

## Licencia

MIT.
