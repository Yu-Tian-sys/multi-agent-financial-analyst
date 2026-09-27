import logging
from src.state import FinanceState
from src.db import Database
from src.memory.working import compress_messages
from src.memory.episodic import EpisodicMemory

logger = logging.getLogger(__name__)


def recall_node(state: FinanceState, db: Database) -> dict:
    """
    召回节点：在流水线开始时召回情景记忆 + 压缩工作记忆

    Args:
        state: 当前状态
        db: Database 实例

    Returns:
        要更新的字段
    """
    user_id = state["user_id"]
    topic = state["topic"]

    # 1. 召回情景记忆
    em = EpisodicMemory(db)
    memory_text = em.recall(user_id, query=topic, top_k=10)

    # 2. 压缩工作记忆
    existing_messages = state.get("messages", [])
    compressed = compress_messages(existing_messages, keep_recent=6)

    # 3. 组装：记忆摘要 + 压缩后的消息
    new_messages = []
    if memory_text:
        new_messages.append({
            "role": "system",
            "content": f"【历史记忆】\n{memory_text}"
        })
        logger.info(f"[memory] 召回记忆：{len(memory_text)} 字")

    return {
        "messages": new_messages + compressed,
    }


def save_node(state: FinanceState, db: Database) -> dict:
    """
    保存节点：在流水线结束时抽取并保存情景记忆

    Args:
        state: 当前状态
        db: Database 实例

    Returns:
        要更新的字段
    """
    user_id = state["user_id"]

    # 抽取事实
    em = EpisodicMemory(db)
    facts = em.extract_facts(dict(state))

    if facts:
        em.save(user_id, facts)
        logger.info(f"[memory] 保存 {len(facts)} 条事实")
        return {
            "messages": [{
                "role": "system",
                "content": f"记忆已保存：{len(facts)} 条事实"
            }]
        }

    return {"messages": [{"role": "system", "content": "无可保存的记忆"}]}


def build_semantic_context(
    state: FinanceState,
    db: Database,
    query: str,
    top_k: int = 3,
) -> str:
    """
    构建语义记忆上下文（用于 RAG）

    Args:
        state: 当前状态
        db: Database 实例（保留参数，未来用于持久化）
        query: 查询文本
        top_k: 返回条数

    Returns:
        格式化的文本，无结果时返回空字符串
    """
    from src.memory.semantic import SemanticMemory

    try:
        sm = SemanticMemory()
        results = sm.search(state["user_id"], query, top_k=top_k)
        if not results:
            return ""
        lines = [f"- [{r['doc_id']}] {r['text']}" for r in results]
        return "相关资料：\n" + "\n".join(lines)
    except Exception as e:
        logger.warning(f"[memory] 语义检索失败：{e}")
        return ""
