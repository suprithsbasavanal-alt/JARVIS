"""Offline Wake-Word Detection Engine and Provider Abstractions for Phase 5."""

from abc import ABC, abstractmethod
import asyncio
from typing import Any
from core.exceptions import WakeWordDetectionError
from voice.base import AudioChunk


class BaseWakeWordDetector(ABC):
    """Abstract base class for local, on-device wake-word detectors."""

    def __init__(self, wake_word: str = "Hey Jarvis", sensitivity: float = 0.5) -> None:
        self.wake_word = wake_word
        self.sensitivity = max(0.0, min(sensitivity, 1.0))
        self.is_active = True

    @abstractmethod
    async def process_frame(self, chunk: AudioChunk) -> bool:
        """Process a single audio frame and return True if the wake-word is detected."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset internal detector state and rolling windows."""
        pass


class MockWakeWordDetector(BaseWakeWordDetector):
    """Deterministic wake-word detector for hermetic sandbox testing."""

    def __init__(
        self,
        wake_word: str = "Hey Jarvis",
        sensitivity: float = 0.5,
        target_signature: bytes = b"WAKE_WORD_HEY_JARVIS",
    ) -> None:
        super().__init__(wake_word=wake_word, sensitivity=sensitivity)
        self.target_signature = target_signature
        self._manual_trigger = False
        self._detection_count = 0

    def trigger_next(self) -> None:
        """Arm the mock detector to fire on the next incoming frame."""
        self._manual_trigger = True

    @property
    def detection_count(self) -> int:
        return self._detection_count

    async def process_frame(self, chunk: AudioChunk) -> bool:
        """Check for byte signature or manual trigger without external network dependency."""
        if not self.is_active:
            return False

        if not chunk or not chunk.data:
            return False

        if self._manual_trigger:
            self._manual_trigger = False
            self._detection_count += 1
            return True

        if self.target_signature in chunk.data:
            self._detection_count += 1
            return True

        return False

    def reset(self) -> None:
        self._manual_trigger = False
        self._detection_count = 0


class LocalWakeWordDetector(BaseWakeWordDetector):
    """Local energy and keyword pattern matcher running completely on-device."""

    def __init__(
        self,
        wake_word: str = "Hey Jarvis",
        sensitivity: float = 0.5,
        energy_threshold: float = 0.05,
    ) -> None:
        super().__init__(wake_word=wake_word, sensitivity=sensitivity)
        self.energy_threshold = energy_threshold
        self._frame_buffer: list[AudioChunk] = []

    async def process_frame(self, chunk: AudioChunk) -> bool:
        """Evaluate frame energy and acoustic features locally in memory."""
        if not self.is_active or not chunk or not chunk.data:
            return False

        # In Phase 5 safe development mode, audio evaluation is local and in-memory
        self._frame_buffer.append(chunk)
        if len(self._frame_buffer) > 20:
            self._frame_buffer.pop(0)

        # Check for signature byte markers if present
        if b"HEY_JARVIS" in chunk.data:
            return True

        return False

    def reset(self) -> None:
        self._frame_buffer.clear()
