"""Token Optimizer, Context Window Pruning, and KV-Cache Prefix Stabilization (Phase 11)."""

import re
from typing import Any
from model_routing.schemas import ChatMessage, MessageRole


class TokenOptimizer:
    """Optimizes context token budgets, prunes message history, and stabilizes KV-cache prefixes."""

    # Approximate character-to-token ratio (4 chars ≈ 1 token for English text/code)
    CHARS_PER_TOKEN = 4.0

    def __init__(
        self,
        max_context_tokens: int = 4096,
        sliding_window_turns: int = 10,
    ) -> None:
        self.max_context_tokens = max_context_tokens
        self.sliding_window_turns = sliding_window_turns

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """Fast, hermetic token count estimation without external C tokenizer dependencies."""
        if not text:
            return 0
        # Count words and punctuation/whitespace chunks
        words = len(re.findall(r"\w+|[^\w\s]+", text))
        char_estimate = int(len(text) / cls.CHARS_PER_TOKEN)
        # Conservative upper bound between word count and character ratio
        return max(words, char_estimate, 1)

    @classmethod
    def estimate_messages_tokens(cls, messages: list[ChatMessage]) -> int:
        """Estimate aggregate token count across a list of ChatMessages."""
        total = 0
        for msg in messages:
            total += cls.estimate_tokens(msg.content) + 4  # 4 tokens overhead per message turn
        return total

    @classmethod
    def normalize_whitespace(cls, text: str) -> str:
        """Strip redundant empty lines and trailing whitespace while preserving structure."""
        if not text:
            return ""
        # Replace multiple consecutive blank lines with a single blank line
        cleaned = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        # Strip trailing whitespace on each line
        lines = [line.rstrip() for line in cleaned.splitlines()]
        return "\n".join(lines).strip()

    @classmethod
    def stabilize_system_prefix(cls, system_prompt: str) -> str:
        """Format system prompt deterministically to maximize KV-cache prefix hits in LLM runtimes."""
        if not system_prompt:
            return ""
        # Standardize line endings and normalize whitespaces
        normalized = cls.normalize_whitespace(system_prompt)
        # Append invariant trailing newline for cache prefix alignment
        return f"{normalized}\n"

    def optimize_messages(
        self,
        messages: list[ChatMessage],
        max_tokens: int | None = None,
        max_turns: int | None = None,
    ) -> tuple[list[ChatMessage], int]:
        """Prune and optimize messages to fit within token budget while preserving system prompt.
        
        Returns:
            tuple of (optimized_messages, estimated_total_tokens)
        """
        if not messages:
            return [], 0

        target_max_tokens = max_tokens or self.max_context_tokens
        target_max_turns = max_turns or self.sliding_window_turns

        # 1. Separate system message from conversation dialogue turns
        system_msgs: list[ChatMessage] = []
        dialogue_msgs: list[ChatMessage] = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                # Stabilize system prompt prefix
                stabilized_content = self.stabilize_system_prefix(msg.content)
                system_msgs.append(
                    ChatMessage(
                        role=msg.role,
                        content=stabilized_content,
                        name=msg.name,
                        tool_call_id=msg.tool_call_id,
                    )
                )
            else:
                cleaned_content = self.normalize_whitespace(msg.content)
                dialogue_msgs.append(
                    ChatMessage(
                        role=msg.role,
                        content=cleaned_content,
                        name=msg.name,
                        tool_call_id=msg.tool_call_id,
                    )
                )

        # 2. Apply sliding window on dialogue turns (keep the most recent N turns)
        if len(dialogue_msgs) > target_max_turns:
            dialogue_msgs = dialogue_msgs[-target_max_turns:]

        # 3. Fit dialogue messages within token budget (newest to oldest)
        system_tokens = self.estimate_messages_tokens(system_msgs)
        available_dialogue_tokens = max(0, target_max_tokens - system_tokens)

        retained_dialogue: list[ChatMessage] = []
        current_tokens = 0

        for msg in reversed(dialogue_msgs):
            msg_tokens = self.estimate_tokens(msg.content) + 4
            if current_tokens + msg_tokens <= available_dialogue_tokens:
                retained_dialogue.insert(0, msg)
                current_tokens += msg_tokens
            else:
                # If even a single recent message exceeds the budget, truncate its text
                if not retained_dialogue and available_dialogue_tokens > 10:
                    truncated_chars = int((available_dialogue_tokens - 10) * self.CHARS_PER_TOKEN)
                    truncated_content = msg.content[-truncated_chars:] + " [truncated...]"
                    retained_dialogue.insert(
                        0,
                        ChatMessage(
                            role=msg.role,
                            content=truncated_content,
                            name=msg.name,
                            tool_call_id=msg.tool_call_id,
                        ),
                    )
                break

        final_messages = system_msgs + retained_dialogue
        final_token_count = self.estimate_messages_tokens(final_messages)
        return final_messages, final_token_count
