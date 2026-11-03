import json
import logging
import time

from ..config import settings
from ..errors import ApiError

logger = logging.getLogger(__name__)


class LLMResult:
    def __init__(self, data, tokens_in=0, tokens_out=0, duration_s=0.0, request_id="-", retries=0):
        self.data = data
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.duration_s = duration_s
        self.request_id = request_id
        self.retries = retries


def call_json(prompt, system=None, temperature=0.3, config=None) -> LLMResult:
    """调用 OpenAI 兼容模型并要求 JSON 输出；超时/失败/非法 JSON 均重试，最多 max_retries 次。"""
    cfg = config or settings
    if not cfg.model_api_key:
        raise ApiError("MODEL_KEY_MISSING", "模型 Key 未配置，请在 backend/.env 填写 MODEL_API_KEY", 503)
    try:
        from openai import OpenAI
    except ImportError:
        raise ApiError("OPENAI_SDK_MISSING", "缺少 openai SDK，请先执行 pip install -r requirements.txt", 500)

    client = OpenAI(
        api_key=cfg.model_api_key,
        base_url=cfg.model_base_url,
        timeout=cfg.model_timeout,
        max_retries=0,  # 重试由本函数统一控制
    )
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    for attempt in range(max(1, cfg.model_max_retries)):
        t0 = time.time()
        try:
            resp = client.chat.completions.create(
                model=cfg.model_name,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=temperature,
            )
            duration = round(time.time() - t0, 2)
            usage = getattr(resp, "usage", None)
            tokens_in = getattr(usage, "prompt_tokens", 0) or 0
            tokens_out = getattr(usage, "completion_tokens", 0) or 0
            request_id = getattr(resp, "id", "-") or "-"
            content = resp.choices[0].message.content or ""
            data = json.loads(content)
            logger.info(
                "llm_call model=%s attempt=%d tokens_in=%s tokens_out=%s duration=%ss",
                cfg.model_name, attempt + 1, tokens_in, tokens_out, duration,
            )
            return LLMResult(data, tokens_in, tokens_out, duration, request_id, attempt)
        except Exception as e:  # noqa: 包括超时、SDK 初始化失败、JSON 解析失败
            logger.warning("llm_call attempt=%d failed=%s", attempt + 1, type(e).__name__)
            time.sleep(min(2 ** attempt, 8))
    raise ApiError("MODEL_CALL_FAILED", f"模型调用失败（重试 {cfg.model_max_retries} 次）", 502)
