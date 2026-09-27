import os
import tempfile
import subprocess
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


# ========================================
# 沙箱配置
# ========================================

# Docker 镜像（轻量 Python）
DOCKER_IMAGE = "python:3.11-slim"

# 最大执行时间（秒）
MAX_EXECUTION_TIME = 30

# 最大内存（MB）
MAX_MEMORY_MB = 256

# 最大 CPU 核数
MAX_CPUS = 0.5

# 是否禁用网络
DISABLE_NETWORK = True

# 是否只读文件系统
READ_ONLY_FS = True


# ========================================
# 沙箱执行
# ========================================

def execute_code(code: str, timeout: int = MAX_EXECUTION_TIME) -> Tuple[bool, str]:
    """
    在 Docker 沙箱中执行 Python 代码

    安全限制：
    - 禁网（--network=none）
    - 限内存（--memory）
    - 限 CPU（--cpus）
    - 只读文件系统（--read-only）
    - 超时强制终止

    Args:
        code: 要执行的 Python 代码
        timeout: 超时时间（秒）

    Returns:
        (是否成功, 输出或错误信息)
    """
    # 1. 检查 Docker 是否可用
    if not _check_docker():
        return False, "Docker 不可用，无法执行代码"

    # 2. 构建 docker run 命令
    cmd = [
        "docker", "run", "--rm",
        f"--memory={MAX_MEMORY_MB}m",
        f"--cpus={MAX_CPUS}",
        "--read-only",
        "--tmpfs", "/tmp:size=10m",
    ]

    if DISABLE_NETWORK:
        cmd.append("--network=none")

    cmd.extend([
        DOCKER_IMAGE,
        "python", "-c", code
    ])

    # 3. 执行
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        output = result.stdout or result.stderr
        success = result.returncode == 0
        if not success:
            logger.warning(f"沙箱执行失败：{output[:200]}")
        return success, output

    except subprocess.TimeoutExpired:
        logger.warning(f"沙箱执行超时（{timeout}秒）")
        return False, f"执行超时（>{timeout}秒），已强制终止"

    except FileNotFoundError:
        return False, "未找到 docker 命令，请先安装 Docker"

    except Exception as e:
        logger.error(f"沙箱执行异常：{e}")
        return False, f"沙箱执行异常：{e}"


def _check_docker() -> bool:
    """
    检查 Docker 是否可用

    Returns:
        是否可用
    """
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# ========================================
# 测试用
# ========================================
if __name__ == "__main__":
    # 正常代码
    print(execute_code("print('hello')"))
    # (True, 'hello\n')

    # 超时
    print(execute_code("import time; time.sleep(60)", timeout=3))
    # (False, '执行超时...')

    # 尝试联网（应该失败）
    print(execute_code("import urllib.request; print(urllib.request.urlopen('http://baidu.com').read()[:50])"))
    # (False, '...') 禁网
