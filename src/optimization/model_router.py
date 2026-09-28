import logging
from typing import Literal, Tuple, Dict

from openai import OpenAI

from src.config import settings

logger = logging.getLogger(__name__)

# 模型层级类型
ModelTier = Literal["cheap", "expensive"]

# 客户端单例缓存
_clients: Dict[str, OpenAI] = {}


def get_model_name(tier: ModelTier) -> str:
    """
    按层级返回模型名

    Args:
        tier: 层级（cheap / expensive）

    Returns:
        模型名
    """
    if tier == "cheap":
        return settings.model_cheap
    elif tier == "expensive":
        return settings.model_expensive
    raise ValueError(f"未知 tier: {tier}，只支持 cheap / expensive")


def get_client(tier: ModelTier) -> OpenAI:
    """
    按层级返回 OpenAI 客户端（单例缓存）

    Args:
        tier: 层级

    Returns:
        OpenAI 客户端
    """
    if tier not in _clients:
        _clients[tier] = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
    return _clients[tier]


def is_mock() -> bool:
    """
    是否启用 mock 模式

    Returns:
        True 表示 mock，不调真实 API
    """
    return settings.llm_mock


def _mock_call(prompt: str, tier: ModelTier) -> Tuple[str, int, float]:
    """
    mock 调用（不调真实 API）

    Args:
        prompt: 提示词
        tier: 层级

    Returns:
        (固定响应, 估算 token, 估算成本)
    """
    content = f"[mock-{tier}] {prompt[:50]}"
    return content, 100, 0.0001


def call_llm(
    prompt: str,
    tier: ModelTier = "cheap",
    *,
    temperature: float = 0.3,
    max_retries: int = 2,
) -> Tuple[str, int, float]:
    """
    统一 LLM 调用入口

    Args:
        prompt: 提示词
        tier: 层级（cheap / expensive）
        temperature: 温度
        max_retries: 最大重试次数

    Returns:
        (内容, tokens, 成本)

    降级策略：
    - expensive 失败 → 降级到 cheap
    - cheap 失败 → 抛异常
    """
    # mock 模式
    if is_mock():
        logger.info(f"[router] mock 模式，tier={tier}")
        return _mock_call(prompt, tier)

    model = get_model_name(tier)
    client = get_client(tier)

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            content = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0
            cost = tokens / 1_000_000 * 1.0
            logger.info(f"[router] {tier}({model}) 成功，{tokens} tokens")
            return content, tokens, cost
        except Exception as e:
            last_error = e
            logger.warning(f"[router] {tier} 调用失败（第 {attempt + 1} 次）：{e}")

    # 降级：expensive → cheap
    if tier == "expensive":
        logger.warning("[router] expensive 降级到 cheap")
        return call_llm(prompt, tier="cheap", temperature=temperature, max_retries=max_retries)

    raise last_error
