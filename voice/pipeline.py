"""Voice Pipeline Orchestrator and State Machine for Phase 5."""

import asyncio
import time
from typing import Any, Callable
from agents.loop import AgentLoop
from agents.sanitizer import InputSanitizer
from config.schema import PermissionLevel
from core.context import SessionContext
from core.exceptions import (
    STTTranscriptionError,
    TTSSynthesisError,
    VoiceBufferOverflowError,
    VoicePermissionDeniedError,
    VoiceTimeoutError,
    WakeWordDetectionError,
)
from security.audit_logger import AuditLogger
from security.permissions import PermissionEngine
from voice.base import AudioChunk, AudioRingBuffer, VoiceState
from voice.stt import BaseSTTProvider, MockSTTProvider, SpeechTranscript
from voice.tts import BaseTTSProvider, MockTTSProvider, SynthesizedAudio
from voice.wake_word import BaseWakeWordDetector, MockWakeWordDetector


class VoiceTurnResult:
    """Structured container for the output of an end-to-end voice turn."""

    def __init__(
        self,
        wake_word_detected: bool,
        transcript: SpeechTranscript | None = None,
        agent_response_text: str | None = None,
        synthesized_audio: SynthesizedAudio | None = None,
        duration_seconds: float = 0.0,
        is_success: bool = True,
        error_message: str | None = None,
    ) -> None:
        self.wake_word_detected = wake_word_detected
        self.transcript = transcript
        self.agent_response_text = agent_response_text
        self.synthesized_audio = synthesized_audio
        self.duration_seconds = duration_seconds
        self.is_success = is_success
        self.error_message = error_message


class VoicePipeline:
    """Manages the lifecycle of on-device voice processing with strict privacy invariants."""

    DEFAULT_LISTEN_TIMEOUT_SECONDS = 10.0
    DEFAULT_PROCESSING_TIMEOUT_SECONDS = 5.0

    def __init__(
        self,
        wake_detector: BaseWakeWordDetector | None = None,
        stt_provider: BaseSTTProvider | None = None,
        tts_provider: BaseTTSProvider | None = None,
        agent_loop: AgentLoop | None = None,
        audit_logger: AuditLogger | None = None,
        permission_engine: PermissionEngine | None = None,
        ring_buffer: AudioRingBuffer | None = None,
    ) -> None:
        self.wake_detector = wake_detector or MockWakeWordDetector()
        self.stt_provider = stt_provider or MockSTTProvider()
        self.tts_provider = tts_provider or MockTTSProvider()
        self.agent_loop = agent_loop
        self.audit_logger = audit_logger or AuditLogger()
        self.permission_engine = permission_engine or PermissionEngine()
        self.ring_buffer = ring_buffer or AudioRingBuffer()
        self._state = VoiceState.IDLE
        self._is_running = True

    @property
    def current_state(self) -> VoiceState:
        return self._state

    def reset_state(self) -> None:
        """Reset pipeline state and clear all audio buffers from RAM."""
        self._state = VoiceState.IDLE
        self.ring_buffer.clear()
        self.wake_detector.reset()

    def shutdown(self) -> None:
        """Gracefully shut down voice pipeline and clear buffers."""
        self._is_running = False
        self.reset_state()

    def _verify_permissions(self, context: SessionContext) -> None:
        """Enforce that voice interaction is permitted under active security policy."""
        if context.permission_level == PermissionLevel.LOCKED:
            self.audit_logger.log(
                actor_id=str(context.session_id),
                session_id=str(context.session_id),
                event_type="VOICE_PERMISSION_DENIED",
                action_type="voice_interaction",
                risk_level="HIGH",
                target_resource="microphone",
                parameters={"reason": "PermissionLevel.LOCKED"},
                decision="DENIED",
            )
            raise VoicePermissionDeniedError("Voice pipeline interaction is disabled under LOCKED permission tier.")

    async def process_audio_chunk(
        self,
        chunk: AudioChunk,
        context: SessionContext,
    ) -> bool:
        """Process an incoming audio chunk in the stream.

        Returns True if wake-word is detected or if state is currently LISTENING.
        """
        if not self._is_running:
            return False

        self._verify_permissions(context)

        # 1. State: IDLE -> check for wake word
        if self._state == VoiceState.IDLE:
            detected = await self.wake_detector.process_frame(chunk)
            if detected:
                self._state = VoiceState.LISTENING
                self.audit_logger.log(
                    actor_id=str(context.session_id),
                    session_id=str(context.session_id),
                    event_type="WAKE_WORD_DETECTED",
                    action_type="wake_word_detection",
                    risk_level="LOW",
                    target_resource="local_microphone",
                    parameters={"wake_word": self.wake_detector.wake_word},
                    decision="AUTHORIZED",
                )
                return True
            return False

        # 2. State: LISTENING -> buffer incoming speech chunks
        if self._state == VoiceState.LISTENING:
            self.ring_buffer.append(chunk)
            return True

        return False

    async def execute_voice_turn(
        self,
        audio_stream: list[AudioChunk],
        context: SessionContext,
        timeout_seconds: float = DEFAULT_PROCESSING_TIMEOUT_SECONDS,
    ) -> VoiceTurnResult:
        """Execute a complete voice turn: WakeWord -> STT -> AgentLoop -> TTS.

        Zero audio is persisted to disk; audio buffers are securely cleared after processing.
        """
        self._verify_permissions(context)
        start_time = time.time()
        self.reset_state()

        try:
            return await asyncio.wait_for(
                self._execute_voice_turn_internal(audio_stream, context),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError as err:
            self.reset_state()
            self.audit_logger.log(
                actor_id=str(context.session_id),
                session_id=str(context.session_id),
                event_type="VOICE_TIMEOUT",
                action_type="voice_turn",
                risk_level="MEDIUM",
                target_resource="voice_pipeline",
                parameters={"timeout_seconds": timeout_seconds},
                decision="ABORTED",
            )
            raise VoiceTimeoutError(f"Voice turn processing timed out after {timeout_seconds}s.") from err
        except Exception as err:
            self.reset_state()
            raise err

    async def _execute_voice_turn_internal(
        self,
        audio_stream: list[AudioChunk],
        context: SessionContext,
    ) -> VoiceTurnResult:
        """Internal voice execution logic."""
        # 1. Detect Wake Word
        wake_detected = False
        speech_chunks: list[AudioChunk] = []

        for chunk in audio_stream:
            if not wake_detected:
                if await self.wake_detector.process_frame(chunk):
                    wake_detected = True
                    self._state = VoiceState.LISTENING
            else:
                speech_chunks.append(chunk)
                self.ring_buffer.append(chunk)

        if not wake_detected:
            self.reset_state()
            return VoiceTurnResult(
                wake_word_detected=False,
                is_success=True,
                error_message="Wake word not detected in audio stream.",
            )

        self.audit_logger.log(
            actor_id=str(context.session_id),
            session_id=str(context.session_id),
            event_type="WAKE_WORD_DETECTED",
            action_type="wake_word_detection",
            risk_level="LOW",
            target_resource="local_microphone",
            parameters={"wake_word": self.wake_detector.wake_word},
            decision="AUTHORIZED",
        )

        # 2. Transition to PROCESSING & Perform Local STT
        self._state = VoiceState.PROCESSING
        raw_chunks = list(self.ring_buffer._chunks)
        transcript = await self.stt_provider.transcribe_chunks(raw_chunks)

        # 3. Log STT Event (Zero raw audio recorded, metadata only)
        self.audit_logger.log(
            actor_id=str(context.session_id),
            session_id=str(context.session_id),
            event_type="STT_TRANSCRIPTION_COMPLETED",
            action_type="speech_to_text",
            risk_level="LOW",
            target_resource="local_stt_engine",
            parameters={
                "char_count": len(transcript.text),
                "duration_seconds": transcript.duration_seconds,
                "confidence": transcript.confidence,
                "language": transcript.language,
            },
            decision="SUCCESS",
        )

        # 4. Sanitize Transcribed User Speech to Neutralize Injected Prompts
        sanitized_input = InputSanitizer.sanitize_user_input(transcript.text)

        # 5. Core Agent Loop Processing (if connected)
        agent_response_text = "Command executed successfully."
        if self.agent_loop:
            agent_res = await self.agent_loop.process_turn(sanitized_input, context)
            agent_response_text = agent_res.content or agent_response_text

        # 6. Local TTS Audio Synthesis
        self._state = VoiceState.SPEAKING
        synthesized = await self.tts_provider.synthesize(agent_response_text)

        # 7. Log TTS Event (Zero raw audio recorded, metadata only)
        self.audit_logger.log(
            actor_id=str(context.session_id),
            session_id=str(context.session_id),
            event_type="TTS_SYNTHESIS_COMPLETED",
            action_type="text_to_speech",
            risk_level="LOW",
            target_resource="local_tts_engine",
            parameters={
                "char_count": synthesized.character_count,
                "duration_seconds": synthesized.duration_seconds,
                "synthesis_time_ms": synthesized.synthesis_time_ms,
                "voice_id": synthesized.voice_id,
            },
            decision="SUCCESS",
        )

        # 8. Clean up and return to IDLE state
        total_duration = time.time() - (self.ring_buffer._chunks[0].timestamp_ms / 1000 if self.ring_buffer._chunks else time.time())
        self.reset_state()

        return VoiceTurnResult(
            wake_word_detected=True,
            transcript=transcript,
            agent_response_text=agent_response_text,
            synthesized_audio=synthesized,
            duration_seconds=total_duration,
            is_success=True,
        )
