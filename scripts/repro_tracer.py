import os, sys, tempfile, threading, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db import Database
from src.observability.tracer import Tracer

fd, path = tempfile.mkstemp(suffix=".db")
os.close(fd)
db = Database(path)
tracer = Tracer(db=db)

# 模拟多线程同时写（LangGraph 并行节点场景）
def worker(name):
    for i in range(20):
        tracer.log_event("tr1", name, "llm_call", f"test-{i}", tokens=10, cost=0.0001)
        time.sleep(0.001)

threads = [threading.Thread(target=worker, args=(f"agent{i}",)) for i in range(3)]
for th in threads: th.start()
for th in threads: th.join()

events = tracer.get_trace_from_db("tr1")
print(f"内存事件数：{len(tracer.get_trace('tr1'))}")
print(f"数据库事件数：{len(events)}")
print(f"是否一致：{len(tracer.get_trace('tr1')) == len(events)}")

db.close()
os.remove(path)
