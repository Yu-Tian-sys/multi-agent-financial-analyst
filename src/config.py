import logging
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

logger = logging.getLogger(__name__)

# 加载 .env 文件（override=True 确保 .env 优先级高于系统环境变量，避免误用其他项目的同名 key）
load_dotenv(override=True)

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

    # 运行环境
    env: str = "development"                                      # development / production
    
    # 限制
    max_steps: int = 20                                           # Agent 最大步数
    timeout_seconds: int = 600                                    # 任务超时时间（秒）
    daily_cost_limit: float = 10.0                                # 每用户每日成本上限（元）
    rate_limit_per_minute: int = 5                               # 每用户每分钟请求上限
    rate_limit_per_day: int = 50                                 # 每用户每日请求上限

    # 模型路由
    model_cheap: str = "deepseek-chat"                            # 便宜层模型（分类/规划/辩论/合规）
    model_expensive: str = "deepseek-reasoner"                    # 昂贵层模型（报告撰写/主持人裁决）
    llm_mock: bool = False                                        # mock 模式开关（True 时不调真实 API）

    # 端到端评估
    enable_evaluation: bool = True                                # 流水线完成后自动运行五维度评估

    # 认证（可选）：设置后需在请求头携带 X-API-Key 才能调用写接口
    api_key: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False

# 全局配置实例
settings = Settings()

# 启动检查
if not settings.deepseek_api_key:
    logger.warning("DEEPSEEK_API_KEY 未设置，请在 .env 文件中配置。")

if settings.env == "production":
    if settings.llm_mock:
        logger.warning("生产环境不建议启用 LLM_MOCK，将返回假数据。")
    if not settings.deepseek_api_key:
        logger.error("生产环境未设置 DEEPSEEK_API_KEY，LLM 调用将失败。")
