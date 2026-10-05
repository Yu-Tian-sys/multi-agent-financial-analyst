import json
import pytest
from src.state import create_initial_state
import src.optimization.model_router as router_module


# ========================================
# debate 测试（mock LLM）
# ========================================

def test_debate_node_mock(monkeypatch):
    """测试多空辩论节点（mock LLM）"""
    bull_args = [
        "营收同比增长15%，净利润增长20%，盈利能力持续增强",
        "市场份额扩大至行业第二，新产品线贡献显著增量",
        "经营现金流充沛，连续三年超过净利润，财务健康度高",
    ]
    bear_args = [
        "估值处于历史高位，PE超过行业均值50%，下行风险大",
        "核心业务增速放缓，新业务尚未盈利，增长动力存疑",
        "行业竞争加剧，毛利率连续两个季度下滑",
    ]
    bull_idx = [0]
    bear_idx = [0]
    def mock_call_llm(prompt, tier="cheap", *, temperature=0.3, max_retries=2):
        # 先判断裁决（裁决 prompt 里也含"摘要"，必须优先）
        if "主持人" in prompt or "JUDGE" in prompt or "裁决" in prompt:
            verdict = json.dumps({
                "stance": "看多",
                "confidence": 0.75,
                "bull_points": ["增长强劲"],
                "bear_points": ["估值偏高"],
                "conclusion": "综合看多"
            }, ensure_ascii=False)
            return verdict, 100, 0.0001
        # 再判断多空（多空 prompt 里也含摘要内容）
        if "多头" in prompt or "乐观" in prompt:
            idx = bull_idx[0]
            bull_idx[0] += 1
            return bull_args[idx % len(bull_args)], 100, 0.0001
        if "空头" in prompt or "谨慎" in prompt:
            idx = bear_idx[0]
            bear_idx[0] += 1
            return bear_args[idx % len(bear_args)], 100, 0.0001
        # 最后才是摘要
        return "【摘要】测试用压缩摘要", 50, 0.00005

    monkeypatch.setattr(router_module, "call_llm", mock_call_llm)

    state = create_initial_state("t1", "u1", "user", "AAPL")
    state["financial_data"] = {"raw_metrics": {"profit": "970亿"}}
    state["news_data"] = [{"title": "增长", "sentiment": "positive"}]
    state["report_data"] = [{"title": "买入", "rating": "买入"}]

    from src.agents.debate import debate_node
    result = debate_node(state)

    assert result["status"] == "running"
    assert result["debate_rounds"] == 2
    # 2 轮 × 2 条 + 1 裁决 = 5 条
    assert len(result["debate_records"]) == 5
    assert result["debate_records"][0]["side"] == "bull"
    assert result["debate_records"][1]["side"] == "bear"
    assert result["debate_records"][-1]["side"] == "judge"


def test_debate_judge_json_fallback(monkeypatch):
    """测试裁决 JSON 解析失败降级"""
    def mock_call_llm(prompt, tier="cheap", *, temperature=0.3, max_retries=2):
        if "整理员" in prompt or "研究摘要" in prompt:
            return "【摘要】测试用压缩摘要", 50, 0.00005
        if "裁决" in prompt or "主持人" in prompt:
            return "这不是 JSON", 100, 0.0001
        return "发言内容", 100, 0.0001

    monkeypatch.setattr(router_module, "call_llm", mock_call_llm)

    state = create_initial_state("t1", "u1", "user", "AAPL")
    state["financial_data"] = {}
    state["news_data"] = []
    state["report_data"] = []

    from src.agents.debate import debate_node
    result = debate_node(state)

    assert result["status"] == "running"
    # 降级为中性
    judge_record = result["debate_records"][-1]
    verdict = json.loads(judge_record["content"])
    assert verdict["stance"] == "中性"


# ========================================
# risk 测试
# ========================================

def test_risk_node_high():
    """测试高风险场景"""
    from src.agents.risk import risk_node
    state = create_initial_state("t1", "u1", "user", "AAPL")
    state["financial_data"] = {
        "raw_metrics": {"profit": "970亿，同比下滑5%"},
        "ratios": {"net_margin": 0.03, "debt_ratio": 0.85},
    }
    state["news_data"] = [
        {"title": "面临反垄断调查", "sentiment": "negative"},
        {"title": "召回部分产品", "sentiment": "negative"},
    ]
    state["debate_records"] = [
        {"round": 4, "side": "judge", "content": '{"stance": "看空", "confidence": 0.7, "bear_points": ["竞争加剧"]}'}
    ]
    result = risk_node(state)
    assert result["status"] == "running"
    ra = result["risk_assessment"]
    assert ra["risk_level"] == "高"
    assert len(ra["risk_factors"]) >= 3
    assert "风险提示" in ra["risk_warning"]


def test_risk_node_low():
    """测试低风险场景"""
    from src.agents.risk import risk_node
    state = create_initial_state("t1", "u1", "user", "AAPL")
    state["financial_data"] = {
        "raw_metrics": {"profit": "970亿，同比增长5%"},
        "ratios": {"net_margin": 0.25},
    }
    state["news_data"] = [{"title": "销量超预期", "sentiment": "positive"}]
    state["debate_records"] = [
        {"round": 4, "side": "judge", "content": '{"stance": "看多", "confidence": 0.8, "bear_points": []}'}
    ]
    result = risk_node(state)
    ra = result["risk_assessment"]
    assert ra["risk_level"] in ["低", "中"]
    # 无论什么等级，风险提示必须有
    assert "风险提示" in ra["risk_warning"]


def test_risk_financial_detection():
    """测试财报风险识别"""
    from src.agents.risk import _check_financial_risk
    risks = _check_financial_risk({
        "raw_metrics": {"profit": "同比下滑10%"},
        "ratios": {"net_margin": 0.02, "debt_ratio": 0.8},
    })
    assert len(risks) >= 3


def test_risk_news_detection():
    """测试新闻风险识别"""
    from src.agents.risk import _check_news_risk
    risks = _check_news_risk([
        {"title": "面临诉讼", "sentiment": "negative"},
        {"title": "被罚款", "sentiment": "negative"},
    ])
    assert len(risks) >= 1


# ========================================
# report_writer 测试（mock LLM）
# ========================================

def test_report_writer_mock(monkeypatch):
    """测试报告撰写节点（mock LLM）"""
    def mock_call_llm(prompt, max_retries=2):
        return "# 测试报告\n\n## 财务分析\n营收增长。\n\n## 风险提示\n投资有风险。", 500, 0.0005

    import src.agents.report_writer as writer_module
    monkeypatch.setattr(writer_module, "_call_llm", mock_call_llm)

    state = create_initial_state("t1", "u1", "user", "AAPL")
    state["company_type"] = "科技"
    state["financial_data"] = {"source": "mock", "raw_metrics": {"revenue": "100亿"}, "ratios": {}}
    state["news_data"] = [{"title": "新闻", "source": "Reuters", "sentiment": "neutral"}]
    state["report_data"] = [{"title": "研报", "broker": "中金", "rating": "买入"}]
    state["debate_records"] = []
    state["risk_assessment"] = {"risk_level": "低", "risk_factors": []}

    from src.agents.report_writer import report_writer_node
    result = report_writer_node(state)

    assert result["status"] == "running"
    assert "测试报告" in result["draft_report"]
    assert len(result["report_references"]) >= 3


def test_build_references():
    """测试引用收集"""
    from src.agents.report_writer import _build_references
    state = create_initial_state("t1", "u1", "user", "AAPL")
    state["financial_data"] = {"source": "mock:AAPL", "raw_metrics": {"revenue": "100亿"}}
    state["news_data"] = [{"title": "新闻1", "source": "Reuters"}]
    state["report_data"] = [{"title": "研报1", "broker": "中金"}]
    refs = _build_references(state)
    # 财报1 + 新闻1 + 研报1 = 3
    assert len(refs) == 3


# ========================================
# compliance 测试（mock LLM）
# ========================================

def test_compliance_pass(monkeypatch):
    """测试合规通过（mock LLM 返回通过）"""
    def mock_llm_check(report):
        return {"passed": True, "issues": [], "suggestions": []}, 100, 0.0001

    import src.agents.compliance as comp_module
    monkeypatch.setattr(comp_module, "_llm_compliance_check", mock_llm_check)

    state = create_initial_state("t1", "u1", "user", "AAPL")
    state["draft_report"] = "# 报告\n## 风险提示\n投资有风险，入市需谨慎。"
    state["report_references"] = [{"source": "财报", "snippet": "..."}]

    from src.agents.compliance import compliance_node
    result = compliance_node(state)

    assert result["status"] == "completed"
    assert result["compliance_result"]["passed"] is True
    assert result["final_report"] == state["draft_report"]


def test_compliance_forbidden_keywords(monkeypatch):
    """测试禁止词拦截"""
    def mock_llm_check(report):
        return {"passed": True, "issues": [], "suggestions": []}, 100, 0.0001

    import src.agents.compliance as comp_module
    monkeypatch.setattr(comp_module, "_llm_compliance_check", mock_llm_check)

    state = create_initial_state("t1", "u1", "user", "AAPL")
    state["draft_report"] = "# 报告\n建议买入，必涨。"
    state["report_references"] = [{"source": "x", "snippet": "y"}]

    from src.agents.compliance import compliance_node
    result = compliance_node(state)

    assert result["compliance_result"]["passed"] is False
    assert any("禁止词" in issue for issue in result["compliance_result"]["issues"])


def test_compliance_missing_risk_warning(monkeypatch):
    """测试缺少风险提示被拦截"""
    def mock_llm_check(report):
        return {"passed": True, "issues": [], "suggestions": []}, 100, 0.0001

    import src.agents.compliance as comp_module
    monkeypatch.setattr(comp_module, "_llm_compliance_check", mock_llm_check)

    state = create_initial_state("t1", "u1", "user", "AAPL")
    state["draft_report"] = "# 报告\n营收增长。"
    state["report_references"] = [{"source": "x", "snippet": "y"}]

    from src.agents.compliance import compliance_node
    result = compliance_node(state)

    assert result["compliance_result"]["passed"] is False
    assert any("风险提示" in issue for issue in result["compliance_result"]["issues"])


def test_compliance_no_references(monkeypatch):
    """测试缺少引用被拦截"""
    def mock_llm_check(report):
        return {"passed": True, "issues": [], "suggestions": []}, 100, 0.0001

    import src.agents.compliance as comp_module
    monkeypatch.setattr(comp_module, "_llm_compliance_check", mock_llm_check)

    state = create_initial_state("t1", "u1", "user", "AAPL")
    state["draft_report"] = "# 报告\n## 风险提示\n投资有风险。"
    state["report_references"] = []

    from src.agents.compliance import compliance_node
    result = compliance_node(state)

    assert result["compliance_result"]["passed"] is False
    assert any("引用" in issue for issue in result["compliance_result"]["issues"])


def test_compliance_llm_rejects(monkeypatch):
    """测试 LLM 审查不通过"""
    def mock_llm_check(report):
        return {"passed": False, "issues": ["结论缺乏数据支撑"], "suggestions": ["补充数据"]}, 100, 0.0001

    import src.agents.compliance as comp_module
    monkeypatch.setattr(comp_module, "_llm_compliance_check", mock_llm_check)

    state = create_initial_state("t1", "u1", "user", "AAPL")
    state["draft_report"] = "# 报告\n## 风险提示\n投资有风险。"
    state["report_references"] = [{"source": "x", "snippet": "y"}]

    from src.agents.compliance import compliance_node
    result = compliance_node(state)

    assert result["compliance_result"]["passed"] is False
