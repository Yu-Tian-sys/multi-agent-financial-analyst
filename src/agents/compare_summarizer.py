import logging
import time
from typing import Dict, Tuple

from openai import OpenAI

from src.config import settings
from src.db import Database
from src.observability.tracer import Tracer

logger = logging.getLogger(__name__)

# 模块级 LLM 客户端单例（和 report_writer 一致，import 时创建一次）
_client = OpenAI(
    api_key=settings.deepseek_api_key,
    base_url=settings.deepseek_base_url,
)

# 模块级数据库实例（和 main.py 一样用 settings.db_path；SQLite WAL 支持并发读）
_db = Database(settings.db_path)

# 模块级 Tracer 单例，把对比总结的 LLM 调用记进 traces 表（供 /metrics /trace 查询）
_tracer = Tracer(db=_db)

# 单份报告截断长度，防止 prompt 过大
MAX_REPORT_CHARS = 8000


def _call_llm(prompt: str, max_retries: int = 2) -> Tuple[str, int, float]:
    """调用 LLM 生成对比总结，带重试。

    Args:
        prompt: 拼好的 prompt
        max_retries: 最大重试次数

    Returns:
        (content, tokens, cost) 三元组；cost = tokens / 1_000_000 * 1.0
    """
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = _client.chat.completions.create(
                model=settings.model_cheap,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
            )
            content = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0
            cost = tokens / 1_000_000 * 1.0
            return content, tokens, cost
        except Exception as e:
            last_error = e
            logger.warning(f"[compare] LLM 调用失败（第 {attempt+1} 次）：{e}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
    raise last_error


def summarize(task_id_a: str, task_id_b: str) -> Dict[str, object]:
    """取两个任务的 final_report，拼成 prompt 让 LLM 输出对比总结。

    Args:
        task_id_a: 任务 A 的 ID
        task_id_b: 任务 B 的 ID

    Returns:
        {"summary": str, "tokens": int, "cost": float}

    Raises:
        ValueError: 任一任务不存在，或没有 final_report
    """
    task_a = _db.get_task(task_id_a)
    task_b = _db.get_task(task_id_b)

    if not task_a:
        raise ValueError(f"任务 A 不存在：{task_id_a}")
    if not task_b:
        raise ValueError(f"任务 B 不存在：{task_id_b}")

    report_a = task_a.get("final_report", "") or ""
    report_b = task_b.get("final_report", "") or ""

    if not report_a.strip():
        raise ValueError(f"任务 A 还没有报告：{task_id_a}")
    if not report_b.strip():
        raise ValueError(f"任务 B 还没有报告：{task_id_b}")

    # 截断，防止 prompt 过大
    if len(report_a) > MAX_REPORT_CHARS:
        report_a = report_a[:MAX_REPORT_CHARS]
    if len(report_b) > MAX_REPORT_CHARS:
        report_b = report_b[:MAX_REPORT_CHARS]

    topic_a = task_a.get("topic", "标的 A")
    topic_b = task_b.get("topic", "标的 B")

    prompt = f"""你是一位资深投资分析师。下面是两份股票分析报告，请给出对比总结。

报告 A（{topic_a}）：
{report_a}

=====

报告 B（{topic_b}）：
{report_b}

=====

请用中文输出一段 150-250 字的对比总结，包含：
1. 两只标的在风险等级上的差异
2. 成长性 / 盈利能力的差异
3. 投资立场（进取 / 稳健 / 中性）的差异
4. 一句话结论：什么样的投资者适合哪一只
用朴实的语言，不要用「综上所述」这种套话，直接说要点。"""

    logger.info(f"[compare] 开始生成对比总结：{topic_a} vs {topic_b}")
    content, tokens, cost = _call_llm(prompt)
    logger.info(f"[compare] 对比总结完成：tokens={tokens}, cost={cost}")

    # 记进可观测性系统：traces 表（供 /metrics /trace 查询）+ cost_log 表（供 /cost 统计）
    compare_id = f"{task_id_a}+{task_id_b}"
    _tracer.log_event(
        trace_id=compare_id,
        agent="compare_summarizer",
        action="llm_call",
        content="对比总结",
        tokens=tokens,
        cost=cost,
        task_id=compare_id,
    )
    _db.log_cost(compare_id, settings.model_cheap, tokens, cost)

    return {"summary": content, "tokens": tokens, "cost": cost}
