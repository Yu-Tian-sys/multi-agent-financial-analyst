import logging
from src.state import FinanceState
from src.db import Database
from src.memory.working import compress_messages
from src.memory.episodic import EpisodicMemory

logger = logging.getLogger(__name__)

# 语义记忆懒加载单例（首次调用才加载 embedding 模型，避免每次节点都重新加载）
_semantic_memory = None


def _get_semantic_memory():
    """懒加载 SemanticMemory 单例（首次调用才加载 embedding 模型）。"""
    global _semantic_memory
    if _semantic_memory is None:
        from src.memory.semantic import SemanticMemory
        _semantic_memory = SemanticMemory()
    return _semantic_memory


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

    # 4. 语义记忆召回（ChromaDB 向量检索，失败不影响主流程）
    try:
        sem_ctx = build_semantic_context(state, db, query=topic, top_k=3)
        if sem_ctx:
            new_messages.append({
                "role": "system",
                "content": sem_ctx,
            })
            logger.info(f"[memory] 语义召回成功：{len(sem_ctx)} 字")
    except Exception as e:
        logger.warning(f"[memory] 语义召回失败：{e}")

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

    # 语义记忆写入：把 final_report 存进 ChromaDB（失败不影响主流程）
    try:
        final_report = state.get("final_report", "") or ""
        if final_report:
            topic = state.get("topic", "unknown")
            text = f"{topic}\n{final_report[:2000]}"
            task_id = state.get("task_id", "")
            sm = _get_semantic_memory()
            sm.add_document(
                user_id=user_id,
                doc_id=task_id or topic,
                text=text,
                metadata={"task_id": task_id, "topic": topic},
            )
            logger.info(f"[memory] 语义写入成功：{len(text)} 字")
    except Exception as e:
        logger.warning(f"[memory] 语义写入失败：{e}")

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
    try:
        sm = _get_semantic_memory()
        results = sm.search(state["user_id"], query, top_k=top_k)
        if not results:
            return ""
        lines = [f"- [{r['doc_id']}] {r['text']}" for r in results]
        return "相关资料：\n" + "\n".join(lines)
    except Exception as e:
        logger.warning(f"[memory] 语义检索失败：{e}")
        return ""
