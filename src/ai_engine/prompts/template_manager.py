"""System Prompt Template Manager with Versioning and Interpolation."""

from typing import Any, Dict, Optional


class SystemPromptTemplateManager:
    """Manages system directives, prompt templates, and variable interpolation."""

    DEFAULT_SYSTEM_PROMPT = (
        "You are Jarvis, a production-grade autonomous AI assistant. "
        "Your core directives are: \n"
        "1. Strictly adhere to user instructions with high precision.\n"
        "2. Leverage tools effectively when detailed information or actions are required.\n"
        "3. Provide clean, structured, and helpful responses.\n"
        "Current System Context: Environment = {environment}, App = {app_name} v{app_version}"
    )

    def __init__(self, templates: Optional[Dict[str, str]] = None) -> None:
        self._templates = templates or {
            "default": self.DEFAULT_SYSTEM_PROMPT,
            "coder": "You are Jarvis Developer Assistant, an expert software engineer specializing in Clean Architecture and SOLID principles.",
            "researcher": "You are Jarvis Research Assistant, an expert analyst providing thorough summaries and fact verification."
        }

    def render(self, template_name: str = "default", **kwargs: Any) -> str:
        """Renders prompt template with variable interpolation."""
        template = self._templates.get(template_name, self.DEFAULT_SYSTEM_PROMPT)
        try:
            return template.format(**kwargs)
        except KeyError:
            return template
