# Multi-Agent Financial Analyst

一句话：输入股票代码或行业名称，自动收集财报、新闻、研报、市场数据，多 Agent 辩论分析，输出带风险提示和引用来源的投资研究报告。

## 核心特性

- 9 个专业 Agent 协作：合规预检、任务规划、财报分析、新闻分析、研报分析、市场数据、数据验证、多空辩论、风控合规
- 多空辩论机制：减少单一视角偏见
- 全链路可追溯：每个结论都有引用来源
- 合规审查：自动识别投资建议，强制加风险提示
- 三层记忆：工作记忆 + 情景记忆 + 语义记忆
- 五层失败恢复：重试、熔断、降级、断点续跑、兜底
- 成本控制：模型路由 + 缓存 + 历史压缩
- 安全边界：四层防注入 + 三级权限 + 审计日志 + Docker 沙箱

## 架构

详见 [docs/architecture.md](docs/architecture.md)

## 快速开始

```bash
git clone https://github.com/你的用户名/multi-agent-financial-analyst.git
cd multi-agent-financial-analyst
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
```

## 技术栈

- Python 3.11
- LangGraph
- FastAPI
- SQLite + ChromaDB + Redis
- DeepSeek API
- Docker

## 项目结构

```text
multi-agent-financial-analyst/
├── src/
│   ├── state.py          # 状态定义
│   ├── config.py         # 配置管理
│   ├── db.py             # 数据库
│   ├── graph.py          # LangGraph 编排
│   ├── main.py           # FastAPI 入口
│   ├── agents/           # 9 个 Agent
│   ├── tools/            # 工具集
│   ├── safety/           # 安全层
│   └── memory/           # 记忆层
├── tests/                # 测试
├── eval/                 # 评估
├── docs/                 # 文档
├── data/                 # 数据
└── output/               # 输出
```

## 状态

开发中。第 1 天完成：项目初始化 + 状态定义 + 架构文档。
