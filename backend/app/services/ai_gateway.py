from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from time import perf_counter
from typing import Any

import httpx

from app.core.config import settings


class AIProviderError(Exception):
    """Safe, provider-neutral error raised by the gateway."""


class AIProviderConfigurationError(AIProviderError):
    """Raised when a provider is not configured on the server."""


@dataclass(frozen=True)
class ProviderUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True)
class ProviderCompletion:
    content: str
    model: str
    usage: ProviderUsage


@dataclass(frozen=True)
class GatewayCompletion:
    content: str
    provider: str
    model: str
    usage: ProviderUsage
    estimated_cost: float
    latency_ms: int


class BaseAIProvider(ABC):
    name: str

    @abstractmethod
    def complete(
        self,
        messages: Sequence[dict[str, str]],
        *,
        model: str,
        temperature: float,
        max_tokens: int | None,
    ) -> ProviderCompletion:
        raise NotImplementedError


class OpenAIAdapter(BaseAIProvider):
    name = "openai"
    base_url = "https://api.openai.com/v1/chat/completions"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.AI_TIMEOUT_SECONDS
        )
        self.max_retries = (
            max_retries if max_retries is not None else settings.AI_MAX_RETRIES
        )

    def complete(
        self,
        messages: Sequence[dict[str, str]],
        *,
        model: str,
        temperature: float,
        max_tokens: int | None,
    ) -> ProviderCompletion:
        if not self._api_key:
            raise AIProviderConfigurationError(
                "OpenAI provider is not configured on the server"
            )

        payload: dict[str, Any] = {
            "model": model,
            "messages": list(messages),
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(
                        self.base_url,
                        headers=headers,
                        json=payload,
                    )
                if response.status_code >= 500:
                    raise AIProviderError("AI provider temporarily unavailable")
                if response.status_code >= 400:
                    raise AIProviderError("AI provider rejected the request")
                return self._parse_response(response.json(), model=model)
            except (
                httpx.TimeoutException,
                httpx.RequestError,
                AIProviderError,
            ) as error:
                last_error = error
                if attempt >= self.max_retries:
                    break

        raise AIProviderError(
            "AI provider request failed after retries"
        ) from last_error

    @staticmethod
    def _parse_response(
        payload: dict[str, Any],
        *,
        model: str,
    ) -> ProviderCompletion:
        choices = payload.get("choices") or []
        if not choices:
            raise AIProviderError("AI provider returned no completion")
        content = choices[0].get("message", {}).get("content")
        if not isinstance(content, str):
            raise AIProviderError("AI provider returned an invalid completion")

        usage = payload.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        total_tokens = int(
            usage.get("total_tokens", prompt_tokens + completion_tokens)
        )
        return ProviderCompletion(
            content=content,
            model=str(payload.get("model") or model),
            usage=ProviderUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
        )


class AIGateway:
    MODEL_PRICING_PER_MILLION_TOKENS = {
        "gpt-4o": (5.0, 15.0),
        "gpt-4o-mini": (0.15, 0.60),
    }

    def __init__(
        self,
        providers: dict[str, BaseAIProvider] | None = None,
    ) -> None:
        self.providers = providers or {"openai": OpenAIAdapter()}

    def complete(
        self,
        messages: Sequence[dict[str, str]],
        *,
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> GatewayCompletion:
        provider_name = provider or settings.AI_DEFAULT_PROVIDER
        model_name = model or settings.AI_DEFAULT_MODEL
        adapter = self.providers.get(provider_name)
        if adapter is None:
            raise AIProviderError(f"Unsupported AI provider: {provider_name}")

        started_at = perf_counter()
        result = adapter.complete(
            messages,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        latency_ms = round((perf_counter() - started_at) * 1000)
        return GatewayCompletion(
            content=result.content,
            provider=provider_name,
            model=result.model,
            usage=result.usage,
            estimated_cost=self.estimate_cost(
                provider_name,
                result.model,
                result.usage,
            ),
            latency_ms=latency_ms,
        )

    @classmethod
    def estimate_cost(
        cls,
        provider: str,
        model: str,
        usage: ProviderUsage,
    ) -> float:
        if provider != "openai":
            return 0.0
        prompt_price, completion_price = cls.MODEL_PRICING_PER_MILLION_TOKENS.get(
            model,
            (0.0, 0.0),
        )
        return round(
            (usage.prompt_tokens / 1_000_000 * prompt_price)
            + (usage.completion_tokens / 1_000_000 * completion_price),
            8,
        )


gateway = AIGateway()
