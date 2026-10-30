<!-- machine translation of README.md; the English README is the complete copy -->
# Maintainability Agent

[English](README.md) | [Español](README.es.md) | [Deutsch](README.de.md) | [Français](README.fr.md) | [हिन्दी](README.hi.md) | **简体中文**

> 机器翻译。[英文 README](README.md) 是唯一完整且持续更新的版本。

## 这是什么

一个确定性的、离线的可维护性审计工具，其输出是交给 AI 编程助手的**有边界的工作单**：针对每一项发现，提供一段可直接复制的提示词，内容是*只修复这些问题，不要重构其他任何代码*。它不调用任何语言模型，也不会把你的代码发送给任何服务。评分以成熟的开源仓库为基准进行校准。

主要界面是聊天（为你的 AI 助手提供一个本地 MCP 服务器）；命令行用于 CI 和脚本。

## 安装

```bash
pip install maintainability-agent
```

## 首次运行

```bash
maintainability-agent --root . --output maintainability-report.md
```

聊天/MCP 配置、仅变更模式、基线以及 CI 集成，请参阅[英文 README](README.md)。

## 许可证

MIT。
