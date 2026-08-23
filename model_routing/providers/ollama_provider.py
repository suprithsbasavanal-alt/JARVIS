"""Production Local Model Provider for Ollama HTTP API (Phase 11 Real LLM Inference)."""

import asyncio
from datetime import datetime, timezone
import json
import os
import time
from typing import Any
import urllib.error
import urllib.request

from core.exceptions import ProviderUnavailableError
from model_routing.base import BaseModelProvider
from model_routing.schemas import (
    ChatMessage,
    ModelRequest,
    ModelResponse,
    ToolCallDefinition,
)


class OllamaModelProvider(BaseModelProvider):
    """Executes real local on-device LLM inference via the native Ollama HTTP API."""

    def __init__(
        self,
        base_url: str | None = None,
        endpoint: str | None = None,
        model_name: str | None = None,
        timeout_seconds: float = 60.0,
        provider_name: str = "ollama",
    ) -> None:
        super().__init__(provider_name)
        url = base_url or endpoint or os.getenv("JARVIS_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.base_url = url.rstrip("/")
        self.model_name = model_name or os.getenv("JARVIS_OLLAMA_MODEL", "llama3:latest")
        self.timeout = timeout_seconds
        self._last_latency_ms: float = 0.0

    def _sync_http_post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute blocking HTTP POST within thread worker."""
        url = f"{self.base_url}{endpoint}"
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw_bytes = resp.read()
                return json.loads(raw_bytes.decode("utf-8"))
        except urllib.error.HTTPError as http_err:
            err_body = ""
            try:
                err_body = http_err.read().decode("utf-8")
            except Exception:
                pass
            if http_err.code == 400 and "tools" in payload:
                # Model (like llama3:latest) does not support Ollama tools parameter; retry dialogue turn without tools
                payload_no_tools = {k: v for k, v in payload.items() if k != "tools"}
                return self._sync_http_post(endpoint, payload_no_tools)
            if http_err.code == 404:
                raise ProviderUnavailableError(
                    f"Ollama model '{self.model_name}' not found at {self.base_url}. "
                    f"Run 'ollama pull {self.model_name}'. Details: {err_body}"
                ) from http_err
            raise ProviderUnavailableError(
                f"Ollama HTTP {http_err.code} error from {url}: {err_body or http_err.reason}"
            ) from http_err
        except urllib.error.URLError as url_err:
            raise ProviderUnavailableError(
                f"Ollama daemon unreachable at {self.base_url}: {url_err.reason}. "
                "Ensure Ollama is running ('ollama serve')."
            ) from url_err
        except TimeoutError as to_err:
            raise ProviderUnavailableError(
                f"Ollama inference timed out after {self.timeout}s on model '{self.model_name}'."
            ) from to_err

    def _sync_http_get(self, endpoint: str) -> dict[str, Any]:
        """Execute blocking HTTP GET within thread worker."""
        url = f"{self.base_url}{endpoint}"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                raw_bytes = resp.read()
                return json.loads(raw_bytes.decode("utf-8"))
        except Exception as err:
            raise ProviderUnavailableError(
                f"Cannot query Ollama tags at {self.base_url}: {err}"
            ) from err

    async def check_availability(self) -> tuple[bool, str, list[str]]:
        """Verify Ollama server connectivity and model availability."""
        try:
            tags_data = await asyncio.to_thread(self._sync_http_get, "/api/tags")
            models_list = [m.get("name", "") for m in tags_data.get("models", [])]
            
            # Check exact name or tag match (e.g. 'llama3:latest' vs 'llama3')
            model_base = self.model_name.split(":")[0]
            has_model = any(
                m == self.model_name or m.startswith(f"{model_base}:")
                for m in models_list
            )
            if not has_model:
                return (
                    False,
                    f"Model '{self.model_name}' not in installed models: {models_list}",
                    models_list,
                )
            return True, "AVAILABLE", models_list
        except ProviderUnavailableError as pue:
            return False, str(pue), []
        except Exception as e:
            return False, f"Ollama health check error: {e}", []

    async def is_healthy(self) -> bool:
        """Return True only if Ollama is actively reachable."""
        avail, _, _ = await self.check_availability()
        return avail

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Perform real LLM inference against local Ollama server."""
        start_time = time.perf_counter()

        # Format chat messages for Ollama /api/chat
        ollama_messages: list[dict[str, Any]] = []
        for msg in request.messages:
            role_str = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
            ollama_msg: dict[str, Any] = {
                "role": role_str,
                "content": msg.content,
            }
            if msg.name:
                ollama_msg["name"] = msg.name
            ollama_messages.append(ollama_msg)

        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }

        if request.tools:
            # Map tools schema if supported by model
            payload["tools"] = request.tools

        # Execute network call in thread executor
        resp_data = await asyncio.to_thread(self._sync_http_post, "/api/chat", payload)

        self._last_latency_ms = (time.perf_counter() - start_time) * 1000.0

        msg_obj = resp_data.get("message", {})
        content = msg_obj.get("content", "")

        # Extract tool calls if model returned structured tool invocations
        tool_calls: list[ToolCallDefinition] = []
        for tc in msg_obj.get("tool_calls", []):
            fn = tc.get("function", {})
            t_name = fn.get("name", "")
            t_args = fn.get("arguments", {})
            if isinstance(t_args, str):
                try:
                    t_args = json.loads(t_args)
                except Exception:
                    t_args = {"raw": t_args}
            if t_name:
                tool_calls.append(
                    ToolCallDefinition(tool_name=t_name, arguments=t_args)
                )

        prompt_tokens = int(resp_data.get("prompt_eval_count", 0))
        completion_tokens = int(resp_data.get("eval_count", 0))

        return ModelResponse(
            model_name=resp_data.get("model", self.model_name),
            provider_name=self.provider_name,
            content=content,
            tool_calls=tool_calls,
            finish_reason=resp_data.get("done_reason", "stop"),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    def get_runtime_info(self) -> dict[str, Any]:
        """Return diagnostic metadata without secrets."""
        return {
            "provider_name": self.provider_name,
            "backend_type": "REAL_LOCAL_OLLAMA",
            "endpoint": self.base_url,
            "model_name": self.model_name,
            "timeout_seconds": self.timeout,
            "last_latency_ms": round(self._last_latency_ms, 2),
        }
