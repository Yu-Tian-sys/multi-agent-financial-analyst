import logging
from typing import List, Dict

from src.db import Database

logger = logging.getLogger(__name__)


class EpisodicMemory:
    """情景记忆：记住用户的关键事实，跨会话保留"""

    def __init__(self, db: Database):
        """
        初始化

        Args:
            db: Database 实例
        """
        self.db = db

    def extract_facts(self, task_result: dict) -> List[Dict[str, str]]:
        """
        从任务结果中抽取值得记住的事实

        Args:
            task_result: 任务最终状态（dict）

        Returns:
            [{"key": "...", "value": "..."}, ...]
        """
        facts = []

        # 1. 分析过的标的
        topic = task_result.get("topic")
        if topic:
            facts.append({
                "key": f"分析过_{topic}",
                "value": f"用户分析过 {topic}"
            })

        # 2. 公司类型偏好
        company_type = task_result.get("company_type")
        if company_type:
            facts.append({
                "key": f"偏好类型_{company_type}",
                "value": f"用户关注 {company_type} 类型公司"
            })

        # 3. 历史风险等级
        ra = task_result.get("risk_assessment", {})
        risk_level = ra.get("risk_level")
        if risk_level:
            facts.append({
                "key": f"风险等级_{topic}",
                "value": f"{topic} 风险等级 {risk_level}"
            })

        # 4. 辩论结论
        debate_records = task_result.get("debate_records", [])
        judge = next((r for r in debate_records if r.get("side") == "judge"), None)
        if judge:
            import json
            try:
                verdict = json.loads(judge.get("content", "{}"))
                stance = verdict.get("stance")
                confidence = verdict.get("confidence")
                if stance:
                    facts.append({
                        "key": f"辩论结论_{topic}",
                        "value": f"{topic} 辩论裁决：{stance}（置信度 {confidence}）"
                    })
            except (json.JSONDecodeError, TypeError):
                pass

        logger.info(f"[episodic] 抽取 {len(facts)} 条事实")
        return facts

    def save(self, user_id: str, facts: List[Dict[str, str]]) -> None:
        """
        保存事实到 memories 表

        Args:
            user_id: 用户 ID
            facts: 事实列表
        """
        for fact in facts:
            self.db.save_memory(user_id, fact["key"], fact["value"])
        logger.info(f"[episodic] 保存 {len(facts)} 条事实（user={user_id}）")

    def recall(self, user_id: str, query: str = "", top_k: int = 10) -> str:
        """
        召回情景记忆（文本格式）

        Args:
            user_id: 用户 ID
            query: 查询关键词（空则返回全部）
            top_k: 最多返回条数

        Returns:
            格式化文本，用于塞进 system prompt
        """
        all_memories = self.db.get_memories(user_id)
        if not all_memories:
            return ""

        # 关键词筛选
        if query:
            keywords = [w for w in query.replace(",", " ").split() if len(w) > 1]
            filtered = [
                m for m in all_memories
                if any(kw in m["value"] or kw in m["key"] for kw in keywords)
            ]
            # 筛选为空则返回全部（避免召回为空）
            memories = filtered if filtered else all_memories
        else:
            memories = all_memories

        memories = memories[:top_k]

        lines = [f"- {m['value']}" for m in memories]
        return "关于该用户的历史信息：\n" + "\n".join(lines)

    def recall_as_dict(self, user_id: str) -> Dict[str, str]:
        """
        召回情景记忆（字典格式）

        Args:
            user_id: 用户 ID

        Returns:
            {key: value}
        """
        all_memories = self.db.get_memories(user_id)
        return {m["key"]: m["value"] for m in all_memories}


# ========================================
# 测试用
# ========================================
if __name__ == "__main__":
    import tempfile, os
    from src.db import Database

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(path)

    em = EpisodicMemory(db)

    # 模拟任务结果
    task_result = {
        "topic": "AAPL",
        "company_type": "科技",
        "risk_assessment": {"risk_level": "中"},
        "debate_records": [
            {"side": "judge", "content": '{"stance": "看多", "confidence": 0.75}'}
        ],
    }

    # 抽取 + 保存
    facts = em.extract_facts(task_result)
    print(f"抽取 {len(facts)} 条事实：")
    for f in facts:
        print(f"  {f['key']} = {f['value']}")

    em.save("u1", facts)

    # 召回
    print("\n召回全部：")
    print(em.recall("u1"))

    print("\n召回关键词 AAPL：")
    print(em.recall("u1", query="AAPL"))

    print("\n字典格式：")
    print(em.recall_as_dict("u1"))

    db.close()
    os.remove(path)
