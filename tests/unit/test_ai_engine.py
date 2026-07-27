"""Unit Test Suite for AI Engine Component."""

import pytest
from src.ai_engine import (
    MockLLMProvider,
    OpenAIProvider,
    GeminiProvider,
    LLMProviderFactory,
    SystemPromptTemplateManager,
    AgentOrchestrator,
    LLMRequest,
    AgentTask,
)


@pytest.mark.asyncio
async def test_mock_llm_provider_generation():
    """Verifies Mock LLM Provider generation and token counts."""
    provider = MockLLMProvider()
    req = LLMRequest(prompt="Execute system diagnostic")
    res = await provider.generate(req)
    assert res.content == "Jarvis Mock Response to: 'Execute system diagnostic'"
    assert res.prompt_tokens == 3


@pytest.mark.asyncio
async def test_mock_llm_provider_streaming():
    """Verifies Mock LLM Provider asynchronous stream generator."""
    provider = MockLLMProvider(response_override="Token1 Token2 Token3")
    req = LLMRequest(prompt="Stream test")
    tokens = []
    async for token in provider.generate_stream(req):
        tokens.append(token.strip())
    assert tokens == ["Token1", "Token2", "Token3"]


def test_llm_provider_factory():
    """Verifies Provider Factory resolution and custom registration."""
    openai_p = LLMProviderFactory.get_provider("openai")
    assert isinstance(openai_p, OpenAIProvider)

    gemini_p = LLMProviderFactory.get_provider("gemini")
    assert isinstance(gemini_p, GeminiProvider)

    unknown_p = LLMProviderFactory.get_provider("unknown")
    assert isinstance(unknown_p, MockLLMProvider)


def test_prompt_template_manager():
    """Verifies System Prompt Template Manager interpolation."""
    manager = SystemPromptTemplateManager()
    rendered = manager.render("default", environment="development", app_name="Jarvis", app_version="0.1.0")
    assert "Environment = development" in rendered
    assert "Jarvis v0.1.0" in rendered

    coder_prompt = manager.render("coder")
    assert "Clean Architecture" in coder_prompt


@pytest.mark.asyncio
async def test_agent_orchestrator_execution():
    """Verifies Agent Orchestrator end-to-end task execution loop."""
    mock_provider = MockLLMProvider(response_override="Task complete!")
    orchestrator = AgentOrchestrator(llm_provider=mock_provider)

    task = AgentTask(
        task_id="task_001",
        user_query="Run system health audit",
        session_id="session_abc"
    )

    result = await orchestrator.execute_task(task)
    assert result.success is True
    assert result.task_id == "task_001"
    assert result.final_output == "Task complete!"
    assert len(result.steps_taken) == 3
