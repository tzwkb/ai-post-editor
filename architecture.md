# AI 游戏本地化 MTPE+QA 工具 — 架构文档

## 目录结构

```
AI审校/
├── config.py                          # 常量：API配置、路径、输出设置、MTPE_PROJECT_FILE
├── engine.py                          # 核心引擎（~900行）：MTPE主流程、异步调度、TM/TB集成
├── qa_module.py                       # QA检查 + 自动修复流水线
├── auto_runner.py                     # 非交互批处理入口
├── prompts/
│   ├── mtpe_base.md                   # 通用MTPE规则（时态锁定、术语、标点、输出格式）
│   ├── mtpe_project_neoepoch.md       # 项目层（世界观、角色规则、术语覆盖）
│   └── qa.md                          # AI QA系统提示（LQA角色、5维检查、JSON输出格式）
├── TM/
│   ├── 超大TM.xlsx                    # 翻译记忆库（4684+条目）
│   └── 超大TM.embeddings.npy          # 向量缓存
├── TB/
│   └── 【项目资料】Neoepoch.xlsx      # 术语库
├── input/                             # 源文件（.xlsx）
├── output/                            # *_postedit.xlsx 结果
├── logs/                              # api_YYYYMMDD_HHMMSS.jsonl（每次运行一个）
└── run_log.xlsx                       # 持久化运行历史
```

---

## 数据流

```
auto_runner.py
  │
  ├─ 读取 TB → glossary list
  ├─ 读取 TM → EmbeddingIndex（加载/生成 .npy 缓存）
  │
  └─ process_file()
       └─ process_sheet()（逐 sheet 处理）
            ├─ 收集行 → 按相同原文(ST)聚类
            └─ asyncio.run(_run_async())
                 └─ 每个聚类 → asyncio.Task（并发，MAX_WORKERS=100 信号量）
                      ├─ 术语匹配（内联，同步）
                      ├─ TM查询（run_in_executor，向量余弦相似度）
                      └─ 异步 API 调用（AsyncOpenAI）
                           └─ 结果写回 sheet（事件循环线程，openpyxl 非线程安全）
                                └─ Checkpoint 防抖写盘（每5s一次 + 最终刷盘）

输出列：
  "Post Edit EN"  — MTPE译文
  "TM Reference"  — 命中的TM参考

  └─ QA阶段：qa_and_repair()（逐 sheet）
       ├─ ai_qa_sheet()：批量行 → AI QA API → JSON issue list
       └─ repair loop（最多2轮）
            ├─ ThreadPoolExecutor 并行修复
            └─ 再次QA验证
                 └─ 写入 "QA Status" + "QA Fixed" 列

  └─ _run_qa() → _write_log() → run_log.xlsx
```

---

## 核心模块说明

| 模块 | 职责 |
|------|------|
| `config.py` | 集中管理所有路径、API参数、模型名、输出列名等常量 |
| `engine.py` | MTPE主流程：ST聚类、异步任务调度、TM/TB查询、Prompt拼接、断点续跑 |
| `qa_module.py` | AI QA（5维检查）+ 自动修复迭代循环，输出结构化JSON问题列表 |
| `auto_runner.py` | 批处理入口：读取TB/TM → 调engine → 调QA → 写日志 |
| `prompts/mtpe_base.md` | 通用规则层，所有项目共用 |
| `prompts/mtpe_project_*.md` | 项目专属层，运行时与base拼接并缓存 |
| `prompts/qa.md` | QA角色定义与输出格式约定（JSON），独立于MTPE prompt |

---

## 关键设计决策

**异步并发（MTPE热路径）**
- `AsyncOpenAI` + `asyncio.Semaphore(MAX_WORKERS=100)` 控制并发上限
- QA修复循环使用同步 `_call_api_raw`（修复量小，简化控制流）

**ST聚类去重**
- 相同原文合并为一个API调用，结果复制至所有同源行
- 显著降低重复文本的API成本

**向量翻译记忆（EmbeddingIndex）**
- 模型：`paraphrase-multilingual-MiniLM-L12-v2`
- 向量缓存至 `.npy`，首次加载后无需重编码
- 查询向量字典缓存：修复循环中同一ST不重复编码

**Prompt分层**
- base + project 文件运行时拼接，结果缓存（避免重复IO）
- `MTPE_PROJECT_FILE` 在 `config.py` 中切换，支持多项目

**术语上下文传递**
- MTPE阶段每行记录命中术语，传入QA模块，实现精确到行的术语核查

**Checkpoint防抖**
- dirty标志 + 5s写盘间隔，防止高并发下频繁IO（thundering herd）
- 运行结束强制最终刷盘

**断点续跑**
- 检测已有输出文件中的"Post Edit EN"列，跳过已填充行
- 支持中断后从断点继续，避免重复调用API
