"""Output Verifier and Post-Execution Sanitizer."""

from security.prompt_guard import PromptGuard
from security.sanitizer import Sanitizer
from tools.base import ToolResult


class OutputVerifier:
    """Validates tool results against prompt injection and PII leakage before returning to context."""

    def __init__(self, prompt_guard: PromptGuard | None = None, sanitizer: Sanitizer | None = None) -> None:
        self.prompt_guard = prompt_guard or PromptGuard()
        self.sanitizer = sanitizer or Sanitizer()

    def verify_tool_result(self, result: ToolResult) -> str:
        """Inspect and safely format tool output."""
        if not result.is_success:
            return f"[Tool Error in {result.tool_name}]: {result.error_message}"

        raw_str = str(result.output_data)

        # Check for injection attempts in external tool output
        self.prompt_guard.inspect(raw_str, source=f"tool_output:{result.tool_name}")

        # Wrap in untrusted boundaries to neutralize any latent instructions
        return self.prompt_guard.wrap_untrusted_content(raw_str, source_label=result.tool_name)
