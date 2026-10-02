import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel

from src.config import settings
from src.db import Database
from src.graph import run_pipeline
from src.agents.compare_summarizer import summarize
from src.agents.precheck import _check_rate_limit, _check_daily_limit

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
# 生产环境静态前端服务（Docker 部署用）
# ========================================

# 前端构建产物目录（多阶段 Docker 构建会把 frontend/dist 复制到这里）
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")


class StripApiPrefixMiddleware(BaseHTTPMiddleware):
    """
    剥离 /api 前缀中间件

    前端代码统一用 /api/xxx 调用后端，开发环境由 vite proxy 转发；
    生产环境（Docker）前后端同源，此中间件把 /api/analyze 重写为 /analyze。
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/"):
            # 重写路径（保留 query string）
            new_path = request.url.path[4:]  # 去掉 "/api"
            request.scope["path"] = new_path
            request.scope["raw_path"] = new_path.encode()
        response = await call_next(request)
        return response


app.add_middleware(StripApiPrefixMiddleware)


def _mount_frontend() -> None:
    """挂载前端静态文件（仅当 dist 目录存在时，即生产环境）"""
    if os.path.isdir(FRONTEND_DIST):
        # 静态资源（js/css/图片等）
        assets_dir = os.path.join(FRONTEND_DIST, "assets")
        if os.path.isdir(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
        logger.info(f"[main] 已挂载前端静态资源：{FRONTEND_DIST}")
    else:
        logger.info(f"[main] 前端 dist 不存在，跳过静态挂载（开发模式）：{FRONTEND_DIST}")


_mount_frontend()


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


class CompareRequest(BaseModel):
    """对比请求"""
    task_id_a: str
    task_id_b: str


class CompareResponse(BaseModel):
    """对比响应"""
    summary: str
    tokens: int
    cost: float


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

        # 把最终结果写回数据库（含进度字段，供前端进度条显示）
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
            current_step=result.get("current_step", 0),
            total_steps=result.get("total_steps", 0),
        )
        logger.info(f"[main] 任务完成：{task_id}，status={result.get('status')}")

    except Exception as e:
        logger.error(f"[main] 任务失败：{task_id}，{e}")
        try:
            db.mark_failed(task_id, str(e))
        except Exception as inner:
            logger.error(f"[main] 标记失败也失败：{inner}")


# ========================================
# 辅助函数
# ========================================

def _events_to_mermaid(events: list) -> str:
    """从事件列表生成 Mermaid 时序图"""
    if not events:
        return "sequenceDiagram\n    Note over system: 无事件"

    agents = sorted(set(e["agent"] for e in events if e["agent"] != "system"))
    lines = ["sequenceDiagram", "    participant system"]
    for a in agents:
        lines.append(f"    participant {a}")

    for e in events:
        agent = e["agent"]
        action = e["action"]
        content = (e.get("content") or "").replace('"', "'")[:50]
        duration = e.get("duration")
        tokens = e.get("tokens", 0)

        if agent == "system":
            continue
        if action == "start":
            lines.append(f"    system->>{agent}: start")
        elif action == "end":
            lines.append(f"    {agent}-->>system: end ({duration}s)")
        elif action == "llm_call":
            lines.append(f"    Note over {agent}: LLM {tokens}tok")
        elif action == "error":
            lines.append(f"    Note over {agent}: ERROR {content}")

    return "\n".join(lines)


def _summarize_events(events: list) -> dict:
    """从事件列表汇总统计"""
    if not events:
        return {"total_events": 0, "total_tokens": 0, "total_cost": 0.0, "total_duration": 0.0}
    return {
        "total_events": len(events),
        "agents": sorted(set(e["agent"] for e in events)),
        "total_tokens": sum(e.get("tokens", 0) or 0 for e in events),
        "total_cost": round(sum(e.get("cost", 0.0) or 0.0 for e in events), 6),
        "total_duration": round(sum(e.get("duration", 0.0) or 0.0 for e in events), 3),
    }


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

    # 限流前置检查（每分钟 + 每日请求上限），拒绝在创建任务之前
    ok, err = _check_rate_limit(request.user_id)
    if not ok:
        raise HTTPException(status_code=429, detail=err)
    ok, err = _check_daily_limit(request.user_id)
    if not ok:
        raise HTTPException(status_code=429, detail=err)

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


@app.post("/compare", response_model=CompareResponse)
def compare(req: CompareRequest):
    """把两个任务的报告交给 LLM，返回对比总结。"""
    try:
        result = summarize(req.task_id_a, req.task_id_b)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return CompareResponse(**result)


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


@app.websocket("/ws/{task_id}")
async def ws_task(websocket: WebSocket, task_id: str):
    """
    WebSocket 实时推送任务状态/进度

    客户端连接后，后端轮询 DB（1s）并在状态/步骤变化时推送，
    任务进入终态（completed/failed/rejected）后关闭连接。
    替代前端 2s 轮询，降低延迟与无效请求。

    Args:
        websocket: WebSocket 连接
        task_id: 任务 ID
    """
    await websocket.accept()
    last_key: Optional[tuple] = None
    try:
        while True:
            task = db.get_task(task_id)
            if task:
                key = (task.get("status"), task.get("current_step"), task.get("total_steps"))
                if key != last_key:
                    await websocket.send_json({"task": task})
                    last_key = key
                    if task.get("status") in ("completed", "failed", "rejected"):
                        break
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@app.get("/tasks")
def list_tasks(limit: int = 50, offset: int = 0):
    """返回最近的任务列表（用于历史记录）。"""
    # 上限保护，避免一次拉太多
    if limit > 200:
        limit = 200
    if limit < 0:
        limit = 0
    if offset < 0:
        offset = 0
    tasks = db.list_tasks(limit=limit, offset=offset)
    return {"tasks": tasks, "count": len(tasks)}


@app.delete("/tasks/{task_id}")
def delete_task(task_id: str):
    """删除指定任务（历史记录）。"""
    ok = db.delete_task(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"ok": True, "task_id": task_id}


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
    成本统计（从 tasks 表汇总今日所有任务）

    注意：返回字段同时保留 llm_calls（旧字段，等于 tasks 数）以兼容旧调用方。

    Returns:
        今日总 token、总成本、任务数、平均每任务成本
    """
    cursor = db.conn.execute("""
        SELECT
            SUM(total_tokens) as total_tokens,
            SUM(total_cost) as total_cost,
            COUNT(*) as tasks
        FROM tasks
        WHERE created_at > datetime('now', '-1 day')
    """)
    row = cursor.fetchone()
    total_tasks = row["tasks"] or 0
    total_cost = row["total_cost"] or 0
    return {
        "total_tokens": row["total_tokens"] or 0,
        "total_cost": round(total_cost, 6),
        "tasks": total_tasks,
        "avg_cost_per_task": round(total_cost / total_tasks, 6) if total_tasks > 0 else 0,
        # 兼容旧字段（语义变为"有成本记录的任务数"）
        "llm_calls": total_tasks,
    }


@app.get("/trace/{task_id}")
def get_trace(task_id: str):
    """
    查询任务的追踪信息

    Args:
        task_id: 任务 ID

    Returns:
        {events, mermaid, summary}
    """
    from src.observability.tracer import Tracer

    tracer = Tracer(db=db)
    events = tracer.get_trace_from_db(task_id)
    if not events:
        raise HTTPException(status_code=404, detail="无追踪记录")

    mermaid = _events_to_mermaid(events)
    summary = _summarize_events(events)

    return {
        "task_id": task_id,
        "events": events,
        "mermaid": mermaid,
        "summary": summary,
    }


@app.get("/overview")
def overview():
    """
    全局可观测性概览

    Returns:
        Markdown 格式报告
    """
    from src.observability.metrics import Metrics
    from src.observability.dashboard import overview_report

    m = Metrics(db)
    return {"report": overview_report(m)}


# ========================================
# 评估接口
# ========================================

class EvaluateRequest(BaseModel):
    """评估请求"""
    tickers: list[str] = []


@app.post("/evaluate")
def evaluate(req: EvaluateRequest):
    """
    运行 Agent 评估（五维度）

    Args:
        tickers: 股票代码列表，为空时使用默认 8 只蓝筹股

    Returns:
        评估结果（Markdown 报告 + 结构化数据）
    """
    from src.evaluation import evaluate_batch, generate_markdown_report, DEFAULT_TICKERS

    # Web 端默认只跑 3 只（各市场一只），避免请求超时；完整 8 只走 CLI
    WEB_DEFAULT_TICKERS = ["600519", "AAPL", "00700.HK"]
    tickers = req.tickers if req.tickers else WEB_DEFAULT_TICKERS
    try:
        evaluations = evaluate_batch(tickers)
        report = generate_markdown_report(evaluations)
        # 结构化数据（供前端渲染）
        results = []
        for se in evaluations:
            results.append({
                "symbol": se.symbol,
                "market": se.market,
                "overall_score": round(se.overall_score, 4),
                "all_passed": se.all_passed,
                "dimensions": [
                    {
                        "name": r.name,
                        "score": r.score,
                        "passed": r.passed,
                        "message": r.message,
                        "details": r.details,
                    }
                    for r in se.results
                ],
            })
        return {"report": report, "results": results}
    except Exception as e:
        logger.error(f"[main] 评估失败：{e}")
        raise HTTPException(status_code=500, detail=f"评估失败：{e}")


# ========================================
# SPA 回退（必须放在所有路由之后）
# ========================================

@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    """
    SPA 回退路由：非 API 路径返回 index.html（支持前端路由刷新）

    仅在前端 dist 存在时生效；开发模式下由 vite 处理。
    必须放在所有具体路由之后，否则会拦截 API 请求。
    """
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Not Found")


# ========================================
# 启动
# ========================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
