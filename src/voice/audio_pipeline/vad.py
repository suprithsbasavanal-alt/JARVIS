"""Voice Activity Detection (VAD) and Audio Stream Buffer."""

from typing import List, Optional
from src.voice.contracts.voice_engine import AudioChunk
from src.shared.logger.logger import get_logger

logger = get_logger("voice.audio_pipeline")


class AudioVADProcessor:
    """Voice Activity Detector processing incoming audio streams for speech segments."""

    def __init__(self, energy_threshold: float = 0.02) -> None:
        self.energy_threshold = energy_threshold
        self._buffer: List[bytes] = []

    def is_speech(self, chunk: AudioChunk) -> bool:
        """Determines whether audio chunk contains active speech energy."""
        if not chunk.pcm_bytes:
            return False
        # Calculate RMS energy of byte sample
        sample_sum = sum(abs(b - 128) for b in chunk.pcm_bytes)
        avg_energy = sample_sum / (len(chunk.pcm_bytes) * 128)
        return avg_energy >= self.energy_threshold

    def append_chunk(self, chunk: AudioChunk) -> None:
        """Appends chunk to active audio stream buffer."""
        self._buffer.append(chunk.pcm_bytes)

    def flush_buffer(self) -> Optional[AudioChunk]:
        """Flushes buffered audio bytes returning concatenated AudioChunk."""
        if not self._buffer:
            return None
        combined_bytes = b"".join(self._buffer)
        self._buffer.clear()
        return AudioChunk(
            pcm_bytes=combined_bytes,
            sample_rate=16000,
            channels=1
        )
