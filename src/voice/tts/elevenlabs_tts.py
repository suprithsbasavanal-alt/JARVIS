"""ElevenLabs Text-to-Speech (TTS) Engine Implementation."""

from typing import AsyncGenerator, Optional
from src.voice.contracts.voice_engine import TTSEngine, AudioChunk
from src.shared.logger.logger import get_logger

logger = get_logger("voice.tts")


class ElevenLabsTTSEngine(TTSEngine):
    """ElevenLabs voice synthesis provider adapter."""

    def __init__(self, voice_id: str = "default_jarvis_voice") -> None:
        self.default_voice_id = voice_id

    async def synthesize(self, text: str, voice_id: Optional[str] = None) -> AudioChunk:
        """Synthesizes text into audio PCM chunk."""
        target_voice = voice_id or self.default_voice_id
        logger.info(f"Synthesizing TTS for text '{text[:40]}...' using voice '{target_voice}'")

        pcm_simulated_bytes = text.encode("utf-8") * 10
        return AudioChunk(
            pcm_bytes=pcm_simulated_bytes,
            sample_rate=16000,
            channels=1,
            duration_ms=round(len(text) * 50.0, 2)
        )

    async def synthesize_stream(self, text: str) -> AsyncGenerator[AudioChunk, None]:
        """Streams audio PCM chunks in real-time."""
        words = text.split()
        for word in words:
            chunk = await self.synthesize(word)
            yield chunk
