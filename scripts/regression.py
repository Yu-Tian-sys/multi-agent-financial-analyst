"""
端到端回归测试脚本

运行：
    python scripts/regression.py

跑 3 个标的，每个约 1-2 分钟，总耗时 5-6 分钟。
消耗约 0.1 元 API 费用。
"""

import time
import json
from datetime import datetime

from src.db import Database
from src.graph import run_pipeline
from src.observability.tracer import Tracer
from src.observability.metrics import Metrics

TEST_TOPICS = [
    ("AAPL", "科技"),
    ("TSLA", "消费"),
    ("招商银行", "银行"),
]


def run_one(topic: str, expected_type: str) -> dict:
    """跑一个标的"""
    task_id = f"regression-{topic}-{int(time.time())}"
    user_id = "regression-user"

    print(f"\n{'='*60}")
    print(f"测试标的：{topic}（预期类型：{expected_type}）")
    print(f"task_id：{task_id}")
    print(f"{'='*60}")

    start = time.time()
    try:
        result = run_pipeline(task_id, user_id, "user", topic)
        elapsed = time.time() - start

        return {
            "topic": topic,
            "expected_type": expected_type,
            "task_id": task_id,
            "status": result.get("status"),
            "company_type": result.get("company_type"),
            "type_match": result.get("company_type") == expected_type,
            "debate_rounds": result.get("debate_rounds", 0),
            "risk_level": result.get("risk_assessment", {}).get("risk_level"),
            "compliance_passed": result.get("compliance_result", {}).get("passed"),
            "final_report_len": len(result.get("final_report", "") or result.get("draft_report", "")),
            "total_tokens": result.get("total_tokens", 0),
            "total_cost": result.get("total_cost", 0.0),
            "elapsed": round(elapsed, 1),
            "error": result.get("error", ""),
        }
    except Exception as e:
        return {
            "topic": topic,
            "status": "exception",
            "error": str(e),
            "elapsed": round(time.time() - start, 1),
        }


def main():
    """主流程"""
    print(f"端到端回归测试开始：{datetime.now().isoformat()}")
    print(f"共 {len(TEST_TOPICS)} 个标的\n")

    results = []
    for topic, expected in TEST_TOPICS:
        r = run_one(topic, expected)
        results.append(r)

        print(f"\n结果：")
        print(f"  status: {r.get('status')}")
        print(f"  company_type: {r.get('company_type')}")
        print(f"  type_match: {r.get('type_match')}")
        print(f"  debate_rounds: {r.get('debate_rounds')}")
        print(f"  risk_level: {r.get('risk_level')}")
        print(f"  compliance_passed: {r.get('compliance_passed')}")
        print(f"  report_len: {r.get('final_report_len')}")
        print(f"  tokens: {r.get('total_tokens')}")
        print(f"  cost: {r.get('total_cost')}")
        print(f"  elapsed: {r.get('elapsed')}s")
        if r.get("error"):
            print(f"  error: {r['error']}")

    print(f"\n{'='*60}")
    print("回归汇总")
    print(f"{'='*60}")

    total = len(results)
    completed = sum(1 for r in results if r.get("status") == "completed")
    type_matched = sum(1 for r in results if r.get("type_match"))
    total_tokens = sum(r.get("total_tokens", 0) for r in results)
    total_cost = sum(r.get("total_cost", 0.0) for r in results)

    summary = {
        "总标的数": total,
        "完成数": completed,
        "类型识别正确": type_matched,
        "总 tokens": total_tokens,
        "总成本": round(total_cost, 4),
        "成功率": f"{completed/total*100:.0f}%",
        "timestamp": datetime.now().isoformat(),
        "results": results,
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    with open("regression_report.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存：regression_report.json")


if __name__ == "__main__":
    main()
