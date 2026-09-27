import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel

from src.config import settings
from src.db import Database
from src.graph import run_pipeline

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


# ========================================
# 全局资源
# ========================================
db: Database = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时建库，关闭时释放"""
    global db
    db = Database(settings.db_path)
    logger.info(f"[main] 数据库初始化完成：{settings.db_path}")
    yield
    db.close()
    logger.info("[main] 数据库连接已关闭")


app = FastAPI(
    title="Multi-Agent Financial Analyst",
    description="多 Agent 金融分析平台",
    version="0.1.0",
    lifespan=lifespan,
)


# ========================================
# 请求/响应模型
# ========================================

class AnalyzeRequest(BaseModel):
    """分析请求"""
    topic: str                       # 股票代码或行业
    user_id: str = "anonymous"       # 用户 ID
    user_role: str = "user"          # 角色：guest/user/admin


class AnalyzeResponse(BaseModel):
    """分析响应"""
    task_id: str
    status: str
    message: str


# ========================================
# 后台任务
# ========================================

def _run_pipeline_task(task_id: str, user_id: str, user_role: str, topic: str) -> None:
    """
    后台执行流水线

    Args:
        task_id: 任务 ID
        user_id: 用户 ID
        user_role: 用户角色
        topic: 股票代码或行业
    """
    logger.info(f"[main] 开始执行任务：{task_id}")
    try:
        db.update_task(task_id, status="running")
        result = run_pipeline(task_id, user_id, user_role, topic)

        # 把最终结果写回数据库
        db.update_task(
            task_id,
            status=result.get("status", "failed"),
            final_report=result.get("final_report", ""),
            draft_report=result.get("draft_report", ""),
            risk_assessment=result.get("risk_assessment", {}),
            compliance_result=result.get("compliance_result", {}),
            total_tokens=result.get("total_tokens", 0),
            total_cost=result.get("total_cost", 0.0),
            error=result.get("error", ""),
        )
        logger.info(f"[main] 任务完成：{task_id}，status={result.get('status')}")

    except Exception as e:
        logger.error(f"[main] 任务失败：{task_id}，{e}")
        try:
            db.mark_failed(task_id, str(e))
        except Exception as inner:
            logger.error(f"[main] 标记失败也失败：{inner}")


# ========================================
# 接口
# ========================================

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    提交分析任务（异步）

    立即返回 task_id，实际执行在后台。

    Args:
        request: 分析请求
        background_tasks: FastAPI 后台任务

    Returns:
        {task_id, status, message}
    """
    # 简单校验
    if not request.topic or not request.topic.strip():
        raise HTTPException(status_code=400, detail="topic 不能为空")

    task_id = str(uuid.uuid4())
    db.create_task(task_id, request.user_id, request.user_role, request.topic)
    background_tasks.add_task(
        _run_pipeline_task,
        task_id, request.user_id, request.user_role, request.topic
    )

    logger.info(f"[main] 任务已提交：{task_id} / {request.topic}")

    return AnalyzeResponse(
        task_id=task_id,
        status="pending",
        message="任务已提交，请通过 GET /task/{task_id} 查询进度"
    )


@app.get("/task/{task_id}")
def get_task(task_id: str):
    """
    查询任务状态

    Args:
        task_id: 任务 ID

    Returns:
        任务完整状态
    """
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@app.get("/health")
def health():
    """健康检查"""
    return {"status": "ok", "version": "0.1.0"}


@app.get("/metrics")
def metrics():
    """
    统计信息

    Returns:
        今日任务数、成功数、失败数、平均 tokens
    """
    cursor = db.conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
            AVG(total_tokens) as avg_tokens,
            SUM(total_cost) as total_cost
        FROM tasks
        WHERE created_at > datetime('now', '-1 day')
    """)
    row = cursor.fetchone()
    return {
        "total_tasks": row["total"] or 0,
        "completed": row["completed"] or 0,
        "failed": row["failed"] or 0,
        "avg_tokens": round(row["avg_tokens"] or 0, 2),
        "total_cost": round(row["total_cost"] or 0, 6),
    }


@app.get("/cost")
def cost():
    """
    成本统计

    Returns:
        今日总 token 和总成本
    """
    cursor = db.conn.execute("""
        SELECT
            SUM(tokens) as total_tokens,
            SUM(cost) as total_cost,
            COUNT(*) as calls
        FROM cost_log
        WHERE created_at > datetime('now', '-1 day')
    """)
    row = cursor.fetchone()
    return {
        "total_tokens": row["total_tokens"] or 0,
        "total_cost": round(row["total_cost"] or 0, 6),
        "llm_calls": row["calls"] or 0,
    }


# ========================================
# 启动
# ========================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
