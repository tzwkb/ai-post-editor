# AI Post-Editor

<!-- bilingual-readme:start -->

## 双语说明 / Bilingual Documentation

> 本节提供整篇 README 的中英双语维护说明；下方保留原始详细说明、命令、路径和配置示例。
> This section provides bilingual maintenance notes for the full README; the original detailed notes, commands, paths, and configuration examples are preserved below.

### 中文

**概览**：游戏本地化 Excel 批量 AI 后编辑工具，读取中文源文和机器英文译文，输出 MTPE 与 QA 后的修订文件。

**主要能力**：
- 批量处理游戏本地化 Excel。
- 调用 LLM 做英文译文后编辑。
- 运行自动 QA 并输出修正后的表格。

**使用方式**：按下方说明准备 Excel 输入、API 配置和输出路径后运行。

**状态**：该仓库仍按当前 README 的说明维护或使用。

**注意事项**：该工具面向 MTPE/QA 工作流，术语和风格要求应来自项目资料。

### English

**Overview**: Batch AI post-editing tool for game-localization Excel files, reading Chinese source and MT English, then outputting MTPE/QA-corrected files.

**Key capabilities**:
- Batch-processes game-localization Excel files.
- Calls an LLM for English MTPE.
- Runs automated QA and writes corrected spreadsheets.

**Usage**: Prepare Excel input, API configuration, and output paths as described below.

**Status**: This repository is maintained or used according to the current README notes.

**Notes**: The tool targets MTPE/QA workflows; terminology and style rules should come from project references.

<!-- bilingual-readme:end -->

Batch-process game-localization Excel files: read Chinese source text + machine-translated English, call an LLM for post-editing (MTPE), run automated QA checks, and output corrected Excel files.

## Quick Start

```bash
python auto_runner.py
```

All paths and parameters are hard-coded in `auto_runner.py`.

## Install

```bash
pip install -r requirements.txt
```

The first run downloads `paraphrase-multilingual-MiniLM-L12-v2` (requires internet); afterwards it uses local cache.

## Setup

Copy `.env.example` to `.env` and fill in your API key:

```bash
cp .env.example .env
```

## Structure

| File | Purpose |
|------|---------|
| `main.py` | Interactive TUI entry point |
| `auto_runner.py` | Non-interactive batch entry point |
| `engine.py` | Core engine: MTPE pipeline, async scheduling, TM/TB integration |
| `qa_module.py` | QA checks + auto-repair loop |
| `config.py` | API settings, paths, output columns, batch size |
| `prompts/mtpe_base.md` | Universal MTPE rules |
| `prompts/mtpe_project_*.md` | Project-specific context (world, characters, terminology) |
| `prompts/qa.md` | AI QA system prompt |

## Features

- **Async concurrency** — All API calls are parallel (`AsyncOpenAI` + `asyncio.Semaphore`)
- **ST deduplication** — Identical source text is sent to the API only once, results are reused
- **Resume support** — Skips already-processed rows if the output file exists
- **Semantic TM matching** — Sentence-embedding cosine similarity for translation-memory lookup; results are cached as `.npy`
- **AI QA** — Automated checks for tags, punctuation, terminology consistency, omissions/over-translations, and context; failed rows are auto-repaired (up to 2 iterations)
- **Checkpoint debounce** — Crash recovery loses at most 5 seconds of work
- **Audit logging** — Records every API call and full run history

## Switching Projects

1. Create `prompts/mtpe_project_newgame.md` with game background, terminology rules, and style requirements.
2. Update `config.py`: `MTPE_PROJECT_FILE = "mtpe_project_newgame.md"`
3. Run `python auto_runner.py`

## Output

- `output/*_postedit.xlsx` — Post-edited results with QA annotation columns
- `logs/` — Detailed API request logs per run
- `run_log.xlsx` — Persistent run history (rows processed, duration, pass rate)