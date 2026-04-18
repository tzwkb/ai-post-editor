# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/) 格式。

---

## [Unreleased]

---

## [2026-04-13]

### Added

- **TM引擎升级**：将 TF-IDF 替换为 Sentence Embedding（`paraphrase-multilingual-MiniLM-L12-v2`），使用 cosine 相似度，阈值 0.55；匹配质量显著提升。
- **Embedding 缓存**：TM 向量缓存为 `.npy` 文件（与 TM 文件同目录），Query 向量运行期内缓存，避免重复编码；加载时改为单次读取 `.npy`（原先读取两次）。
- **AI QA 模块**（`qa_module.py`，全新）：
  - Layer 1：AI 语义检查，基于 `qa.md` prompt，返回结构化 JSON。
  - 修复循环：最多迭代 2 次，使用 `ThreadPoolExecutor` 并行修复。
  - 输出新列：`QA Status`（问题标记）、`QA Fixed`（修复译文）。
  - 超过 1500 行自动分批处理，相邻批次保留 50 行重叠以维持上下文。
- **异步 IO + 多线程**：主 MTPE 流程改为 `asyncio.run(_run_async())`，HTTP 请求改用 `AsyncOpenAI`；`asyncio.Semaphore(MAX_WORKERS)` 限制并发；TM 查询通过 `run_in_executor` 卸载到线程池。
- **Checkpoint debounce**：每个 cluster 完成即触发保存，5 秒 debounce 防止高频写盘，程序结束时强制 flush。
- **Prompt 分层**：拆分为通用层（`mtpe_base.md`）与项目层（`mtpe_project_neoepoch.md`）；由 `config.MTPE_PROJECT_FILE` 控制项目切换；运行时拼接并缓存，避免重复 IO。
- **API 日志**：每次运行生成独立日志文件 `logs/api_YYYYMMDD_HHMMSS.jsonl`，记录 `messages`、`response`、`error`、`ts`、`model` 字段；程序启动时调用 `init_api_log()` 初始化。
- **运行日志**：`run_log.xlsx` 中每次运行追加一行，字段：序号、时间、测试文件、AI QA 结果。
- **Per-row 术语命中**：MTPE 阶段为每行记录实际命中的术语对，QA 阶段精确注入该行的术语上下文，替代原先的全局术语表批量注入。

### Changed

- 提取 `_build_cluster_messages()` 辅助函数，消除 `call_api_cluster` 同步/异步两个版本之间的重复代码。
- `_null_semaphore` 改为模块级单例 `_NULL_SEMAPHORE`，避免每次调用重复创建。
- 行命中计数改用集合交集计算，逻辑更严谨。

### Removed

- 删除旧的 `prompts/mtpe.md`（已由分层 prompt 取代）。
- 删除 `qa_module.py` 中未使用的 `threading.Lock` 引入。
- 删除 `_save_workbook` 中冗余的局部 `import datetime`。

### Fixed

- 修复 `do_repair` 闭包错误捕获可变变量 `still_failing` 的 bug，改为 default-arg 快照传入，确保每次修复循环持有正确的失败行快照。
- `EmbeddingIndex.query` 中 `float(sims[i])` 由多次计算改为 walrus operator 单次计算，消除重复开销。

---

## [2026-04-13 v2]

### Added

- **引号自动补全**（`engine.py` `_sanitize()`）：新增 `_fix_dangling_quotes()` 函数，逐行检测句首/句尾不对称的双引号/单引号，自动补全另一侧；单引号仅处理长度 > 3 的文本以避免误触发所有格 `'s`。
- **MTPE 上下文行注入**（`engine.py` `process_cluster_async()`）：当 `config.MTPE_CONTEXT_ROWS > 0` 时，自动取当前行前 N 行的 ST+TT 文本，以 `Adjacent context (preceding rows — for reference only)` 形式注入 `ref_data`，AI 可见前序内容以提升跨行一致性；默认 `MTPE_CONTEXT_ROWS = 5`。
- **`config.MTPE_CONTEXT_ROWS`**（`config.py`）：新增参数，控制上下文注入行数，`0` 为禁用。
- **拟声词 TM 过滤**（`engine.py`）：新增 `_is_onomatopoeia()` 函数，通过 Unicode 正则识别哈/嘿/啊/嗯等单字拟声词；TM 查询条件改为 `if tm_index and st_text.strip() and not _is_onomatopoeia(st_text)`，拟声词行跳过 TM 查询，避免情绪语境不同时 TM 误导。

### Changed

- **破折号禁用范围扩展**（`prompts/mtpe_base.md`）：Em-dash 禁用范围从 `dialogue`（仅对话）扩展为 `ALL text (dialogue and narration)`，旁白中也严禁使用破折号。
- **拟声词 Prompt 规则**（`prompts/mtpe_base.md`）：PART 4 末尾追加 `【Onomatopoeia】` 规则块，要求拟声词/感叹词按情感和语境翻译，忽略 TM 参考。
- `_sanitize()` 第 4 步 em-dash 正则替换（`\s*[–—]\s*` → `, `）兜底覆盖 API 返回中残留的破折号。
