# Voice Processing Module (`src/voice`)

## Purpose
Handles real-time audio input/output streams, Speech-to-Text (STT) transcription, Text-to-Speech (TTS) voice synthesis, and Voice Activity Detection (VAD).

## Architectural Layer
**Interface Adapter Layer**. Concrete implementations connect external audio models (Whisper, ElevenLabs, Deepgram, OS Native TTS) to domain audio stream abstractions.

## Subdirectories
- `contracts/`: Abstract Base Classes (`STTEngine`, `TTSEngine`, `AudioStreamContract`).
- `stt/`: Speech recognition provider adapters (Whisper, Deepgram).
- `tts/`: Speech synthesis provider adapters (ElevenLabs, Coqui, OS Native).
- `audio_pipeline/`: Real-time PCM audio streaming, VAD chunking, and buffer management.
