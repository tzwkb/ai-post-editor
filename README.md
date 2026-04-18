# AI Post-Editor

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
