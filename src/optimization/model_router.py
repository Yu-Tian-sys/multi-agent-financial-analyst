import logging
import time
from typing import Literal, Tuple, Dict

from openai import OpenAI

from src.config import settings

logger = logging.getLogger(__name__)

# 模型层级类型
ModelTier = Literal["cheap", "expensive"]

# 客户端单例缓存
_clients: Dict[str, OpenAI] = {}

# 各模型单价（元/百万 token），用于成本核算
MODEL_PRICE_PER_MTOK: Dict[str, float] = {
    "deepseek-chat": 1.0,
    "deepseek-reasoner": 4.0,
}

# 请求超时（秒）
REQUEST_TIMEOUT = 60


def get_model_name(tier: ModelTier) -> str:
    if tier == "cheap":
        return settings.model_cheap
    elif tier == "expensive":
        return settings.model_expensive
    raise ValueError(f"未知 tier: {tier}，只支持 cheap / expensive")


def _calc_cost(model: str, tokens: int) -> float:
    """按模型单价计算成本（元）"""
    price = MODEL_PRICE_PER_MTOK.get(model, 1.0)
    return tokens / 1_000_000 * price


def get_client(tier: ModelTier) -> OpenAI:
    if tier not in _clients:
        _clients[tier] = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=REQUEST_TIMEOUT,
        )
    return _clients[tier]


def is_mock() -> bool:
    return settings.llm_mock


def _mock_call(prompt: str, tier: ModelTier) -> Tuple[str, int, float]:
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

    降级策略：
    - 429 限流：指数退避后重试
    - 超时/网络错误：重试
    - expensive 失败 → 降级到 cheap
    - cheap 失败 → 抛异常
    """
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
                timeout=REQUEST_TIMEOUT,
            )
            content = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0
            cost = _calc_cost(model, tokens)
            logger.info(f"[router] {tier}({model}) 成功，{tokens} tokens")
            return content, tokens, cost
        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            # 429 限流：指数退避（1s, 2s, 4s...）
            if "429" in err_str or "rate limit" in err_str:
                wait = 2 ** attempt
                logger.warning(f"[router] {tier} 限流，{wait}s 后重试（第 {attempt + 1} 次）")
                time.sleep(wait)
                continue
            # 超时/网络错误：短延迟重试
            logger.warning(f"[router] {tier} 调用失败（第 {attempt + 1} 次）：{e}")
            if attempt < max_retries:
                time.sleep(1.5 * (attempt + 1))

    # 降级：expensive → cheap
    if tier == "expensive":
        logger.warning("[router] expensive 降级到 cheap")
        return call_llm(prompt, tier="cheap", temperature=temperature, max_retries=max_retries)

    raise last_error
