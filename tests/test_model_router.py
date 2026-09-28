import pytest
from unittest.mock import MagicMock, patch

from src.optimization import model_router
from src.optimization.model_router import (
    get_model_name,
    is_mock,
    call_llm,
)


def test_get_model_name_cheap(monkeypatch):
    """测试 cheap 层返回正确模型名"""
    monkeypatch.setattr(model_router.settings, "model_cheap", "test-cheap-model")
    assert get_model_name("cheap") == "test-cheap-model"


def test_get_model_name_expensive(monkeypatch):
    """测试 expensive 层返回正确模型名"""
    monkeypatch.setattr(model_router.settings, "model_expensive", "test-expensive-model")
    assert get_model_name("expensive") == "test-expensive-model"


def test_get_model_name_invalid():
    """测试未知层级抛异常"""
    with pytest.raises(ValueError):
        get_model_name("unknown")


def test_is_mock(monkeypatch):
    """测试 mock 模式开关"""
    monkeypatch.setattr(model_router.settings, "llm_mock", True)
    assert is_mock() is True
    monkeypatch.setattr(model_router.settings, "llm_mock", False)
    assert is_mock() is False


def test_call_llm_mock_mode(monkeypatch):
    """测试 mock 模式不调真实 API"""
    monkeypatch.setattr(model_router.settings, "llm_mock", True)
    content, tokens, cost = call_llm("test prompt", tier="cheap")
    assert "[mock-cheap]" in content
    assert tokens == 100
    assert cost == 0.0001


def test_call_llm_real_mode(monkeypatch):
    """测试真实模式（mock 掉 OpenAI 客户端）"""
    monkeypatch.setattr(model_router.settings, "llm_mock", False)

    # 构造假的 OpenAI 响应
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = "fake response"
    fake_response.usage.total_tokens = 500

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_response

    monkeypatch.setattr(model_router, "get_client", lambda tier: fake_client)
    monkeypatch.setattr(model_router, "get_model_name", lambda tier: "fake-model")

    content, tokens, cost = call_llm("test", tier="cheap")
    assert content == "fake response"
    assert tokens == 500
    assert cost == 0.0005


def test_call_llm_retry_success(monkeypatch):
    """测试重试后成功"""
    monkeypatch.setattr(model_router.settings, "llm_mock", False)

    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = "ok"
    fake_response.usage.total_tokens = 100

    call_count = [0]
    def fake_create(**kwargs):
        call_count[0] += 1
        if call_count[0] < 2:
            raise Exception("temporary error")
        return fake_response

    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = fake_create

    monkeypatch.setattr(model_router, "get_client", lambda tier: fake_client)
    monkeypatch.setattr(model_router, "get_model_name", lambda tier: "fake")

    content, _, _ = call_llm("test", tier="cheap", max_retries=2)
    assert content == "ok"
    assert call_count[0] == 2


def test_call_llm_expensive_fallback(monkeypatch):
    """测试 expensive 失败降级到 cheap"""
    monkeypatch.setattr(model_router.settings, "llm_mock", False)

    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = "fallback ok"
    fake_response.usage.total_tokens = 50

    call_count = {"expensive": 0, "cheap": 0}

    def fake_create(model, **kwargs):
        if model == "expensive-model":
            call_count["expensive"] += 1
            raise Exception("expensive down")
        call_count["cheap"] += 1
        return fake_response

    fake_client = MagicMock()
    fake_client.chat.completions.create.side_effect = fake_create

    monkeypatch.setattr(model_router, "get_client", lambda tier: fake_client)
    monkeypatch.setattr(
        model_router, "get_model_name",
        lambda tier: "expensive-model" if tier == "expensive" else "cheap-model"
    )

    content, _, _ = call_llm("test", tier="expensive", max_retries=0)
    assert content == "fallback ok"
    assert call_count["expensive"] == 1
    assert call_count["cheap"] >= 1
