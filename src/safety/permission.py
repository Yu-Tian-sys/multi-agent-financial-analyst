import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


# ========================================
# 三级权限定义
# ========================================

# 只读工具（所有角色可用）
READONLY_TOOLS = [
    "parse_pdf",
    "extract_financial_metrics",
    "search_news",
    "analyze_sentiment",
    "search_reports",
    "get_stock_price",
    "get_valuation",
    "calculate_ratio",
    "cross_validate",
    "query_database",
]

# 写入工具（user 和 admin 可用）
WRITE_TOOLS = READONLY_TOOLS + [
    "generate_chart",
    "save_report",
]

# 危险工具（只有 admin 可用，且需要二次确认）
DANGEROUS_TOOLS = WRITE_TOOLS + [
    "send_notification",
    "execute_code",
]

# 角色 → 可用工具映射
ROLE_TOOLS = {
    "guest": READONLY_TOOLS,
    "user": WRITE_TOOLS,
    "admin": DANGEROUS_TOOLS,
}

# 需要二次确认的工具
NEED_CONFIRM_TOOLS = [
    "send_notification",
    "execute_code",
]


# ========================================
# 权限检查函数
# ========================================

def check_permission(role: str, tool_name: str) -> Tuple[bool, Optional[str]]:
    """
    检查角色是否有权限调用工具

    Args:
        role: 用户角色（guest / user / admin）
        tool_name: 工具名

    Returns:
        (是否有权限, 错误信息)
    """
    # 角色校验
    if role not in ROLE_TOOLS:
        logger.warning(f"未知角色：{role}")
        return False, f"未知角色：{role}"

    # 工具校验
    allowed_tools = ROLE_TOOLS[role]
    if tool_name not in allowed_tools:
        logger.warning(f"权限不足：角色 {role} 无权调用 {tool_name}")
        return False, f"权限不足：{role} 角色无法调用 {tool_name}"

    return True, None


def need_confirmation(tool_name: str) -> bool:
    """
    检查工具是否需要二次确认

    Args:
        tool_name: 工具名

    Returns:
        是否需要二次确认
    """
    return tool_name in NEED_CONFIRM_TOOLS


def check_and_confirm(
    role: str,
    tool_name: str,
    confirmed: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    综合检查：权限 + 二次确认

    Args:
        role: 用户角色
        tool_name: 工具名
        confirmed: 用户是否已二次确认

    Returns:
        (是否通过, 错误信息)
    """
    # 1. 权限检查
    ok, err = check_permission(role, tool_name)
    if not ok:
        return False, err

    # 2. 二次确认检查
    if need_confirmation(tool_name) and not confirmed:
        return False, f"危险操作 {tool_name}，需要二次确认后才能执行"

    return True, None


def get_allowed_tools(role: str) -> list:
    """
    获取某角色可用的所有工具

    Args:
        role: 用户角色

    Returns:
        可用工具列表（如果角色未知，返回空列表）
    """
    return ROLE_TOOLS.get(role, [])


def is_dangerous(tool_name: str) -> bool:
    """
    判断工具是否危险

    Args:
        tool_name: 工具名

    Returns:
        是否危险
    """
    return tool_name in NEED_CONFIRM_TOOLS


# ========================================
# 测试用
# ========================================
if __name__ == "__main__":
    # guest 只能读
    print(check_permission("guest", "search_news"))      # (True, None)
    print(check_permission("guest", "save_report"))      # (False, '权限不足...')

    # user 能写
    print(check_permission("user", "save_report"))       # (True, None)
    print(check_permission("user", "execute_code"))      # (False, '权限不足...')

    # admin 能执行危险工具，但需要二次确认
    print(check_and_confirm("admin", "execute_code"))              # (False, '需要二次确认...')
    print(check_and_confirm("admin", "execute_code", confirmed=True))  # (True, None)
