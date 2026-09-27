# 贡献指南

感谢你对本项目的兴趣！

## 开发环境

```bash
git clone https://github.com/Yu-Tian-sys/multi-agent-financial-analyst.git
cd multi-agent-financial-analyst
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
```

## 运行测试

```bash
# 全部测试（跳过 e2e）
pytest tests/ -v

# 含慢测试
pytest tests/ -v -m ""

# 端到端（需要真实 API）
pytest tests/ -v -m e2e
```

## 代码风格

- Python 3.11
- 类型注解必须有
- 函数必须有 docstring（中文）
- 所有外部调用必须有 try/except
- 所有 LLM 调用必须能 mock

## 提交 PR

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交：`git commit -m "feat: 你的功能"`
4. 推送：`git push origin feature/your-feature`
5. 创建 Pull Request

## Commit 规范

- `feat:` 新功能
- `fix:` 修 bug
- `docs:` 文档
- `test:` 测试
- `chore:` 杂项
- `refactor:` 重构

## 报告 Bug

请提供：

- 复现步骤
- 期望行为
- 实际行为
- 环境信息（Python 版本、操作系统）
