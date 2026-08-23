"""Local Streaming Speech-to-Text (STT) Provider Abstraction for Phase 5."""

from abc import ABC, abstractmethod
import asyncio
from typing import Any, AsyncIterator
from core.compat import BaseModel, Field
from core.exceptions import STTTranscriptionError
from voice.base import AudioChunk


class SpeechTranscript(BaseModel):
    """Container for transcribed speech text and acoustic confidence metrics."""
    text: str
    confidence: float = 1.0
    language: str = "en"
    duration_seconds: float = 0.0
    is_final: bool = True
    words: list[dict[str, Any]] = Field(default_factory=list)


class BaseSTTProvider(ABC):
    """Abstract interface for local on-device Speech-to-Text engines."""

    def __init__(self, provider_name: str = "base_stt") -> None:
        self.provider_name = provider_name

    @abstractmethod
    async def transcribe_chunks(
        self,
        chunks: list[AudioChunk],
        language: str = "en",
    ) -> SpeechTranscript:
        """Transcribe buffered list of audio chunks to text."""
        pass


class MockSTTProvider(BaseSTTProvider):
    """Deterministic, local mock STT engine for hermetic sandbox testing."""

    def __init__(self) -> None:
        super().__init__(provider_name="mock_whisper_local")
        self._fixtures: dict[bytes, str] = {}
        self._default_text = "What is the status of system security?"
        self._hang_seconds = 0.0
        self._should_fail = False

    def register_fixture(self, audio_byte_marker: bytes, transcript_text: str) -> None:
        """Register specific transcript output for a given audio byte pattern."""
        self._fixtures[audio_byte_marker] = transcript_text

    def set_default_text(self, text: str) -> None:
        self._default_text = text

    def set_hang_timeout(self, seconds: float) -> None:
        self._hang_seconds = seconds

    def set_failure_mode(self, fail: bool) -> None:
        self._should_fail = fail

    async def transcribe_chunks(
        self,
        chunks: list[AudioChunk],
        language: str = "en",
    ) -> SpeechTranscript:
        """Transcribe buffered chunks deterministically without network communication."""
        if self._should_fail:
            raise STTTranscriptionError("Local STT engine encountered internal transcription failure.")

        if self._hang_seconds > 0:
            await asyncio.sleep(self._hang_seconds)

        if not chunks:
            return SpeechTranscript(
                text="",
                confidence=0.0,
                language=language,
                duration_seconds=0.0,
                is_final=True,
            )

        total_bytes = b"".join(c.data for c in chunks)
        total_duration = sum(c.duration_seconds for c in chunks)

        # Check registered fixtures
        for marker, text in self._fixtures.items():
            if marker in total_bytes:
                return SpeechTranscript(
                    text=text,
                    confidence=0.98,
                    language=language,
                    duration_seconds=total_duration,
                    is_final=True,
                )

        # Decode embedded plaintext markers if audio payload contains ASCII markers
        try:
            for c in chunks:
                if b"TRANSCRIPT:" in c.data:
                    idx = c.data.find(b"TRANSCRIPT:")
                    extracted = c.data[idx + len(b"TRANSCRIPT:"):].decode("utf-8", errors="ignore").strip()
                    if extracted:
                        return SpeechTranscript(
                            text=extracted,
                            confidence=0.99,
                            language=language,
                            duration_seconds=total_duration,
                            is_final=True,
                        )
        except Exception:
            pass

        return SpeechTranscript(
            text=self._default_text,
            confidence=0.95,
            language=language,
            duration_seconds=total_duration,
            is_final=True,
        )


class LocalWhisperSTTProvider(BaseSTTProvider):
    """Local on-device Whisper model provider interface (runs locally via CPU/Metal/NEON)."""

    def __init__(self, model_size: str = "tiny.en") -> None:
        super().__init__(provider_name=f"local_whisper_{model_size}")
        self.model_size = model_size

    async def transcribe_chunks(
        self,
        chunks: list[AudioChunk],
        language: str = "en",
    ) -> SpeechTranscript:
        """Simulate local quantized model inference in memory."""
        if not chunks:
            return SpeechTranscript(text="", confidence=0.0, language=language)

        total_duration = sum(c.duration_seconds for c in chunks)
        return SpeechTranscript(
            text="Local voice command processed.",
            confidence=0.92,
            language=language,
            duration_seconds=total_duration,
            is_final=True,
        )
