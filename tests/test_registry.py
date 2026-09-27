import pytest
from src.tools.registry import list_tools, get_tools_schema, get_tool, call_tool


def test_list_tools():
    """测试列出所有工具"""
    tools = list_tools()
    assert len(tools) == 10
    assert "search_news" in tools
    assert "calculate" in tools


def test_get_tools_schema():
    """测试 schema 格式"""
    schema = get_tools_schema()
    assert len(schema) == 10
    for item in schema:
        assert item["type"] == "function"
        assert "name" in item["function"]
        assert "description" in item["function"]
        assert "parameters" in item["function"]


def test_get_tool():
    """测试获取工具函数"""
    func = get_tool("calculate")
    assert callable(func)
    assert get_tool("not_exist") is None


def test_call_tool():
    """测试调用工具"""
    result = call_tool("calculate", {"expression": "1+1"})
    assert result == "2"


def test_call_tool_not_exist():
    """测试调用不存在的工具"""
    result = call_tool("not_exist", {})
    assert "不存在" in result


def test_call_tool_error():
    """测试工具执行异常"""
    result = call_tool("calculate", {"wrong_param": "1+1"})
    assert "失败" in result or "无法计算" in result
