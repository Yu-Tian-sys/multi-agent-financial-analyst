# 开源发布清单

发布到 GitHub 前，逐项确认。

## 安全检查

- [ ] 没有硬编码 API Key（`grep -r "sk-" src/ tests/` 无结果）
- [ ] `.env` 在 `.gitignore` 里
- [ ] `.env.example` 只有占位符
- [ ] `data/agent.db` 未提交
- [ ] `data/chroma/` 未提交
- [ ] `regression_report.json` 未提交
- [ ] `__pycache__/` 未提交

## 文档检查

- [ ] `README.md` 完整（含快速开始、API 使用、架构图）
- [ ] `LICENSE` 存在
- [ ] `CONTRIBUTING.md` 存在
- [ ] `docs/architecture.md` 完整
- [ ] `.env.example` 包含所有需要的环境变量

## 代码检查

- [ ] `pytest tests/ -v` 全部通过
- [ ] 所有 Python 文件有类型注解
- [ ] 所有公开函数有 docstring
- [ ] 没有 `print()` 调试语句（用 `logging`）

## CI 检查

- [ ] `.github/workflows/test.yml` 存在
- [ ] push 到 GitHub 后 CI 通过

## GitHub 仓库设置

- [ ] 仓库描述填写（一句话简介）
- [ ] Topics 填写（如 `ai-agent`、`langgraph`、`multi-agent`、`finance`）
- [ ] README 显示正常
- [ ] About 部分填写网站或文档链接

## 发布

- [ ] 打 tag：`git tag -a v0.1.0 -m "Initial release"`
- [ ] 推送 tag：`git push origin v0.1.0`
- [ ] 在 GitHub 创建 Release，附上 release notes

## 发布后

- [ ] 写技术博客（掘金/知乎/Medium）
- [ ] 发 X/微博
- [ ] 提交到 awesome-langchain、awesome-ai-agents 等列表
- [ ] 在 Hacker News / Reddit r/LocalLLaMA 分享
