"""Base Types, Audio Data Containers, and Ephemeral Ring Buffers for Phase 5 Voice Pipeline."""

from collections import deque
from enum import Enum
import time
from typing import Any
from core.compat import BaseModel, Field
from core.exceptions import VoiceBufferOverflowError


class VoiceState(str, Enum):
    """Lifecycle states of the voice interaction state machine."""
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    SPEAKING = "SPEAKING"
    MUTED = "MUTED"
    ERROR = "ERROR"


class AudioFormat(str, Enum):
    """Supported PCM and container audio formats."""
    PCM_16BIT = "PCM_16BIT"
    PCM_FLOAT32 = "PCM_FLOAT32"
    WAV = "WAV"


class AudioChunk:
    """Ephemeral in-memory audio chunk container with zero disk persistence."""

    def __init__(
        self,
        data: bytes,
        sample_rate: int = 16000,
        channels: int = 1,
        audio_format: AudioFormat = AudioFormat.PCM_16BIT,
        timestamp_ms: float | None = None,
        is_speech: bool = True,
    ) -> None:
        self.data = data
        self.sample_rate = sample_rate
        self.channels = channels
        self.audio_format = audio_format
        self.timestamp_ms = timestamp_ms if timestamp_ms is not None else time.time() * 1000
        self.is_speech = is_speech

    @property
    def byte_length(self) -> int:
        return len(self.data)

    @property
    def duration_seconds(self) -> float:
        """Calculate duration based on 16-bit mono PCM bytes."""
        bytes_per_sample = 2 if self.audio_format == AudioFormat.PCM_16BIT else 4
        total_samples = len(self.data) / (bytes_per_sample * self.channels)
        return total_samples / max(self.sample_rate, 1)

    def __repr__(self) -> str:
        return (
            f"AudioChunk(bytes={len(self.data)}, rate={self.sample_rate}Hz, "
            f"dur={self.duration_seconds:.2f}s, is_speech={self.is_speech})"
        )


class AudioRingBuffer:
    """Bounded, in-memory FIFO ring buffer for streaming audio with strict memory bounds."""

    DEFAULT_MAX_BYTES = 5 * 1024 * 1024  # 5 MB max memory (~160s of 16kHz mono)

    def __init__(self, max_bytes: int = DEFAULT_MAX_BYTES) -> None:
        self.max_bytes = max_bytes
        self._chunks: deque[AudioChunk] = deque()
        self._current_bytes: int = 0

    @property
    def current_bytes(self) -> int:
        return self._current_bytes

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    def append(self, chunk: AudioChunk) -> None:
        """Append an audio chunk into the buffer. Drops oldest chunk if buffer exceeds max_bytes."""
        if not chunk or not chunk.data:
            return

        chunk_size = len(chunk.data)
        if chunk_size > self.max_bytes:
            raise VoiceBufferOverflowError(
                f"Single audio chunk size ({chunk_size} bytes) exceeds buffer capacity of {self.max_bytes} bytes."
            )

        # Evict oldest chunks if adding this chunk would exceed capacity
        while self._current_bytes + chunk_size > self.max_bytes and self._chunks:
            evicted = self._chunks.popleft()
            self._current_bytes -= len(evicted.data)

        self._chunks.append(chunk)
        self._current_bytes += chunk_size

    def get_all_bytes(self) -> bytes:
        """Concatenate all buffered PCM audio bytes."""
        return b"".join(c.data for c in self._chunks)

    def get_total_duration_seconds(self) -> float:
        """Compute cumulative duration of buffered chunks."""
        return sum(c.duration_seconds for c in self._chunks)

    def clear(self) -> None:
        """Securely wipe and clear ephemeral audio buffers from memory."""
        self._chunks.clear()
        self._current_bytes = 0
