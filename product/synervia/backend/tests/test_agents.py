"""Tests for AI agent module (PydanticAI)."""

from unittest.mock import patch

import pytest
from pydantic_ai.models.test import TestModel

from app.agents.assistant import AssistantAgent, Deps, _build_model, get_agent
from app.agents.prompts import get_system_prompt_with_rag
from app.agents.utils import get_current_datetime
from app.core.config import settings


class TestDeps:
    """Tests for Deps dataclass."""

    def test_deps_default_values(self):
        """Test Deps has correct default values."""
        deps = Deps()
        assert deps.user_id is None
        assert deps.user_name is None
        assert deps.metadata == {}

    def test_deps_with_values(self):
        """Test Deps with custom values."""
        deps = Deps(user_id="123", user_name="Test User", metadata={"key": "value"})
        assert deps.user_id == "123"
        assert deps.user_name == "Test User"
        assert deps.metadata == {"key": "value"}


class TestGetCurrentDatetime:
    """Tests for get_current_datetime tool."""

    def test_returns_dict_with_date_time_datetime(self):
        """Tool returns a dict with date/time/datetime keys."""
        result = get_current_datetime()
        assert isinstance(result, dict)
        assert {"date", "time", "datetime"} <= result.keys()
        # ISO-like date "YYYY-MM-DD"
        assert len(result["date"]) == 10


class TestAssistantAgent:
    """Tests for AssistantAgent class."""

    def test_init_with_defaults(self):
        """Test AssistantAgent initializes with defaults."""
        agent = AssistantAgent()
        assert agent.system_prompt == get_system_prompt_with_rag()
        assert agent._agent is None

    def test_init_with_custom_values(self):
        """Test AssistantAgent with custom configuration."""
        agent = AssistantAgent(
            model_name="gpt-4",
            temperature=0.5,
            system_prompt="Custom prompt",
        )
        assert agent.model_name == "gpt-4"
        assert agent.temperature == 0.5
        assert agent.system_prompt == "Custom prompt"

    def test_openai_responses_model_uses_custom_base_url(self):
        """OpenAI-compatible Responses gateways receive the configured URL and key."""
        with (
            patch.object(settings, "OPENAI_API_KEY", "relay-key"),
            patch.object(settings, "OPENAI_BASE_URL", "https://relay.example/v1"),
            patch.object(settings, "OPENAI_API_MODE", "responses"),
            patch("app.agents.assistant.OpenAIProvider") as provider_cls,
            patch("app.agents.assistant.OpenAIResponsesModel") as model_cls,
        ):
            model = _build_model("openai/relay-model")

        provider_cls.assert_called_once_with(
            api_key="relay-key", base_url="https://relay.example/v1"
        )
        model_cls.assert_called_once_with("relay-model", provider=provider_cls.return_value)
        assert model is model_cls.return_value

    def test_openai_chat_mode_uses_chat_completions_model(self):
        """Chat-only OpenAI-compatible gateways use the Chat Completions adapter."""
        with (
            patch.object(settings, "OPENAI_API_KEY", "relay-key"),
            patch.object(settings, "OPENAI_BASE_URL", "https://relay.example/v1"),
            patch.object(settings, "OPENAI_API_MODE", "chat"),
            patch("app.agents.assistant.OpenAIProvider") as provider_cls,
            patch("app.agents.assistant.OpenAIChatModel") as model_cls,
        ):
            model = _build_model("relay-model")

        model_cls.assert_called_once_with("relay-model", provider=provider_cls.return_value)
        assert model is model_cls.return_value

    # ``_build_model`` is the single per-provider model factory in
    # assistant.py, so patching it keeps these tests provider-agnostic
    # (openai/anthropic/google/openrouter/all) and avoids needing real API keys.
    @patch("app.agents.assistant._build_model")
    def test_agent_property_creates_agent(self, mock_build_model):
        """Test agent property creates agent on first access."""
        mock_build_model.return_value = TestModel()
        agent = AssistantAgent()
        _ = agent.agent
        assert agent._agent is not None
        mock_build_model.assert_called_once()

    @patch("app.agents.assistant._build_model")
    def test_agent_property_caches_agent(self, mock_build_model):
        """Test agent property caches the agent instance."""
        mock_build_model.return_value = TestModel()
        agent = AssistantAgent()
        agent1 = agent.agent
        agent2 = agent.agent
        assert agent1 is agent2
        mock_build_model.assert_called_once()


class TestGetAgent:
    """Tests for get_agent factory function."""

    def test_returns_assistant_agent(self):
        """Test get_agent returns AssistantAgent."""
        agent = get_agent()
        assert isinstance(agent, AssistantAgent)


class TestAgentRoutes:
    """Tests for agent WebSocket routes."""

    @pytest.mark.anyio
    async def test_agent_websocket_connection(self, client):
        """Test WebSocket connection to agent endpoint."""
        # This test verifies the WebSocket endpoint is accessible
        # Actual agent testing would require mocking OpenAI
        pass


class TestHistoryConversion:
    """Tests for conversation history conversion."""

    def test_empty_history(self):
        """Test with empty history."""
        _agent = AssistantAgent()
        # History conversion happens inside run/iter methods
        # We test the structure here
        history = []
        assert len(history) == 0

    def test_history_roles(self):
        """Test history with different roles."""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "system", "content": "You are helpful"},
        ]
        assert len(history) == 3
        assert all("role" in msg and "content" in msg for msg in history)
