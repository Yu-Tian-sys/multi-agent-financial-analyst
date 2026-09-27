import logging
from typing import Optional
from src.db import Database

logger = logging.getLogger(__name__)


class AuditLogger:
    """审计日志记录器，封装 Database 的审计方法"""

    def __init__(self, db: Database):
        """
        初始化审计记录器

        Args:
            db: Database 实例
        """
        self.db = db

    def log(self, user_id: str, role: str, action: str,
            detail: str = "", status: str = "success") -> None:
        """
        记录审计日志

        Args:
            user_id: 用户 ID
            role: 用户角色
            action: 操作名（如 query_stock / execute_code / send_email）
            detail: 详细信息
            status: 状态（success / denied / failed）
        """
        self.db.log_audit(user_id, role, action, detail, status)
        logger.info(f"[审计] {user_id} ({role}) {action} - {status}")

    def log_denied(self, user_id: str, role: str, action: str, detail: str = "") -> None:
        """记录被拒绝的操作"""
        self.log(user_id, role, action, detail, status="denied")

    def log_failed(self, user_id: str, role: str, action: str, detail: str = "") -> None:
        """记录失败的操作"""
        self.log(user_id, role, action, detail, status="failed")

    def query(self, user_id: str, limit: int = 50) -> list:
        """
        查询某用户的审计记录

        Args:
            user_id: 用户 ID
            limit: 返回条数上限

        Returns:
            审计记录列表
        """
        return self.db.get_audit_log(user_id, limit)

    def summary(self, user_id: str) -> dict:
        """
        统计某用户的操作摘要

        Args:
            user_id: 用户 ID

        Returns:
            {total, success, denied, failed}
        """
        logs = self.db.get_audit_log(user_id, limit=1000)
        result = {"total": len(logs), "success": 0, "denied": 0, "failed": 0}
        for log in logs:
            status = log.get("status", "")
            if status in result:
                result[status] += 1
        return result
