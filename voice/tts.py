"""Local Text-to-Speech (TTS) Synthesis Provider Abstraction for Phase 5."""

from abc import ABC, abstractmethod
import asyncio
import time
from typing import Any
from core.compat import BaseModel, Field
from core.exceptions import TTSSynthesisError
from voice.base import AudioChunk, AudioFormat


class SynthesizedAudio:
    """Container for synthesized audio output with zero disk persistence."""

    def __init__(
        self,
        audio_chunk: AudioChunk,
        character_count: int,
        synthesis_time_ms: float,
        voice_id: str = "en-jarvis-calm",
    ) -> None:
        self.audio_chunk = audio_chunk
        self.character_count = character_count
        self.synthesis_time_ms = synthesis_time_ms
        self.voice_id = voice_id

    @property
    def raw_pcm_bytes(self) -> bytes:
        return self.audio_chunk.data

    @property
    def duration_seconds(self) -> float:
        return self.audio_chunk.duration_seconds


class BaseTTSProvider(ABC):
    """Abstract interface for local on-device Text-to-Speech synthesis engines."""

    def __init__(self, provider_name: str = "base_tts") -> None:
        self.provider_name = provider_name

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: str = "en-jarvis-calm",
        speed: float = 1.0,
    ) -> SynthesizedAudio:
        """Synthesize input text into an ephemeral in-memory AudioChunk."""
        pass


class MockTTSProvider(BaseTTSProvider):
    """Deterministic mock TTS engine generating synthetic PCM waves in memory."""

    def __init__(self) -> None:
        super().__init__(provider_name="mock_tts_local")
        self._hang_seconds = 0.0
        self._should_fail = False
        self._last_spoken_text = ""

    def set_hang_timeout(self, seconds: float) -> None:
        self._hang_seconds = seconds

    def set_failure_mode(self, fail: bool) -> None:
        self._should_fail = fail

    @property
    def last_spoken_text(self) -> str:
        return self._last_spoken_text

    async def synthesize(
        self,
        text: str,
        voice_id: str = "en-jarvis-calm",
        speed: float = 1.0,
    ) -> SynthesizedAudio:
        """Synthesize audio bytes deterministically without network communication."""
        if self._should_fail:
            raise TTSSynthesisError("Local TTS engine synthesis error.")

        if self._hang_seconds > 0:
            await asyncio.sleep(self._hang_seconds)

        clean_text = (text or "").strip()
        self._last_spoken_text = clean_text

        start_time = time.time()

        # Generate synthetic PCM 16-bit audio frames (e.g. 50ms per character of text)
        sample_rate = 16000
        # Estimate duration: ~0.06 seconds per character, minimum 0.5s
        duration = max(0.5, len(clean_text) * 0.06)
        total_samples = int(sample_rate * duration)
        # 16-bit mono PCM = 2 bytes per sample (silence/tone buffer)
        pcm_bytes = b"\x00\x00" * total_samples

        chunk = AudioChunk(
            data=pcm_bytes,
            sample_rate=sample_rate,
            channels=1,
            audio_format=AudioFormat.PCM_16BIT,
        )

        synthesis_ms = (time.time() - start_time) * 1000

        return SynthesizedAudio(
            audio_chunk=chunk,
            character_count=len(clean_text),
            synthesis_time_ms=synthesis_ms,
            voice_id=voice_id,
        )


class LocalPiperTTSProvider(BaseTTSProvider):
    """Local on-device neural TTS provider abstraction (Piper / macOS AVFoundation)."""

    def __init__(self, voice_model: str = "en_US-lessac-medium") -> None:
        super().__init__(provider_name=f"local_piper_{voice_model}")
        self.voice_model = voice_model

    async def synthesize(
        self,
        text: str,
        voice_id: str = "en-jarvis-calm",
        speed: float = 1.0,
    ) -> SynthesizedAudio:
        """Simulate on-device neural synthesis."""
        clean_text = text.strip()
        sample_rate = 22050
        duration = max(0.5, len(clean_text) * 0.05)
        pcm_bytes = b"\x00\x00" * int(sample_rate * duration)

        chunk = AudioChunk(
            data=pcm_bytes,
            sample_rate=sample_rate,
            channels=1,
            audio_format=AudioFormat.PCM_16BIT,
        )

        return SynthesizedAudio(
            audio_chunk=chunk,
            character_count=len(clean_text),
            synthesis_time_ms=12.5,
            voice_id=voice_id,
        )
