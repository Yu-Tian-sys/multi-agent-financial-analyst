# 基准测试数据

## AAPL 端到端（优化前 vs 优化后）

### 优化前（3 轮辩论，无总结）

单次运行：
- total_tokens: 26,688
- total_cost: 0.027 元
- debate_rounds: 3
- debate_records: 7

### 优化后（2 轮辩论 + 上下文总结）

4 次运行：

| 次数 | tokens | 成本 | 报告长度 | debate_rounds | debate_records |
|------|--------|------|----------|---------------|----------------|
| run1 | 14,291 | 0.0143 | 2,733 | 2 | 5 |
| run2 | 14,402 | 0.0144 | 2,008 | 2 | 5 |
| run3 | 13,869 | 0.0139 | 2,504 | 2 | 5 |
| run4 | 17,633 | — | 1,896 | 2 | 5 |
| **平均** | **15,049** | **0.015** | **2,285** | 2 | 5 |

**降幅**：43.6%（按平均 tokens）

## 三个标的端到端（优化前基准，供对比）

| 标的 | 状态 | 类型 | 风险 | tokens | 耗时 |
|------|------|------|------|--------|------|
| AAPL | completed | 科技 | 高 | 26,688 | 45.2s |
| TSLA | completed | 科技 | 高 | 29,274 | 48.3s |
| 招商银行 | completed | 银行 | 高 | 34,872 | 56.8s |

合计 90,834 tokens，成本约 0.09 元。

## 测试数据

- 全量测试：138 passed, 2 deselected
- 覆盖模块：db, safety, tools, registry, agents, validator, debate, risk, writer, compliance, api, memory, observability, model_router
