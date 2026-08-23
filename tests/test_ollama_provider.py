"""Unit and Integration Tests for Ollama Model Provider."""

import asyncio
from datetime import datetime, timezone
import json
import unittest
from unittest.mock import MagicMock, patch
import urllib.error

from core.exceptions import ProviderUnavailableError
from model_routing.providers.ollama_provider import OllamaModelProvider
from model_routing.schemas import (
    ChatMessage,
    MessageRole,
    ModelRequest,
    ModelResponse,
)


class TestOllamaModelProviderUnit(unittest.IsolatedAsyncioTestCase):
    """Unit tests for OllamaModelProvider with deterministic mocks."""

    def setUp(self) -> None:
        self.provider = OllamaModelProvider(
            base_url="http://127.0.0.1:11434",
            model_name="llama3:latest",
            timeout_seconds=5.0,
        )

    @patch("urllib.request.urlopen")
    async def test_ollama_generate_success(self, mock_urlopen: MagicMock) -> None:
        """Verify successful response parsing and token counting."""
        fake_response = {
            "model": "llama3:latest",
            "message": {
                "role": "assistant",
                "content": "A Python virtual environment isolates package dependencies.",
            },
            "done_reason": "stop",
            "prompt_eval_count": 25,
            "eval_count": 50,
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(fake_response).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        req = ModelRequest(
            messages=[ChatMessage(role=MessageRole.USER, content="Explain virtual environment.")]
        )
        resp = await self.provider.generate(req)

        self.assertEqual(resp.model_name, "llama3:latest")
        self.assertEqual(resp.provider_name, "ollama")
        self.assertIn("isolates package dependencies", resp.content)
        self.assertEqual(resp.prompt_tokens, 25)
        self.assertEqual(resp.completion_tokens, 50)

    @patch("urllib.request.urlopen")
    async def test_ollama_connection_refused(self, mock_urlopen: MagicMock) -> None:
        """Verify connection refused raises ProviderUnavailableError with clear message."""
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        req = ModelRequest(
            messages=[ChatMessage(role=MessageRole.USER, content="Hello")]
        )
        with self.assertRaises(ProviderUnavailableError) as ctx:
            await self.provider.generate(req)

        self.assertIn("unreachable", str(ctx.exception).lower())

    @patch("urllib.request.urlopen")
    async def test_ollama_model_not_found(self, mock_urlopen: MagicMock) -> None:
        """Verify 404 HTTPError raises ProviderUnavailableError advising ollama pull."""
        err = urllib.error.HTTPError(
            url="http://127.0.0.1:11434/api/chat",
            code=404,
            msg="Not Found",
            hdrs=MagicMock(),
            fp=MagicMock(read=lambda: b'{"error":"model not found"}'),
        )
        mock_urlopen.side_effect = err

        req = ModelRequest(
            messages=[ChatMessage(role=MessageRole.USER, content="Hello")]
        )
        with self.assertRaises(ProviderUnavailableError) as ctx:
            await self.provider.generate(req)

        self.assertIn("not found", str(ctx.exception).lower())

    @patch("urllib.request.urlopen")
    async def test_check_availability_tags(self, mock_urlopen: MagicMock) -> None:
        """Verify tags endpoint checks for model existence."""
        fake_tags = {
            "models": [
                {"name": "llama3:latest"},
                {"name": "mistral:latest"},
            ]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(fake_tags).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        avail, status, models = await self.provider.check_availability()
        self.assertTrue(avail)
        self.assertEqual(status, "AVAILABLE")
        self.assertIn("llama3:latest", models)


class TestOllamaModelProviderLiveIntegration(unittest.IsolatedAsyncioTestCase):
    """Smoke test running against actual Ollama instance if available on the system."""

    async def asyncSetUp(self) -> None:
        self.provider = OllamaModelProvider(model_name="llama3:latest")
        self.is_live = await self.provider.is_healthy()

    async def test_live_ollama_inference(self) -> None:
        """Run real query against local Ollama if running."""
        if not self.is_live:
            self.skipTest("Ollama daemon is not running locally.")

        req = ModelRequest(
            messages=[
                ChatMessage(role=MessageRole.USER, content="Respond with exactly the word: SUCCESS")
            ],
            temperature=0.0,
            max_tokens=20,
        )
        resp = await self.provider.generate(req)
        self.assertEqual(resp.provider_name, "ollama")
        self.assertIn("SUCCESS", resp.content.strip().upper())
