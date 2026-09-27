# Multi-Agent Financial Analyst

一句话：输入股票代码或行业名称，自动收集财报、新闻、研报、市场数据，多 Agent 辩论分析，输出带风险提示和引用来源的投资研究报告。

## 核心特性

- **9 个专业 Agent 协作**：合规预检、任务规划、财报分析、新闻分析、研报分析、数据验证、多空辩论、风控、报告撰写+合规审查
- **多空辩论机制**：多头研究员 vs 空头研究员，主持人裁决，减少单一视角偏见
- **并行数据收集**：财务、新闻、研报三路并行，LangGraph Send fan-out
- **交叉验证**：三源信号对比，自动发现矛盾
- **全链路可追溯**：每个结论都有引用来源
- **合规审查**：规则层（禁止词/风险提示/引用）+ LLM 层双重审查，不合格打回
- **四层防注入**：规则过滤 + 标签隔离 + 输出检查 + LLM 验证
- **三级权限**：guest / user / admin，危险工具需二次确认
- **审计日志**：所有操作记录到 SQLite
- **Docker 沙箱**：代码执行禁网、限内存、限 CPU、只读文件系统
- **限流 + 成本熔断**：每用户每分钟/每日上限
- **FastAPI 服务**：异步流水线，5 个接口

## 架构

详见 [docs/architecture.md](docs/architecture.md)

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/你的用户名/multi-agent-financial-analyst.git
cd multi-agent-financial-analyst

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 4. 启动服务
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

打开 http://127.0.0.1:8000/docs 查看 API 文档。

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

其他接口：

- `GET /health` — 健康检查
- `GET /metrics` — 今日任务统计
- `GET /cost` — 今日成本统计

## 流水线

```text
用户输入
  → 合规预检（安全+权限+限流+成本）
  → 任务规划（识别公司类型+拆子任务）
  → 并行数据收集（财报 + 新闻 + 研报）
  → 数据验证（交叉验证+矛盾检测）
  → 多空辩论（多头 vs 空头，3 轮 + 主持人裁决）
  → 风控（风险识别+定级+合规提示）
  → 报告撰写（结构化+引用来源）
  → 合规审查（规则+LLM 双重）
  → 输出报告
```

## 技术栈

- Python 3.11
- LangGraph（多 Agent 编排）
- FastAPI（服务层）
- SQLite（状态持久化）
- Docker（沙箱）
- DeepSeek API（LLM）
- sentence-transformers（本地嵌入）

## 测试

```bash
pytest tests/ -v
# 107 passed
```

## 实际运行

一次完整流水线（AAPL）：

- 耗时：约 1-2 分钟
- Token：约 30000
- 成本：约 0.03 元
- 输出：带引用和风险提示的投资研究报告

## 项目结构

```text
multi-agent-financial-analyst/
├── src/
│   ├── state.py              # FinanceState 定义
│   ├── config.py             # 配置管理
│   ├── db.py                 # SQLite 持久化
│   ├── graph.py              # LangGraph 编排
│   ├── main.py               # FastAPI 服务
│   ├── agents/               # 9 个 Agent
│   ├── tools/                # 6 个工具 + 注册表
│   ├── safety/               # 防注入+权限+审计+沙箱
│   └── memory/               # （规划中）
├── tests/                    # 107 个测试
├── eval/                     # （规划中）
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

## 状态

开发中。已完成：

- 9 个 Agent 全部实现
- LangGraph 流水线跑通
- FastAPI 服务 5 个接口
- 107 个测试全通过

规划中：

- 三层记忆（工作+情景+语义）
- 成本控制（模型路由+缓存+历史压缩）
- 可观测性（Trace + Dashboard）
- Docker 部署
- ChromaDB 语义检索

## License

MIT
