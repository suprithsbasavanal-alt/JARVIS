"""Persona Governor and Conversational Style Rules for JARVIS."""

from core.context import SessionContext
from core.types import ExecutionContext


class PersonaGovernor:
    """Enforces personality attributes, context-appropriate salutations, and epistemic honesty."""

    BASE_SYSTEM_PROMPT = """You are JARVIS, a sophisticated, calm, highly intelligent personal AI assistant.
Your attributes:
- Professional, composed, and articulate at all times.
- Slightly witty when appropriate, but never frivolous.
- Direct, concise, and structured in your explanations.
- Epistemically honest: If you detect a logical flaw, technical error, or unsafe premise in the user's request, respectfully disagree and clearly explain your reasoning.
- Never assume or pretend to know whether the user is alone unless reliable, explicitly permitted context exists.
"""

    @classmethod
    def get_salutation_for_context(cls, context: SessionContext) -> str:
        """Return 'Suprith' in private contexts and 'Sir' in formal/public contexts."""
        if context.exec_context == ExecutionContext.PRIVATE:
            return context.user_name
        return context.formal_salutation

    @classmethod
    def construct_system_prompt(cls, context: SessionContext) -> str:
        """Assemble dynamic system prompt incorporating active context rules."""
        salutation = cls.get_salutation_for_context(context)
        context_guideline = f"Address the user as '{salutation}'."

        if not context.is_user_confirmed_alone:
            context_guideline += " Note: Physical solitude is unconfirmed; maintain professional boundaries."

        return f"{cls.BASE_SYSTEM_PROMPT}\nActive Context Guideline: {context_guideline}\n"
