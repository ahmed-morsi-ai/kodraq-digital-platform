from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
import logging
from time import perf_counter

import httpx
from google import genai
from google.genai import errors, types

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIProviderError(Exception):
    """Safe, provider-neutral error raised by the gateway."""

    def __init__(self, detail: str, *, status_code: int = 502) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class AIProviderConfigurationError(AIProviderError):
    """Raised when a provider is not configured on the server."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=503)


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


class GeminiAdapter(BaseAIProvider):
    name = "gemini"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
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
                "Gemini provider is not configured on the server"
            )

        model_name = model
        prompt = self._format_prompt(messages)
        client = genai.Client(api_key=self._api_key)
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    http_options=types.HttpOptions(
                        timeout=int(self.timeout_seconds * 1000),
                        retry_options=types.HttpRetryOptions(
                            attempts=self.max_retries + 1
                        ),
                    ),
                ),
            )
        except errors.APIError as error:
            detail = self._redact_api_key(error.message or str(error))[:500]
            logger.error(
                "Gemini API returned HTTP %s: %s",
                error.code,
                detail,
            )
            raise AIProviderError(
                f"Gemini API returned HTTP {error.code}: {detail}"
            ) from None
        except (httpx.TimeoutException, httpx.RequestError) as error:
            logger.error(
                "Gemini SDK transport failed: %s",
                type(error).__name__,
            )
            raise AIProviderError("Gemini API request failed") from None

        text_output = response.text
        if not isinstance(text_output, str) or not text_output:
            raise AIProviderError("AI provider returned an invalid completion")

        usage = response.usage_metadata
        prompt_tokens = int(usage.prompt_token_count or 0) if usage else 0
        completion_tokens = int(usage.candidates_token_count or 0) if usage else 0
        total_tokens = (
            int(usage.total_token_count)
            if usage and usage.total_token_count is not None
            else prompt_tokens + completion_tokens
        )
        return ProviderCompletion(
            content=text_output,
            model=str(response.model_version or model_name),
            usage=ProviderUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
        )

    def _redact_api_key(self, detail: str) -> str:
        if self._api_key:
            return detail.replace(self._api_key, "[redacted]")
        return detail

    @staticmethod
    def _format_prompt(messages: Sequence[dict[str, str]]) -> str:
        system_messages = [
            message["content"]
            for message in messages
            if message.get("role") == "system"
        ]
        conversation = [
            f"{'Tutor' if message.get('role') == 'assistant' else 'Student'}: "
            f"{message['content']}"
            for message in messages
            if message.get("role") != "system"
        ]

        prompt_sections = []
        if system_messages:
            prompt_sections.append("Instructions:\n" + "\n\n".join(system_messages))
        if conversation:
            prompt_sections.append("Conversation:\n" + "\n".join(conversation))
        return "\n\n".join(prompt_sections)

class AIGateway:
    def __init__(
        self,
        providers: dict[str, BaseAIProvider] | None = None,
    ) -> None:
        self.providers = providers or {"gemini": GeminiAdapter()}

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
        return 0.0


gateway = AIGateway()
