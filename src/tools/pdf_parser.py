import os
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def parse_pdf(file_path: str) -> Tuple[bool, str]:
    """解析 PDF 文件，提取纯文本"""
    if not os.path.exists(file_path):
        return False, f"文件不存在：{file_path}"
    if not file_path.lower().endswith(".pdf"):
        return False, f"不是 PDF 文件：{file_path}"
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
        text = "\n".join(text_parts).strip()
        if not text:
            return False, "PDF 解析成功，但未提取到文本（可能是扫描件，需要 OCR）"
        logger.info(f"解析 PDF 成功：{file_path}，{len(text)} 字符")
        return True, text
    except ImportError:
        return False, "未安装 pypdf，请运行 pip install pypdf"
    except Exception as e:
        logger.error(f"解析 PDF 失败：{e}")
        return False, f"解析 PDF 失败：{e}"


def extract_financial_metrics(text: str) -> dict:
    """从文本中提取财务指标（简化版，用正则匹配）"""
    import re
    metrics = {}
    patterns = {
        "revenue": [
            r"(营业收入|营收|revenue)[：:\s]*([0-9,，.]+)\s*(亿|万|million|billion)?",
            r"(total\s+revenue)[：:\s]*([0-9,，.]+)",
        ],
        "profit": [
            r"(净利润|净利|profit)[：:\s]*([0-9,，.-]+)\s*(亿|万|million|billion)?",
            r"(net\s+income)[：:\s]*([0-9,，.-]+)",
        ],
        "debt": [
            r"(负债|负债总额|debt)[：:\s]*([0-9,，.]+)\s*(亿|万|million|billion)?",
            r"(total\s+debt)[：:\s]*([0-9,，.]+)",
        ],
        "roe": [
            r"(净资产收益率|ROE)[：:\s]*([0-9,，.-]+)\s*%?",
        ],
        "gross_margin": [
            r"(毛利率|gross\s+margin)[：:\s]*([0-9,，.-]+)\s*%?",
        ],
    }
    for key, pats in patterns.items():
        for pat in pats:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                if len(match.groups()) >= 2:
                    value = match.group(2)
                    unit = match.group(3) if len(match.groups()) >= 3 else ""
                    metrics[key] = f"{value}{unit}"
                break
    return metrics
