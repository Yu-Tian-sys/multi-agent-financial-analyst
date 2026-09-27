import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    """
    粗略估算文本的 token 数

    规则：中文 1 token / 2 字符，英文 1 token / 4 字符

    Args:
        text: 文本

    Returns:
        估算的 token 数
    """
    if not text:
        return 0

    chinese = 0
    other = 0
    for c in text:
        if '\u4e00' <= c <= '\u9fff':
            chinese += 1
        else:
            other += 1

    return chinese // 2 + other // 4 + 1


def _summarize_old_messages(old_messages: List[Dict], max_chars: int = 500) -> str:
    """
    把旧消息压缩成摘要（不调 LLM，用简单截断规则）

    Args:
        old_messages: 要压缩的消息列表
        max_chars: 摘要最大长度

    Returns:
        摘要文本
    """
    if not old_messages:
        return ""

    parts = []
    for m in old_messages:
        role = m.get("role", "unknown")
        content = m.get("content", "") or ""
        if role == "user":
            snippet = content[:50]
            parts.append(f"用户：{snippet}")
        elif role == "assistant":
            snippet = content[:80]
            parts.append(f"助手：{snippet}")
        # system 消息不压缩（本来就是元信息）

    summary = " | ".join(parts)

    # 超长则截断
    if len(summary) > max_chars:
        summary = summary[:max_chars] + "..."

    return f"[历史摘要] {summary}"


def compress_messages(
    messages: List[Dict],
    keep_recent: int = 6,
    max_summary_chars: int = 500,
) -> List[Dict]:
    """
    压缩消息列表：保留最近 N 条 + 把更早的压缩成摘要

    Args:
        messages: 完整消息列表
        keep_recent: 保留最近多少条原始消息
        max_summary_chars: 摘要最大长度

    Returns:
        压缩后的消息列表
    """
    if not messages:
        return []

    # 分离 system 消息和普通消息
    system_msgs = [m for m in messages if m.get("role") == "system"]
    normal_msgs = [m for m in messages if m.get("role") != "system"]

    # 消息不多，不压缩
    if len(normal_msgs) <= keep_recent:
        return messages

    # 分离：老的压缩，新的保留
    old = normal_msgs[:-keep_recent]
    recent = normal_msgs[-keep_recent:]

    # 压缩老的
    summary = _summarize_old_messages(old, max_summary_chars)

    # 组装：system + 摘要（作为 system）+ 最近消息
    result = list(system_msgs)
    if summary:
        result.append({"role": "system", "content": summary})
    result.extend(recent)

    # 日志
    original_tokens = sum(estimate_tokens(m.get("content", "")) for m in messages)
    compressed_tokens = sum(estimate_tokens(m.get("content", "")) for m in result)
    logger.info(
        f"[working] 压缩：{len(messages)} 条 → {len(result)} 条，"
        f"tokens 约 {original_tokens} → {compressed_tokens}"
    )

    return result


def get_working_context(messages: List[Dict], keep_recent: int = 6) -> List[Dict]:
    """
    获取工作记忆上下文（compress_messages 的封装）

    Args:
        messages: 完整消息列表
        keep_recent: 保留最近多少条

    Returns:
        压缩后的消息列表
    """
    return compress_messages(messages, keep_recent=keep_recent)


# ========================================
# 测试用
# ========================================
if __name__ == "__main__":
    # 模拟 20 轮对话
    msgs = [{"role": "system", "content": "你是助手"}]
    for i in range(20):
        msgs.append({"role": "user", "content": f"第 {i+1} 轮用户消息，这是一段比较长的内容用来测试压缩效果"})
        msgs.append({"role": "assistant", "content": f"第 {i+1} 轮助手回复，内容也是比较长的测试文本，用来验证 token 压缩"})

    print(f"原始消息数：{len(msgs)}")
    print(f"原始 tokens：{sum(estimate_tokens(m['content']) for m in msgs)}")

    compressed = compress_messages(msgs, keep_recent=6)
    print(f"压缩后消息数：{len(compressed)}")
    print(f"压缩后 tokens：{sum(estimate_tokens(m['content']) for m in compressed)}")
    print()
    print("压缩后结构：")
    for m in compressed:
        content = m.get("content", "")
        print(f"  [{m['role']}] {content[:60]}...")
