"""Unit Test Suite for Voice Component."""

import pytest
from src.voice import (
    WhisperSTTEngine,
    ElevenLabsTTSEngine,
    AudioVADProcessor,
    AudioChunk,
)


@pytest.mark.asyncio
async def test_whisper_stt_engine():
    """Verifies Whisper STT engine transcription."""
    stt = WhisperSTTEngine()
    audio = AudioChunk(pcm_bytes=b"sample_pcm_data_12345", sample_rate=16000)

    result = await stt.transcribe(audio)
    assert result.confidence > 0.9
    assert "Jarvis" in result.text
    assert result.language == "en"


@pytest.mark.asyncio
async def test_elevenlabs_tts_engine():
    """Verifies ElevenLabs TTS engine synthesis and streaming generator."""
    tts = ElevenLabsTTSEngine()

    # Single Synthesis
    audio_chunk = await tts.synthesize("Hello world")
    assert len(audio_chunk.pcm_bytes) > 0
    assert audio_chunk.sample_rate == 16000

    # Stream Synthesis
    chunks = []
    async for chunk in tts.synthesize_stream("Jarvis online"):
        chunks.append(chunk)

    assert len(chunks) == 2  # Two words: 'Jarvis', 'online'


def test_audio_vad_processor():
    """Verifies Voice Activity Detector (VAD) energy detection and buffer flushing."""
    vad = AudioVADProcessor(energy_threshold=0.01)

    empty_chunk = AudioChunk(pcm_bytes=b"")
    assert vad.is_speech(empty_chunk) is False

    speech_bytes = bytes([200] * 50)
    speech_chunk = AudioChunk(pcm_bytes=speech_bytes)

    assert vad.is_speech(speech_chunk) is True

    vad.append_chunk(speech_chunk)
    flushed = vad.flush_buffer()
    assert flushed is not None
    assert len(flushed.pcm_bytes) == 50

    assert vad.flush_buffer() is None
