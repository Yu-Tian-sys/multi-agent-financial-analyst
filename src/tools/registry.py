import logging
from typing import Dict, Callable, List

from src.tools.pdf_parser import parse_pdf, extract_financial_metrics
from src.tools.news_search import search_news, analyze_sentiment
from src.tools.report_search import search_reports
from src.tools.market_data import get_stock_price, get_valuation
from src.tools.calculator import calculate, calculate_ratio
from src.tools.chart import generate_chart

logger = logging.getLogger(__name__)


# ========================================
# 工具注册表
# ========================================
# 结构：{工具名: {"func": 可调用函数, "description": 说明, "parameters": JSON Schema}}
TOOL_REGISTRY: Dict[str, dict] = {
    "parse_pdf": {
        "func": parse_pdf,
        "description": "解析 PDF 文件，提取纯文本。当需要读取财报、研报等 PDF 文件时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "PDF 文件路径"}
            },
            "required": ["file_path"]
        }
    },
    "extract_financial_metrics": {
        "func": extract_financial_metrics,
        "description": "从财报文本中提取财务指标（营收、净利润、负债、ROE、毛利率）。",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "财报文本"}
            },
            "required": ["text"]
        }
    },
    "search_news": {
        "func": search_news,
        "description": "搜索指定股票的近期新闻。当需要了解市场情绪、突发事件时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "股票代码或关键词，如 AAPL"},
                "limit": {"type": "integer", "description": "返回条数，默认 10", "default": 10}
            },
            "required": ["query"]
        }
    },
    "analyze_sentiment": {
        "func": analyze_sentiment,
        "description": "分析文本情感倾向（positive / negative / neutral）。",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "要分析的文本"}
            },
            "required": ["text"]
        }
    },
    "search_reports": {
        "func": search_reports,
        "description": "检索券商研报。当需要获取专业机构观点时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "limit": {"type": "integer", "description": "返回条数，默认 5", "default": 5}
            },
            "required": ["query"]
        }
    },
    "get_stock_price": {
        "func": get_stock_price,
        "description": "获取股票当前价格、涨跌、成交量。",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "股票代码，如 AAPL"},
                "days": {"type": "integer", "description": "历史天数，默认 30", "default": 30}
            },
            "required": ["symbol"]
        }
    },
    "get_valuation": {
        "func": get_valuation,
        "description": "获取股票估值指标（PE、PB、PS）。",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "股票代码，如 AAPL"}
            },
            "required": ["symbol"]
        }
    },
    "calculate": {
        "func": calculate,
        "description": "计算数学表达式，如 '123 * 456'。不要用于财务比率。",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "数学表达式"}
            },
            "required": ["expression"]
        }
    },
    "calculate_ratio": {
        "func": calculate_ratio,
        "description": "计算财务比率（gross_margin / net_margin / roe / roa / debt_ratio）。",
        "parameters": {
            "type": "object",
            "properties": {
                "metrics": {"type": "object", "description": "财务指标字典，如 {revenue, profit, equity}"},
                "ratio_type": {"type": "string", "description": "比率类型"}
            },
            "required": ["metrics", "ratio_type"]
        }
    },
    "generate_chart": {
        "func": generate_chart,
        "description": "生成图表（line / bar / pie），保存到 output/ 目录。",
        "parameters": {
            "type": "object",
            "properties": {
                "data": {"type": "array", "items": {"type": "number"}, "description": "数据列表"},
                "chart_type": {"type": "string", "description": "line / bar / pie"},
                "title": {"type": "string", "description": "图表标题"}
            },
            "required": ["data", "chart_type"]
        }
    },
}


def get_tool(name: str) -> Callable:
    """
    根据工具名获取可调用函数

    Args:
        name: 工具名

    Returns:
        可调用函数，不存在返回 None
    """
    entry = TOOL_REGISTRY.get(name)
    return entry["func"] if entry else None


def list_tools() -> List[str]:
    """
    列出所有工具名

    Returns:
        工具名列表
    """
    return list(TOOL_REGISTRY.keys())


def get_tools_schema() -> List[dict]:
    """
    返回 OpenAI Function Calling 格式的工具列表

    Returns:
        [{"type": "function", "function": {...}}, ...]
    """
    schema = []
    for name, entry in TOOL_REGISTRY.items():
        schema.append({
            "type": "function",
            "function": {
                "name": name,
                "description": entry["description"],
                "parameters": entry["parameters"]
            }
        })
    return schema


def call_tool(name: str, arguments: dict):
    """
    调用工具

    Args:
        name: 工具名
        arguments: 参数字典

    Returns:
        工具结果，或错误信息
    """
    func = get_tool(name)
    if func is None:
        return f"工具 {name} 不存在"
    try:
        return func(**arguments)
    except Exception as e:
        logger.error(f"工具 {name} 执行失败：{e}")
        return f"工具 {name} 执行失败：{e}"


# ========================================
# 测试用
# ========================================
if __name__ == "__main__":
    print("工具数:", len(list_tools()))
    print("工具列表:", list_tools())
    schema = get_tools_schema()
    print("schema 数:", len(schema))
    print("第一个 schema:", schema[0]["function"]["name"])
    print("调用 calculate:", call_tool("calculate", {"expression": "1+1"}))
    print("调用不存在的工具:", call_tool("not_exist", {}))
