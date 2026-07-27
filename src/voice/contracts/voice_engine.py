"""Abstract Base Classes for Voice Processing Engines (OCP / ISP)."""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
from pydantic import BaseModel


class AudioChunk(BaseModel):
    """Normalized audio frame data."""
    pcm_bytes: bytes
    sample_rate: int = 16000
    channels: int = 1
    duration_ms: float = 0.0


class TranscriptionResult(BaseModel):
    """Transcription text output from STT engine."""
    text: str
    confidence: float
    language: Optional[str] = None


class STTEngine(ABC):
    """Abstract Interface for Speech-to-Text Providers."""

    @abstractmethod
    async def transcribe(self, audio: AudioChunk) -> TranscriptionResult:
        """Transcribes audio chunk to text."""
        pass


class TTSEngine(ABC):
    """Abstract Interface for Text-to-Speech Providers."""

    @abstractmethod
    async def synthesize(self, text: str, voice_id: Optional[str] = None) -> AudioChunk:
        """Synthesizes text into audio PCM chunk."""
        pass

    @abstractmethod
    async def synthesize_stream(self, text: str) -> AsyncGenerator[AudioChunk, None]:
        """Streams audio chunks in real-time."""
        pass
