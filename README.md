# Multi-Agent Financial Analyst

一句话：输入股票代码或行业名称，自动收集财报、新闻、研报、市场数据，多 Agent 辩论分析，输出带风险提示和引用来源的投资研究报告。

## 核心特性

- **9 个专业 Agent 协作**：合规预检、任务规划、财报分析、新闻分析、研报分析、数据验证、多空辩论、风控、报告撰写+合规审查
- **真实市场数据**：A股（AKShare）、美股/港股（yfinance）自动路由，覆盖行情、估值、财报、分析师评级、新闻
- **五维度 Agent 评估体系**：财务准确率 / 风险一致性 / 报告完整性 / 分析师共识对比 / 辩论质量（LLM-as-judge），量化衡量 Agent 输出质量
- **多空辩论机制**：多头研究员 vs 空头研究员，主持人裁决，减少单一视角偏见
- **并行数据收集**：财务、新闻、研报三路并行，LangGraph Send fan-out
- **交叉验证**：三源信号对比，自动发现矛盾
- **三层记忆架构**：工作记忆（滑动窗口压缩）+ 情景记忆（跨会话事实抽取）+ 语义记忆（ChromaDB 向量检索）
- **完整可观测性**：Tracer 追踪每个 Agent 事件 + Metrics 指标聚合 + Dashboard 可视化
- **全链路可追溯**：每个结论都有引用来源
- **合规审查**：规则层（禁止词/风险提示/引用）+ LLM 层双重审查
- **四层防注入**：规则过滤 + 标签隔离 + 输出检查 + LLM 验证
- **三级权限**：guest / user / admin，危险工具需二次确认
- **审计日志**：所有操作记录到 SQLite
- **Docker 沙箱**：代码执行禁网、限内存、限 CPU、只读文件系统
- **限流 + 成本熔断**：每用户每分钟/每日请求上限 + 每日成本上限
- **FastAPI 服务**：异步流水线，11 个 REST 接口 + WebSocket 实时推送

## 架构

详见 [docs/architecture.md](docs/architecture.md)

## 快速开始

**环境要求**：
- Python 3.11 或更高
- Node.js 20 或更高（前端需要）

**1. 克隆仓库**

```bash
git clone https://github.com/Yu-Tian-sys/multi-agent-financial-analyst.git
cd multi-agent-financial-analyst
```

**2. 创建虚拟环境并安装后端依赖**

Windows（PowerShell）：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS / Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**3. 配置环境变量**

```bash
cp .env.example .env
```

然后编辑 .env，至少填入你的 DeepSeek API Key：

```text
DEEPSEEK_API_KEY=你的key
```

（API Key 在 `https://platform.deepseek.com/` 申请）

**4. 启动后端**

```bash
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

打开 http://127.0.0.1:8000/docs 可查看 API 文档。

**5. 启动前端 Dashboard（可选）**

前端提供可视化界面，需要另开一个终端：

```bash
cd frontend
npm install
npm run dev
```

浏览器打开终端显示的地址（通常是 http://localhost:5173/）。

---

**Windows 用户可一键启动**

项目根目录提供了 `start.bat`。双击它，会自动开两个窗口（后端 + 前端）并打开浏览器。

- 关闭那两个窗口即可停止服务
- 仅 Windows 有效；macOS / Linux 用户请按上面 4、5 步手动启动

---

## Docker 部署（推荐生产环境）

一键启动后端 + Redis，前端已内置于后端镜像（FastAPI 静态服务）。

**1. 配置环境变量**

```bash
cp .env.example .env
# 编辑 .env，至少填入 DEEPSEEK_API_KEY
```

**2. 构建并启动**

```bash
docker-compose up -d --build
```

**3. 访问**

- 前端 + API：http://localhost:8000
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

**4. 常用命令**

```bash
docker-compose logs -f backend    # 查看后端日志
docker-compose down               # 停止并删除容器
docker-compose down -v            # 同时删除数据卷（清空数据库）
```

**说明**：
- 数据持久化：SQLite 和 ChromaDB 存储在 `app-data` volume
- Redis：限流用，独立容器
- 健康检查：backend 每 30s 探活 `/health`
- 前端构建：Docker 多阶段构建内自动 `npm run build`，无需本地 Node

---

## API 使用

提交分析任务：

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"topic": "AAPL", "user_id": "u1", "user_role": "user"}'
# 返回 {"task_id": "...", "status": "pending", "message": "..."}
```

查询任务状态：

```bash
curl http://127.0.0.1:8000/task/{task_id}
# 流水线约 1-2 分钟，status 从 running 变成 completed
```

查看追踪：

```bash
curl http://127.0.0.1:8000/trace/{task_id}
# 返回 events + mermaid 时序图 + summary
```

全局概览：

```bash
curl http://127.0.0.1:8000/overview
# 返回 Markdown 格式的可观测性报告
```

其他接口：

- `GET /health` — 健康检查
- `GET /metrics` — 今日任务统计
- `GET /cost` — 今日成本统计

运行 Agent 评估（五维度）：

```bash
curl -X POST http://127.0.0.1:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["AAPL", "600519", "00700.HK"]}'
# 返回 {"report": "...", "results": [...]}
# tickers 为空时使用默认 8 只蓝筹股：茅台/招行/宁德/苹果/微软/谷歌/腾讯/美团
```

也可以用 CLI 跑批评估并生成 Markdown 报告：

```bash
python -m src.evaluation.evaluate --tickers AAPL,600519,00700.HK --output docs/evaluation_report.md
```

## 流水线

```text
用户输入
  → 限流（HTTP 层前置：每分钟/每日请求上限）
  → 合规预检（安全+权限+成本熔断）
  → 记忆召回（情景记忆 + 工作记忆压缩）
  → 任务规划（识别公司类型+拆子任务）
  → 并行数据收集（财报 + 新闻 + 研报）
  → 数据验证（交叉验证+矛盾检测）
  → 多空辩论（多头 vs 空头，3 轮 + 主持人裁决）
  → 风控（风险识别+定级+合规提示）
  → 报告撰写（结构化+引用来源）
  → 合规审查（规则+LLM 双重）
  → 五维度评估（财务准确率/风险一致性/报告完整性/分析师共识/辩论质量）
  → 记忆保存（抽取事实存 SQLite）
  → 输出报告
```

## 数据层（真实市场数据）

所有市场数据已从 Mock 切换为真实 API，通过 `MarketRouter` 自动识别市场并路由到对应 Provider。

| 市场 | Provider | 数据源 | 覆盖内容 |
|------|----------|--------|----------|
| A 股 | `AStockProvider` | AKShare（免费） | 行情、PE/PB/PS 估值、三大财报、分析师评级、新闻 |
| 美股 | `USStockProvider` | yfinance | 行情、PE/PB/PS 估值、财报、新闻 |
| 港股 | `HKStockProvider` | yfinance | 行情、估值、财报、新闻 |

- 路由规则：`600519`/`000001` → A 股；`AAPL`/`MSFT` → 美股；`00700.HK` → 港股
- 统一财报结构 `FinancialStatements`（营收/净利润/毛利率/净利率/ROE/资产负债率），跨市场可比
- 估值数据含 TTM 变体（`PE_TTM`、`PB`、`PS_TTM`）
- 工具层封装：`market_data.py`（行情+估值）、`news_search.py`（新闻）、`report_search.py`（分析师评级）

## 评估体系（五维度）

`src/evaluation/` 提供 Agent 输出质量的量化评估，5 个维度各自独立打分（0~1），综合得分取平均。

| 维度 | 评估内容 | 通过阈值 | 实现 |
|------|----------|----------|------|
| 财务指标准确率 | 报告中的营收/净利润/PE/PB 等与真实数据的偏差率 | ≥ 0.6 | 数值比对，容差 20% |
| 风险评级一致性 | Agent 给出的风险等级与基于财务指标的规则风险是否一致 | ≥ 0.6 | 负债率/净利率/关键词规则 vs Agent 结论 |
| 报告完整性 | 6 大章节（摘要/财务/新闻/研报/风险/结论）是否齐全 | ≥ 0.6 | 章节关键词匹配 |
| 分析师共识对比 | Agent 评级与市场分析师一致评级的偏离度 | ≥ 0.5 | 买入/增持/中性/减持/卖出 5 档映射 |
| 辩论质量 | 多空辩论的逻辑深度、论据支撑、反驳力度 | ≥ 0.6 | LLM-as-judge（deepseek-reasoner） |

**Benchmark**：8 只蓝筹股（茅台/招行/宁德/苹果/微软/谷歌/腾讯/美团）的实测评估结果见 [docs/benchmark_data.md](docs/benchmark_data.md)。

## 三层记忆

| 层 | 用途 | 实现 |
|----|------|------|
| 工作记忆 | 当前会话上下文 | `src/memory/working.py` — 滑动窗口 + 摘要压缩 |
| 情景记忆 | 跨会话记住用户事实 | `src/memory/episodic.py` — 抽取 + SQLite 存储 |
| 语义记忆 | RAG 向量检索 | `src/memory/semantic.py` — ChromaDB + bge-small-zh |

## 可观测性

| 模块 | 用途 | 实现 |
|------|------|------|
| Tracer | 记录每个 Agent 的事件 | `src/observability/tracer.py` — 内存 + SQLite 持久化 |
| Metrics | 聚合指标 | `src/observability/metrics.py` — overview / by_agent / latency / errors |
| Dashboard | 可视化 | `src/observability/dashboard.py` — Mermaid 时序图 + Markdown 报告 |

## 技术栈

- Python 3.11
- LangGraph（多 Agent 编排）
- FastAPI（服务层）
- SQLite（状态持久化 + 追踪）
- ChromaDB（语义记忆）
- Docker（沙箱 + 容器化部署）
- Docker Compose（多服务编排：backend + redis）
- DeepSeek API（LLM）
- sentence-transformers（本地嵌入）
- AKShare（A 股数据，免费）
- yfinance（美股/港股数据）
- pandas（数据处理）

## 测试

```bash
# 后端全部测试
pytest tests/ -v
# 138 passed, 2 deselected (e2e)

# 端到端回归（3 个标的，约 5-6 分钟）
python scripts/regression.py

# 前端组件测试
cd frontend && npx vitest run
# 16 passed (ProgressBar / Badge / Stat / StatusDot)
```

## 实际运行数据

端到端回归（3 个标的）：

| 标的 | 状态 | 类型 | 风险 | 合规 | Tokens | 耗时 |
|------|------|------|------|------|--------|------|
| AAPL | completed | 科技 | 高 | ✅ | 26,688 | 45.2s |
| TSLA | completed | 科技 | 高 | ✅ | 29,274 | 48.3s |
| 招商银行 | completed | 银行 | 高 | ✅ | 34,872 | 56.8s |

成功率：100%

总 tokens：90,834

总成本：约 0.09 元

可观测性验证：

- 单次流水线产生 27 条 trace 事件
- 覆盖全部 14 个 Agent
- 追踪数据完整（内存与数据库一致）

## 成本优化

一次流水线原消耗约 26,688 tokens（0.027 元），优化后平均 15,049 tokens（0.015 元），**降幅 43.6%**。

### 三步优化

1. **debate 接入统一模型路由**：把 debate.py 本地 LLM 调用改为走 model_router，为后续优化铺路（不降本）
2. **辩论轮数 3 → 2**：减少 2 次 LLM 调用，且 history 累积变短
3. **辩论前先总结上下文**：把财务/新闻/研报压成 200 字摘要，4 次辩论只发摘要，不再重复传原文

### 实测数据（4 次 AAPL）

| 次数 | tokens | 成本 | 报告长度 |
|------|--------|------|----------|
| 改前基准 | 26,688 | 0.027 元 | — |
| run1 | 14,291 | 0.0143 元 | 2,733 字 |
| run2 | 14,402 | 0.0144 元 | 2,008 字 |
| run3 | 13,869 | 0.0139 元 | 2,504 字 |
| run4 | 17,633 | — | 1,896 字 |
| **平均** | **15,049** | **0.015 元** | **约 2,400 字** |

### 质量验证

人工审阅报告全文，确认优化后未降质：
- 6 个核心财务指标全部保留（营收、净利润、净利率、毛利率、ROE、负债）
- 多空双方各 4 条论据，有数据支撑
- 风险提示 3 大因素，等级 + 来源齐全
- 5 处引用来源
- 6 章结构完整

详见 [docs/cost_optimization.md](docs/cost_optimization.md)。

## 项目结构

```text
multi-agent-financial-analyst/
├── src/
│   ├── state.py              # FinanceState 定义
│   ├── config.py             # 配置管理
│   ├── db.py                 # SQLite 持久化（WAL + 锁）
│   ├── graph.py              # LangGraph 编排 + Tracer 集成
│   ├── main.py               # FastAPI 服务（11 个接口）
│   ├── agents/               # 9 个 Agent
│   ├── tools/                # 6 个工具 + 注册表（market_data/news_search/report_search 已接真实数据）
│   ├── data/                 # 数据层：MarketRouter + AStock/USStock/HKStock Provider
│   ├── evaluation/           # 五维度评估体系（financial_accuracy/risk_consistency/.../evaluate）
│   ├── safety/               # 防注入+权限+审计+沙箱
│   ├── memory/               # 三层记忆
│   └── observability/        # Tracer + Metrics + Dashboard
├── tests/                    # 138 个后端测试
├── frontend/src/test/        # 16 个前端组件测试（vitest）
├── frontend/src/components/  # EvaluationCenter 评估中心页面
├── scripts/
│   └── regression.py         # 端到端回归脚本
├── docs/                     # 架构文档
├── data/                     # 数据目录
└── output/                   # 输出目录
```

## 设计决策

**为什么用 LangGraph？**
需要条件路由、并行 fan-out、状态共享。纯 while 循环写不出来。

**为什么财务/新闻/研报并行？**
三者互相独立，串行会慢 3 倍。LangGraph 的 Send 支持 fan-out。

**为什么多空辩论？**
单 Agent 分析容易片面。多空双方互相反驳，主持人裁决，减少偏见。

**为什么加合规审查？**
金融领域合规是刚需。规则层拦截明显违规，LLM 层检查数据支撑和逻辑。

**为什么用 SQLite？**
轻量、无依赖、够用。生产环境可换 PostgreSQL。

**为什么给 Tracer 加锁 + 开 WAL？**
LangGraph 并行节点在不同线程同时写 traces 表，SQLite 单连接多线程并发写会丢数据。加 `threading.Lock` 串行化写入，开 WAL 模式提升并发性能。复现脚本验证：修复前 60 条丢 12 条，修复后 60==60。

**为什么风险评估用规则+LLM 混合？**
LLM 有随机性，同一标的两次跑可能给出不同风险等级。规则部分保证下限（负债率、净利率、关键词），LLM 部分提供深度分析。

**为什么数据层用 MarketRouter + 多 Provider？**
A 股、美股、港股数据源不同（AKShare vs yfinance），接口字段也不同。用 `MarketRouter` 按代码规则自动路由，`MarketDataProvider` 抽象基类统一返回 `FinancialStatements`/`ValuationData` 结构，上层 Agent 无需关心市场差异。新增市场只需实现一个 Provider。

**为什么评估体系拆成 5 个独立维度？**
金融分析报告的质量不是单一分数能衡量的。财务数值错了（准确率）和论据没逻辑（辩论质量）是两类问题，分开打分才能定位 Agent 短板，也便于针对性优化。阈值分档（0.5/0.6）是基于实际跑出来的分布设定的。

## 状态

开发中。已完成：

- 9 个 Agent 全部实现
- LangGraph 流水线跑通
- 三层记忆架构
- 完整可观测性
- FastAPI 服务 11 个 REST 接口 + WebSocket 实时推送
- 真实市场数据层（A 股 AKShare + 美股/港股 yfinance，自动路由）
- 五维度 Agent 评估体系 + 前端评估中心页面
- 端到端 pipeline 集成评估（报告生成后自动跑五维度评估，结果存入 state）
- Docker 一键部署（多阶段构建 + docker-compose，前后端同源 + Redis）
- 138 个后端测试 + 16 个前端组件测试全通过
- 端到端回归 100% 成功

## License

MIT

## 前端 Dashboard

提供 Web 界面提交分析任务、查看结果与可观测性数据。

**技术栈**：React + TypeScript + Vite，代码位于 `frontend/`。

**首次使用**：

```bash
# 1. 装依赖（只首次需要）
cd frontend && npm install

# 2. 启动后端（前端依赖后端在跑）
cd .. && python -m uvicorn src.main:app --host 127.0.0.1 --port 8000

# 3. 启动前端
cd frontend && npm run dev
```

**访问地址**：http://localhost:5173/（端口被占会自动切换，看终端输出）。

**功能**：

- 提交分析任务（股票代码 / 行业）
- 实时推送任务状态（WebSocket 主路径 + 轮询降级，pending → running → completed/failed/rejected）
- 渲染 Markdown 分析报告（含 GFM 表格）
- trace Mermaid 时序图（源码 + mermaid.live 外链，零依赖）
- trace 事件时间线（按事件顺序展开/折叠查看 content）
- 可观测性看板（独立视图：今日任务数 / 成功失败 / 平均 tokens / 总成本 + 全局概览 Markdown 报告）
- **评估中心**（独立视图：五维度 Agent 评估 — 汇总卡片 + 标的评分表 + 每只股票 5 维度详情，颜色按得分阈值分级）
- 对比模式（双任务独立提交 + AI 对比总结）
- 历史记录侧边栏（点击加载、悬停删除、相对时间）
- 网络错误自动重试（5xx/断网退避重试，4xx 不重试）

**网络**：前端通过 `vite.config.ts` 的 `/api` 代理转发到 `http://127.0.0.1:8000`，无需配置 CORS。
