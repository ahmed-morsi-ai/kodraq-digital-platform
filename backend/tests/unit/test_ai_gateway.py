from __future__ import annotations

from types import SimpleNamespace

import pytest
from google.genai import errors

from app.api.v1 import ai as ai_api
from app.core.config import settings
from app.main import app
from app.services.ai_gateway import (
    AIGateway,
    AIProviderError,
    AIProviderConfigurationError,
    GeminiAdapter,
    GatewayCompletion,
    ProviderCompletion,
    ProviderUsage,
)


def test_gemini_adapter_sends_formatted_context_and_maps_response(monkeypatch):
    requests = []

    class MockModels:
        @staticmethod
        def generate_content(*, model, contents, config):
            requests.append(
                {"model": model, "contents": contents, "config": config}
            )
            return SimpleNamespace(
                text="Grounded tutor response",
                model_version="gemini-3.8-flash",
                usage_metadata=SimpleNamespace(
                    prompt_token_count=21,
                    candidates_token_count=8,
                    total_token_count=29,
                ),
            )

    class MockClient:
        def __init__(self, *, api_key):
            requests.append({"api_key": api_key})
            self.models = MockModels()

    monkeypatch.setattr("app.services.ai_gateway.genai.Client", MockClient)
    adapter = GeminiAdapter(
        api_key="test-gemini-key",
        timeout_seconds=30,
        max_retries=0,
    )

    result = adapter.complete(
        [
            {
                "role": "system",
                "content": "Use the lesson context when answering.",
            },
            {
                "role": "user",
                "content": "Lesson: Understanding Backend Architecture.",
            },
            {"role": "assistant", "content": "What would you like to know?"},
            {"role": "user", "content": "What is a service layer?"},
        ],
        model="gemini-3.8-flash",
        temperature=0.2,
        max_tokens=800,
    )

    assert requests[0]["api_key"] == "test-gemini-key"
    assert requests[1]["model"] == "gemini-3.8-flash"
    prompt = requests[1]["contents"]
    assert "Use the lesson context when answering." in prompt
    assert "Lesson: Understanding Backend Architecture." in prompt
    assert "Tutor: What would you like to know?" in prompt
    assert "Student: What is a service layer?" in prompt
    assert requests[1]["config"].temperature == 0.2
    assert requests[1]["config"].max_output_tokens == 800
    assert requests[1]["config"].http_options.timeout == 30_000
    assert requests[1]["config"].http_options.retry_options.attempts == 1
    assert result.content == "Grounded tutor response"
    assert result.model == "gemini-3.8-flash"
    assert result.usage == ProviderUsage(
        prompt_tokens=21,
        completion_tokens=8,
        total_tokens=29,
    )


def test_gemini_adapter_requires_api_key():
    adapter = GeminiAdapter(api_key=None, max_retries=0)

    with pytest.raises(AIProviderConfigurationError, match="Gemini provider"):
        adapter.complete(
            [{"role": "user", "content": "hello"}],
            model="gemini-3.8-flash",
            temperature=0.2,
            max_tokens=None,
        )


def test_gateway_uses_supported_default_model():
    captured = {}

    class MockProvider:
        @staticmethod
        def complete(_messages, *, model, temperature, max_tokens):
            captured["model"] = model
            return ProviderCompletion(
                content="response",
                model=model,
                usage=ProviderUsage(),
            )

    gateway = AIGateway(providers={"gemini": MockProvider()})
    gateway.complete([{"role": "user", "content": "hello"}])

    assert settings.AI_DEFAULT_MODEL == "gemini-3.8-flash"
    assert captured["model"] == "gemini-3.8-flash"


@pytest.mark.parametrize(
    ("status_code", "error_detail"),
    [
        (400, "Invalid model name"),
        (401, "API key not valid"),
    ],
)
def test_gemini_adapter_logs_and_raises_api_error(
    monkeypatch,
    caplog,
    status_code,
    error_detail,
):
    class MockModels:
        @staticmethod
        def generate_content(**_kwargs):
            raise errors.APIError(
                status_code,
                {"error": {"message": error_detail}},
            )

    class MockClient:
        def __init__(self, **_kwargs):
            self.models = MockModels()

        def close(self):
            return None

    monkeypatch.setattr("app.services.ai_gateway.genai.Client", MockClient)
    adapter = GeminiAdapter(api_key="test-gemini-key", max_retries=0)

    with pytest.raises(
        AIProviderError,
        match=f"HTTP {status_code}: {error_detail}",
    ):
        adapter.complete(
            [{"role": "user", "content": "hello"}],
            model="gemini-1.5-flash",
            temperature=0.2,
            max_tokens=None,
        )

    assert f"Gemini API returned HTTP {status_code}: {error_detail}" in caplog.text


def test_lesson_chat_endpoint_returns_gateway_answer_and_forwards_context(
    client, monkeypatch
):
    registration = client.post(
        "/api/v1/users",
        json={
            "email": "gemini-chat-test@example.test",
            "full_name": "Gemini Chat Test",
            "password": "TestPassword123!",
            "role": "student",
        },
    )
    assert registration.status_code == 201
    login = client.post(
        "/api/v1/login/access-token",
        data={
            "username": "gemini-chat-test@example.test",
            "password": "TestPassword123!",
        },
    )
    assert login.status_code == 200

    captured = {}
    model = "gemini-1.5-flash"

    class MockGateway:
        @staticmethod
        def complete(messages, **kwargs):
            captured["messages"] = messages
            captured["kwargs"] = kwargs
            return GatewayCompletion(
                content="Gemini response",
                provider="gemini",
                model=model,
                usage=ProviderUsage(20, 7, 27),
                estimated_cost=0.0,
                latency_ms=15,
            )

    monkeypatch.setitem(app.dependency_overrides, ai_api.get_ai_gateway, MockGateway)
    response = client.post(
        "/api/v1/ai/completions",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        json={
            "request_type": "lesson_rag_chat",
            "messages": [
                {
                    "role": "system",
                    "content": "Lesson context: Understanding Backend Architecture",
                },
                {"role": "user", "content": "What is a service layer?"},
            ],
            "model": model,
            "temperature": 0.2,
            "max_tokens": 800,
        },
    )

    assert response.status_code == 200
    assert response.json()["content"] == "Gemini response"
    assert response.json()["provider"] == "gemini"
    assert "Understanding Backend Architecture" in captured["messages"][0]["content"]
    assert captured["kwargs"]["model"] == model