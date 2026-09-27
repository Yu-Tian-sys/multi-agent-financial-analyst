import os
import pytest
import tempfile
import shutil
from src.db import Database
from src.state import create_initial_state
from src.memory.working import compress_messages, estimate_tokens
from src.memory.episodic import EpisodicMemory
from src.memory.integration import recall_node, save_node


@pytest.fixture
def db():
    """临时数据库"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database = Database(path)
    yield database
    database.close()
    if os.path.exists(path):
        os.remove(path)


# ========================================
# working 测试
# ========================================

def test_estimate_tokens():
    """测试 token 估算"""
    assert estimate_tokens("") == 0
    assert estimate_tokens("hello") > 0
    assert estimate_tokens("你好世界") > 0


def test_compress_messages_no_compress():
    """测试消息少时不压缩"""
    msgs = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    result = compress_messages(msgs, keep_recent=6)
    assert len(result) == 2


def test_compress_messages_compress():
    """测试消息多时压缩"""
    msgs = [{"role": "system", "content": "你是助手"}]
    for i in range(20):
        msgs.append({"role": "user", "content": f"用户消息{i}"})
        msgs.append({"role": "assistant", "content": f"助手回复{i}"})

    result = compress_messages(msgs, keep_recent=6)
    # 1 system + 1 摘要 system + 6 recent = 8
    assert len(result) == 8
    assert result[0]["role"] == "system"
    assert result[1]["role"] == "system"
    assert "历史摘要" in result[1]["content"]


# ========================================
# episodic 测试
# ========================================

def test_extract_facts():
    """测试事实抽取"""
    em = EpisodicMemory.__new__(EpisodicMemory)  # 不调 __init__
    task = {
        "topic": "AAPL",
        "company_type": "科技",
        "risk_assessment": {"risk_level": "中"},
        "debate_records": [{"side": "judge", "content": '{"stance": "看多", "confidence": 0.75}'}],
    }
    facts = em.extract_facts(task)
    assert len(facts) == 4
    keys = [f["key"] for f in facts]
    assert "分析过_AAPL" in keys


def test_episodic_save_and_recall(db):
    """测试情景记忆保存和召回"""
    em = EpisodicMemory(db)
    task = {
        "topic": "AAPL",
        "company_type": "科技",
        "risk_assessment": {"risk_level": "中"},
        "debate_records": [],
    }
    facts = em.extract_facts(task)
    em.save("u1", facts)

    text = em.recall("u1")
    assert "AAPL" in text

    d = em.recall_as_dict("u1")
    assert len(d) >= 2


def test_episodic_isolation(db):
    """测试用户隔离"""
    em = EpisodicMemory(db)
    em.save("u1", [{"key": "k1", "value": "u1的"}])
    em.save("u2", [{"key": "k2", "value": "u2的"}])

    u1_mem = em.recall("u1")
    assert "u1的" in u1_mem
    assert "u2的" not in u1_mem


# ========================================
# semantic 测试
# ========================================

@pytest.mark.slow
def test_semantic_basic():
    """测试语义记忆基础功能"""
    from src.memory.semantic import SemanticMemory

    tmp = tempfile.mkdtemp()
    try:
        sm = SemanticMemory(persist_dir=tmp)
        sm.add_document("u1", "doc1", "苹果公司营收 3832 亿美元，净利润 970 亿，毛利率 46%。")
        sm.add_document("u1", "doc2", "特斯拉营收 967 亿美元，净利润 150 亿。")
        sm.add_document("u2", "doc3", "另一个用户的文档内容，不应该被 u1 检索到。")

        results = sm.search("u1", "苹果毛利率", top_k=2)
        assert len(results) == 2
        assert results[0]["doc_id"] == "doc1"

        # 隔离
        results2 = sm.search("u2", "苹果", top_k=5)
        assert len(results2) == 1
        assert results2[0]["doc_id"] == "doc3"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.slow
def test_semantic_delete():
    """测试删除文档"""
    from src.memory.semantic import SemanticMemory

    tmp = tempfile.mkdtemp()
    try:
        sm = SemanticMemory(persist_dir=tmp)
        sm.add_document("u1", "doc1", "测试文档内容，这是一段足够长的文本用于检索。")
        sm.delete_document("u1", "doc1")
        results = sm.search("u1", "测试", top_k=5)
        assert len(results) == 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ========================================
# integration 测试
# ========================================

def test_recall_node_empty(db):
    """测试召回节点（无历史记忆）"""
    state = create_initial_state("t1", "u1", "user", "AAPL")
    result = recall_node(state, db)
    assert "messages" in result


def test_save_node(db):
    """测试保存节点"""
    state = create_initial_state("t1", "u1", "user", "AAPL")
    state["company_type"] = "科技"
    state["risk_assessment"] = {"risk_level": "中"}
    result = save_node(state, db)
    assert "messages" in result
    # 验证写入了
    em = EpisodicMemory(db)
    mems = em.recall_as_dict("u1")
    assert len(mems) >= 1
