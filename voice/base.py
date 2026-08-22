"""Abstract Voice Pipeline Interfaces (Wake-Word, STT, TTS)."""

from abc import ABC, abstractmethod


class BaseWakeWordDetector(ABC):
    """Abstract interface for local on-device wake-phrase detection ('Hey Jarvis')."""

    @abstractmethod
    async def listen_for_wake_phrase(self) -> bool:
        """Poll circular RAM buffer for wake trigger."""
        pass


class BaseSTTEngine(ABC):
    """Abstract interface for Speech-to-Text transcription."""

    @abstractmethod
    async def transcribe_audio_chunk(self, audio_bytes: bytes) -> str:
        """Transcribe raw audio frame into text."""
        pass


class BaseTTSEngine(ABC):
    """Abstract interface for Text-to-Speech synthesis."""

    @abstractmethod
    async def synthesize_speech(self, text: str) -> bytes:
        """Convert text into synthesized audio waveform."""
        pass
