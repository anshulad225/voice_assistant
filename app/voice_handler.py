import asyncio
import audioop
import base64
import io
import logging
import re
import wave
import httpx
from enum import Enum
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

SARVAM_BASE_URL = "https://api.sarvam.ai"
EXOTEL_RATE = 16000  # Exotel sends/receives 16 kHz PCM16

# VAD
SPEECH_THRESHOLD  = 400  # RMS above this = speech
SILENCE_CHUNKS    = 20   # 20 × 20 ms = 400 ms silence → end of utterance
MIN_SPEECH_CHUNKS = 3    # 3 × 20 ms = 60 ms minimum
                         # was 7 (140 ms) — short words like "no" / "na" only
                         # produce 3-5 chunks and were being silently discarded

# Post-TTS silence guard: extra seconds to keep ignoring mic AFTER audio duration.
#
# Why this exists: Exotel buffers + plays our audio, then the caller's mic can
# pick up acoustic echo of that audio. We block inbound audio for
# (audio_duration + TTS_ECHO_GUARD) to prevent that echo from hitting STT.
TTS_ECHO_GUARD = 0.8     # seconds — 0.5 caused echo capture, 1.2 blocked "no"

# Call-level timeout: hang up gracefully if no completion within this many seconds.
CALL_TIMEOUT_SECS = 120

# ── Intent keyword sets ───────────────────────────────────────────────────────
# Removed "ha", "ho", "hua", "ok", "ji" — Sarvam transcribes background noise
# and partial syllables as these short tokens, causing false "yes" detections.
YES_WORDS = {
    "yes", "yeah", "yep", "yup", "okay", "sure", "correct",
    "right", "haan", "haa", "bilkul", "theek", "sahi",
}
NO_WORDS = {
    "no", "nope", "nah", "nahi", "nahin", "na", "naa", "mat",
    "wrong", "incorrect", "9",   # "9" — Sarvam translates "no" → "9" (nau/नौ homophone)
}


def _match_intent(text: str) -> Optional[str]:
    """
    Return 'yes', 'no', or None from a raw STT transcript.

    Uses re.findall to strip punctuation before matching so that
    transcripts like "no." / "nahi," / "Yes!" all match correctly.
    """
    text_lower = text.lower().strip()
    tokens = set(re.findall(r"[a-z0-9]+", text_lower))
    logger.info(f"intent tokens: {tokens}  (raw: {text_lower!r})")

    for w in YES_WORDS:
        if w in tokens:
            return "yes"
    for w in NO_WORDS:
        if w in tokens:
            return "no"
    return None


# ── Conversation states ───────────────────────────────────────────────────────
class _State(Enum):
    WAIT_REASON     = "wait_reason"
    WAIT_EXISTING   = "wait_existing"
    WAIT_PATIENT_ID = "wait_patient_id"
    WAIT_NAME       = "wait_name"
    WAIT_CONFIRM    = "wait_confirm"
    DONE            = "done"


class VoiceHandler:
    def __init__(self):
        self._in_queue:  asyncio.Queue = asyncio.Queue()
        self._out_queue: asyncio.Queue = asyncio.Queue()
        self._closed   = False
        self._process_task: Optional[asyncio.Task] = None
        self._tts_playing = False

        self.call_sid = None
        self.conversation_data = {
            "caller_name": None,
            "patient_id":  None,
            "reason":      None,
            "transcript":  [],
        }
        self._patient_info_saved = False

        # State machine
        self._state: _State       = _State.WAIT_REASON
        self._is_existing: Optional[bool] = None

        # Persistent HTTP client — one TCP+TLS connection reused for all Sarvam calls
        self._http = httpx.AsyncClient(
            base_url=SARVAM_BASE_URL,
            timeout=httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=5.0),
        )

        # VAD state
        self._speech_buffer: list = []
        self._silence_count: int  = 0
        self._is_speaking:   bool = False

    # ── Public API ────────────────────────────────────────────────────────────

    async def start_session(self):
        """Queue greeting audio then start the STT → state-machine → TTS loop."""
        self._process_task = asyncio.create_task(self._process_loop())
        await self._play_greeting()
        logger.info("Sarvam STT + keyword-matching session ready")

    async def send_audio(self, audio_base64: str):
        """VAD-gate: buffer speech, queue complete utterances for processing.
        Ignores audio while TTS is playing to prevent echo false-positives."""
        try:
            if self._tts_playing:
                return

            pcm = base64.b64decode(audio_base64)
            rms  = audioop.rms(pcm, 2)

            if rms > SPEECH_THRESHOLD:
                if not self._is_speaking:
                    self._is_speaking   = True
                    self._silence_count = 0
                    self._speech_buffer = []
                    logger.debug("VAD: speech detected")
                self._speech_buffer.append(pcm)

            elif self._is_speaking:
                self._silence_count += 1
                if self._silence_count >= SILENCE_CHUNKS:
                    chunks = self._speech_buffer[:]
                    self._speech_buffer = []
                    self._silence_count = 0
                    self._is_speaking   = False

                    if len(chunks) >= MIN_SPEECH_CHUNKS:
                        await self._in_queue.put(b"".join(chunks))
                        logger.info(
                            f"VAD: utterance queued "
                            f"({len(chunks)} chunks = {len(chunks)*20}ms)"
                        )
                    else:
                        logger.debug(
                            f"VAD: utterance too short "
                            f"({len(chunks)} chunks), discarded"
                        )
        except Exception as e:
            logger.error(f"send_audio error: {e}")

    async def get_response_audio(self) -> Optional[bytes]:
        return await self._out_queue.get()

    async def close(self):
        self._closed = True
        await self._in_queue.put(None)
        if self._process_task:
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass
        await self._http.aclose()
        logger.info("Voice handler closed")

    def get_summary(self) -> dict:
        transcript_text = "\n".join(
            f"{t['role']}: {t['text']}" for t in self.conversation_data["transcript"]
        )
        return {
            "caller_name":        self.conversation_data.get("caller_name"),
            "patient_id":         self.conversation_data.get("patient_id"),
            "reason":             self.conversation_data.get("reason") or "Not specified",
            "transcript_snippet": transcript_text[:500],
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _reset_vad(self):
        """Clear VAD state so no stale speech fires after TTS ends."""
        self._speech_buffer = []
        self._silence_count = 0
        self._is_speaking   = False

    def _drain_queue(self):
        """Discard any utterances queued while we were busy (STT + TTS time)."""
        drained = 0
        while not self._in_queue.empty():
            try:
                self._in_queue.get_nowait()
                drained += 1
            except asyncio.QueueEmpty:
                break
        if drained:
            logger.info(f"Drained {drained} stale utterance(s) from queue")

    async def _play_greeting(self):
        """Synthesize opening greeting and queue it."""
        greeting = "Thank you for calling. May I know the reason for your call?"
        self.conversation_data["transcript"].append(
            {"role": "assistant", "text": greeting}
        )
        audio = await self._tts(greeting)
        if audio:
            self._reset_vad()
            self._tts_playing = True
            await self._out_queue.put(audio)
            asyncio.get_running_loop().call_later(
                len(audio) / 32000 + TTS_ECHO_GUARD,
                self._finish_tts,
            )

    def _finish_tts(self):
        """Called by call_later after greeting TTS finishes. Unblocks VAD and drains queue."""
        self._drain_queue()
        self._tts_playing = False

    async def _process_loop(self):
        """Core loop: utterance → Sarvam STT → state machine → Sarvam TTS."""
        deadline = asyncio.get_running_loop().time() + CALL_TIMEOUT_SECS

        while not self._closed:
            try:
                # Enforce call-level timeout
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    logger.warning("Call timeout — closing")
                    await self._out_queue.put(None)
                    return

                audio_data = await asyncio.wait_for(
                    self._in_queue.get(),
                    timeout=min(1.0, remaining),
                )
                if audio_data is None:
                    break

                # ── 1. Speech-to-Text (Sarvam Saaras v3) — retry once ─────────
                transcript = await self._stt(audio_data)
                if not transcript or not transcript.strip():
                    logger.warning("STT returned empty, retrying once")
                    transcript = await self._stt(audio_data)
                if not transcript or not transcript.strip():
                    logger.warning("STT failed twice, skipping utterance")
                    continue

                logger.info(f"Caller [{self._state.value}]: {transcript}")
                self.conversation_data["transcript"].append(
                    {"role": "user", "text": transcript}
                )

                # ── 2. State machine (no LLM) ─────────────────────────────────
                response_text = self._advance_state(transcript)
                if not response_text:
                    continue

                logger.info(f"Assistant: {response_text[:120]}")
                self.conversation_data["transcript"].append(
                    {"role": "assistant", "text": response_text}
                )

                # ── 3. Text-to-Speech — retry once on failure ─────────────────
                audio = await self._tts(response_text)
                if not audio:
                    logger.warning("TTS failed, retrying once")
                    audio = await self._tts(response_text)

                if audio:
                    self._reset_vad()
                    self._tts_playing = True
                    await self._out_queue.put(audio)
                    await asyncio.sleep(len(audio) / 32000 + TTS_ECHO_GUARD)
                    self._drain_queue()
                    self._tts_playing = False
                else:
                    logger.error("TTS failed twice — caller will hear silence")

                # ── 4. Auto-close after goodbye ───────────────────────────────
                if self._patient_info_saved:
                    logger.info("Goodbye complete — closing call")
                    await self._out_queue.put(None)
                    return

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"_process_loop error: {e}")

        await self._out_queue.put(None)

    def _advance_state(self, transcript: str) -> str:
        """
        Pure state machine — no LLM, no cloud inference.
        Returns the text to speak next, or '' to stay silent.
        Raw Sarvam STT transcript is stored as-is for name and reason.
        """
        t = transcript.strip()

        if self._state == _State.WAIT_REASON:
            self.conversation_data["reason"] = t
            self._state = _State.WAIT_EXISTING
            return "Are you an existing patient with us? Please say yes or no."

        if self._state == _State.WAIT_EXISTING:
            intent = _match_intent(t)
            if intent == "yes":
                self._is_existing = True
                self._state = _State.WAIT_PATIENT_ID
                return "May I have your patient ID please?"
            if intent == "no":
                self._is_existing = False
                self._state = _State.WAIT_NAME
                return "May I have your full name please?"
            return "I'm sorry, I didn't catch that. Please say yes or no."

        if self._state == _State.WAIT_PATIENT_ID:
            self.conversation_data["patient_id"] = t
            self._state = _State.WAIT_NAME
            return "And your full name please?"

        if self._state == _State.WAIT_NAME:
            self.conversation_data["caller_name"] = t
            self._state = _State.WAIT_CONFIRM
            patient_type = "an existing patient" if self._is_existing else "a new patient"
            return (
                f"Just to confirm — your name is {t}, "
                f"you are calling about {self.conversation_data['reason']}, "
                f"and you are {patient_type}. Is that correct?"
            )

        if self._state == _State.WAIT_CONFIRM:
            intent = _match_intent(t)
            if intent == "yes":
                self._patient_info_saved = True
                self._state = _State.DONE
                name = self.conversation_data.get("caller_name", "")
                return (
                    f"Thank you {name}. "
                    "Someone from our team will call you back shortly. "
                    "Have a great day, goodbye!"
                )
            if intent == "no":
                self.conversation_data["reason"]      = None
                self.conversation_data["caller_name"] = None
                self.conversation_data["patient_id"]  = None
                self._is_existing = None
                self._state = _State.WAIT_REASON
                return (
                    "I apologize, let me get that right. "
                    "May I know the reason for your call?"
                )
            return "I'm sorry, could you please say yes or no?"

        return ""

    # ── Sarvam STT ────────────────────────────────────────────────────────────

    async def _stt(self, audio_pcm: bytes) -> Optional[str]:
        """Transcribe PCM 16 kHz audio → text via Sarvam Saaras v3."""
        try:
            wav_bytes = self._pcm_to_wav(audio_pcm, EXOTEL_RATE)
            resp = await self._http.post(
                "/speech-to-text",
                headers={"api-subscription-key": settings.sarvam_api_key},
                files={"file": ("audio.wav", wav_bytes, "audio/wav")},
                data={"model": "saaras:v3", "language_code": "en-IN"},
            )
            resp.raise_for_status()
            transcript = resp.json().get("transcript", "")
            logger.info(f"STT raw transcript: {transcript!r}")
            return transcript
        except httpx.HTTPStatusError as e:
            logger.error(f"STT error {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"STT error: {e}")
            return None

    # ── Sarvam TTS ────────────────────────────────────────────────────────────

    async def _tts(self, text: str) -> Optional[bytes]:
        """Convert text → PCM 16 kHz via Sarvam Bulbul v3; returns raw PCM bytes."""
        try:
            resp = await self._http.post(
                "/text-to-speech",
                headers={
                    "api-subscription-key": settings.sarvam_api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "target_language_code": "en-IN",
                    "speaker": "priya",
                    "model": "bulbul:v3",
                    "speech_sample_rate": 16000,
                    "pace": 1.0,
                },
            )
            resp.raise_for_status()
            audios = resp.json().get("audios", [])
            if audios:
                wav_bytes = base64.b64decode(audios[0])
                return self._wav_to_pcm(wav_bytes)
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"TTS error {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None

    # ── Audio utilities ───────────────────────────────────────────────────────

    @staticmethod
    def _pcm_to_wav(pcm_data: bytes, sample_rate: int) -> bytes:
        """Wrap raw PCM16 mono data in a WAV container."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)
        return buf.getvalue()

    @staticmethod
    def _wav_to_pcm(wav_bytes: bytes) -> bytes:
        """Extract raw PCM frames from a WAV container."""
        buf = io.BytesIO(wav_bytes)
        with wave.open(buf, "rb") as wf:
            return wf.readframes(wf.getnframes())
