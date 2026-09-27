import os
import logging
import uuid
from typing import List, Optional

logger = logging.getLogger(__name__)

OUTPUT_DIR = "./output"


def generate_chart(data: List[float], chart_type: str = "line",
                   title: str = "", xlabel: str = "", ylabel: str = "") -> str:
    """
    生成图表并保存到 output/ 目录

    Args:
        data: 数据列表
        chart_type: 图表类型：line / bar / pie
        title: 标题
        xlabel: X 轴标签
        ylabel: Y 轴标签

    Returns:
        图片文件路径，失败返回空字符串
    """
    try:
        import matplotlib
        matplotlib.use("Agg")  # 无 GUI 后端
        import matplotlib.pyplot as plt

        # 确保中文字体
        plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False

        # 确保输出目录存在
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # 创建图表
        fig, ax = plt.subplots(figsize=(10, 6))

        if chart_type == "line":
            ax.plot(data, marker="o")
        elif chart_type == "bar":
            ax.bar(range(len(data)), data)
        elif chart_type == "pie":
            ax.pie(data, autopct="%1.1f%%")
        else:
            return ""

        if chart_type != "pie":
            ax.set_title(title)
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            ax.grid(True, alpha=0.3)

        # 保存
        filename = f"chart_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(OUTPUT_DIR, filename)
        plt.tight_layout()
        plt.savefig(filepath, dpi=100)
        plt.close(fig)

        logger.info(f"图表已保存：{filepath}")
        return filepath

    except ImportError:
        logger.error("未安装 matplotlib")
        return ""
    except Exception as e:
        logger.error(f"生成图表失败：{e}")
        return ""
