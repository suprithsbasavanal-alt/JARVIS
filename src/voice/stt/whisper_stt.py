"""Whisper Speech-to-Text (STT) Engine Implementation (SOLID - SRP / LSP)."""

from src.voice.contracts.voice_engine import STTEngine, AudioChunk, TranscriptionResult
from src.shared.logger.logger import get_logger

logger = get_logger("voice.stt")


class WhisperSTTEngine(STTEngine):
    """Whisper Speech Recognition provider adapter."""

    def __init__(self, model_name: str = "whisper-1") -> None:
        self.model_name = model_name

    async def transcribe(self, audio: AudioChunk) -> TranscriptionResult:
        """Transcribes PCM audio chunk to text."""
        logger.info(f"Transcribing audio chunk ({len(audio.pcm_bytes)} bytes, {audio.sample_rate}Hz)...")

        # Mock transcription result for testing and simulation
        transcribed_text = "Jarvis, what is the current system status?"
        return TranscriptionResult(
            text=transcribed_text,
            confidence=0.98,
            language="en"
        )
