"""Text-Only Conversation Interface & Interactive Driver for JARVIS."""

from collections.abc import Callable
from agents.base import BaseAgent
from core.context import SessionContext
from core.exceptions import HumanConfirmationRequiredError, PermissionDeniedError, SecurityError
from security.permissions import ApprovalCard, ApprovalToken


class TextConversationInterface:
    """Synchronous and asynchronous text interface for testing and interacting with JARVIS."""

    def __init__(
        self,
        agent_loop: BaseAgent,
        context: SessionContext | None = None,
        confirmation_callback: Callable[[ApprovalCard], bool] | None = None,
    ) -> None:
        self.agent_loop = agent_loop
        self.context = context or SessionContext()
        self.confirmation_callback = confirmation_callback

    async def send_message(self, user_text: str) -> str:
        """Send a message to JARVIS and receive the text response."""
        try:
            response = await self.agent_loop.process_turn(user_text, self.context)
            return response.content

        except HumanConfirmationRequiredError as confirm_err:
            if self.confirmation_callback:
                card: ApprovalCard = confirm_err.approval_card
                approved = self.confirmation_callback(card)
                if approved:
                    token = ApprovalToken(
                        card_id=card.card_id,
                        payload_hash=card.payload_hash,
                        signature="simulated-sig",
                    )
                    res = await self.agent_loop.process_turn(
                        user_text, self.context, approval_token=token, approval_card=card
                    )
                    return res.content
                return f"[Action '{confirm_err.action_name}' was rejected by user.]"

            return f"[Action '{confirm_err.action_name}' halted: Human confirmation required.]"

        except PermissionDeniedError as perm_err:
            return f"[Permission Denied]: {perm_err}"

        except SecurityError as sec_err:
            return f"[Security Block]: {sec_err}"

        except Exception as err:
            return f"[JARVIS Core Error]: An unexpected issue occurred: {err}"
