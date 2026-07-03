# AI Post-Editor

中文 | [English](README.md)

## 概览

游戏本地化 Excel 批量 AI 后编辑工具，读取中文源文和机器英文译文，输出 MTPE 与 QA 后的修订文件。

## 主要能力

- 批量处理游戏本地化 Excel。
- 调用 LLM 做英文译文后编辑。
- 运行自动 QA 并输出修正后的表格。

## 使用方式

按下方说明准备 Excel 输入、API 配置和输出路径后运行。

## 状态

该仓库仍按当前 README 的说明维护或使用。

## 注意事项

该工具面向 MTPE/QA 工作流，术语和风格要求应来自项目资料。

## 命令与配置参考

以下代码块从主 README 保留；命令、路径和配置键不翻译，复制时请以实际环境为准。

```bash
python auto_runner.py
```

```bash
pip install -r requirements.txt
```

```bash
cp .env.example .env
```

## 详细技术说明

主 README 保留了原始技术细节、历史说明、完整命令和文件结构。本文件作为中文版本维护核心说明；需要逐项核对命令时，请参照主 README 的代码块和路径。
