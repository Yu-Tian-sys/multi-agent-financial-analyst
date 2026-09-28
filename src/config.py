import logging
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

logger = logging.getLogger(__name__)

# 加载 .env 文件
load_dotenv()

class Settings(BaseSettings):
    """全局配置"""
    
    # DeepSeek API
    deepseek_api_key: str = ""                                    # DeepSeek API Key
    deepseek_base_url: str = "https://api.deepseek.com"           # DeepSeek API 地址
    
    # Redis
    redis_url: str = "redis://localhost:6379"                     # Redis 连接地址
    
    # 数据库
    db_path: str = "./data/agent.db"                              # SQLite 数据库路径
    chroma_path: str = "./data/chroma"                            # ChromaDB 向量库路径
    
    # 日志
    log_level: str = "INFO"                                       # 日志级别
    
    # 限制
    max_steps: int = 20                                           # Agent 最大步数
    timeout_seconds: int = 600                                    # 任务超时时间（秒）
    daily_cost_limit: float = 10.0                                # 每用户每日成本上限（元）
    rate_limit_per_minute: int = 5                               # 每用户每分钟请求上限

    # 模型路由
    model_cheap: str = "deepseek-chat"                            # 便宜层模型（分类/规划/辩论/合规）
    model_expensive: str = "deepseek-reasoner"                    # 昂贵层模型（报告撰写/主持人裁决）
    llm_mock: bool = False                                        # mock 模式开关（True 时不调真实 API）

    class Config:
        env_file = ".env"
        case_sensitive = False

# 全局配置实例
settings = Settings()

# 启动检查
if not settings.deepseek_api_key:
    logger.warning("DEEPSEEK_API_KEY 未设置，请在 .env 文件中配置。")
