"""Voice Pipeline Coordinator."""

from voice.base import BaseSTTEngine, BaseTTSEngine, BaseWakeWordDetector


class MockWakeWordDetector(BaseWakeWordDetector):
    """Mock wake-word detector for safe Phase 0 development."""
    async def listen_for_wake_phrase(self) -> bool:
        return False


class MockSTTEngine(BaseSTTEngine):
    """Mock STT engine for safe Phase 0 development."""
    async def transcribe_audio_chunk(self, audio_bytes: bytes) -> str:
        return "[MOCK TRANSCRIPTION]"


class MockTTSEngine(BaseTTSEngine):
    """Mock TTS engine for safe Phase 0 development."""
    async def synthesize_speech(self, text: str) -> bytes:
        return b"[MOCK AUDIO BYTES]"


class VoicePipeline:
    """Orchestrates audio capture, wake detection, STT transcription, and TTS playback."""

    def __init__(
        self,
        wake_detector: BaseWakeWordDetector | None = None,
        stt_engine: BaseSTTEngine | None = None,
        tts_engine: BaseTTSEngine | None = None,
        is_enabled: bool = False,
    ) -> None:
        self.wake_detector = wake_detector or MockWakeWordDetector()
        self.stt_engine = stt_engine or MockSTTEngine()
        self.tts_engine = tts_engine or MockTTSEngine()
        self.is_enabled = is_enabled

    def enable(self) -> None:
        """Enable voice pipeline."""
        self.is_enabled = True

    def disable(self) -> None:
        """Disable voice pipeline."""
        self.is_enabled = False
