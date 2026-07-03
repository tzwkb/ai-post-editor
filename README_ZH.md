# AI Post-Editor

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/)

[English](README.md) | 中文

## 概览

游戏本地化 Excel 批量 AI 后编辑工具，读取中文源文和机器英文译文，输出 MTPE 与 QA 后的修订文件。

## 文档对齐说明

本 README_ZH.md 与英文 README.md 使用同一项目事实，但采用中文读者更容易扫描的结构。命令、路径、配置键和示例数据保持原样。

## 主要能力

- 按项目术语和风格规则处理翻译初稿。
- 组织源文、初译和输出文件。
- 支持在不同项目 profile 之间切换。

## 主要能力

- 批量处理游戏本地化 Excel。
- 调用 LLM 做英文译文后编辑。
- 运行自动 QA 并输出修正后的表格。

## 使用方式

按下方说明准备 Excel 输入、API 配置和输出路径后运行。

## 注意事项

该工具面向 MTPE/QA 工作流，术语和风格要求应来自项目资料。

## 命令与配置参考

以下命令、路径和配置键保持原样，复制时请以实际环境为准。

```bash
python auto_runner.py
```

```bash
pip install -r requirements.txt
```

```bash
cp .env.example .env
```
