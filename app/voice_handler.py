import asyncio
import audioop
import base64
import io
import json
import logging
import re
import wave
import httpx
from typing import Optional
from app.config import settings
from app.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

SARVAM_BASE_URL = "https://api.sarvam.ai"
EXOTEL_RATE     = 8000   # Exotel sends/receives 8 kHz PCM16

# VAD — manual activity detection
SPEECH_THRESHOLD  = 400  # RMS above this = speech
SILENCE_CHUNKS    = 15   # 15 × 20 ms = 300 ms silence → end of utterance
MIN_SPEECH_CHUNKS = 7   # 10 × 20 ms = 200 ms minimum — discards echo/noise bursts


class VoiceHandler:
    def __init__(self):
        self._in_queue:  asyncio.Queue = asyncio.Queue()   # complete utterance PCM bytes
        self._out_queue: asyncio.Queue = asyncio.Queue()   # PCM bytes → Exotel, or None to close
        self._closed  = False
        self._process_task: Optional[asyncio.Task] = None
        self._tts_playing = False   # True while TTS audio is playing back

        self.call_sid = None
        self.conversation_data = {
            "caller_name": None,
            "patient_id":  None,
            "reason":      None,
            "transcript":  []
        }
        self._conv_history = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self._patient_info_saved = False

        # Persistent HTTP client — one TCP+TLS connection reused for all Sarvam calls
        self._http = httpx.AsyncClient(
            base_url=SARVAM_BASE_URL,
            timeout=httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=5.0),
        )

        # VAD state
        self._speech_buffer: list = []
        self._silence_count: int  = 0
        self._is_speaking:   bool = False

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def start_session(self):
        """Queue greeting audio then start the STT→LLM→TTS processing loop."""
        self._process_task = asyncio.create_task(self._process_loop())
        await self._play_greeting()
        logger.info("Sarvam session ready")

    async def send_audio(self, audio_base64: str):
        """VAD-gate: buffer speech, queue complete utterances for processing.
        Ignores audio while TTS is playing to prevent echo false-positives."""
        try:
            if self._tts_playing:
                return

            pcm8k = base64.b64decode(audio_base64)
            rms   = audioop.rms(pcm8k, 2)   # 16-bit samples

            if rms > SPEECH_THRESHOLD:
                if not self._is_speaking:
                    self._is_speaking   = True
                    self._silence_count = 0
                    self._speech_buffer = []
                    logger.debug("VAD: speech detected")
                self._speech_buffer.append(pcm8k)

            elif self._is_speaking:
                self._silence_count += 1
                if self._silence_count >= SILENCE_CHUNKS:
                    chunks = self._speech_buffer[:]
                    self._speech_buffer = []
                    self._silence_count = 0
                    self._is_speaking   = False

                    if len(chunks) >= MIN_SPEECH_CHUNKS:
                        await self._in_queue.put(b"".join(chunks))
                        logger.info(f"VAD: utterance queued ({len(chunks)} chunks = {len(chunks)*20}ms)")
                    else:
                        logger.debug(f"VAD: utterance too short ({len(chunks)} chunks), discarded")

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
            "transcript_snippet": transcript_text[:500]
        }

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    async def _play_greeting(self):
        """Synthesize opening greeting and queue it; block until TTS is done."""
        greeting = "Thank you for calling. May I know the reason for your call?"
        # Sarvam LLM requires the first non-system message to be from "user".
        # We inject a silent trigger so the history is [system, user, assistant, ...].
        self._conv_history.append({"role": "user", "content": "[call connected]"})
        self._conv_history.append({"role": "assistant", "content": greeting})
        self.conversation_data["transcript"].append({"role": "assistant", "text": greeting})
        audio = await self._tts(greeting)
        if audio:
            # Schedule VAD block: greeting plays after start_session() returns,
            # so we fire a delayed unblock rather than sleeping here.
            self._tts_playing = True
            await self._out_queue.put(audio)
            asyncio.get_event_loop().call_later(
                len(audio) / 16000 + 1.0,   # duration + 1 s buffer
                lambda: setattr(self, "_tts_playing", False)
            )

    async def _process_loop(self):
        """Core loop: for each caller utterance → STT → LLM → TTS."""
        while not self._closed:
            try:
                audio_data = await asyncio.wait_for(self._in_queue.get(), timeout=1.0)
                if audio_data is None:
                    break

                # ── 1. Speech-to-Text ──────────────────────────────────────
                transcript = await self._stt(audio_data)
                if not transcript or not transcript.strip():
                    logger.warning("STT returned empty transcript, skipping")
                    continue

                logger.info(f"Caller: {transcript}")
                self.conversation_data["transcript"].append({"role": "user", "text": transcript})
                self._conv_history.append({"role": "user", "content": transcript})

                # ── 2. LLM ────────────────────────────────────────────────
                response_text = await self._llm()
                if not response_text:
                    continue

                # ── 3. Extract patient data (strips <PATIENT_DATA> marker) ─
                clean_text = self._extract_and_save(response_text)

                logger.info(f"Assistant: {clean_text[:120]}")
                self.conversation_data["transcript"].append({"role": "assistant", "text": clean_text})
                self._conv_history.append({"role": "assistant", "content": clean_text})

                # ── 4. Text-to-Speech ─────────────────────────────────────
                audio = await self._tts(clean_text)
                if audio:
                    self._tts_playing = True
                    await self._out_queue.put(audio)
                    await asyncio.sleep(len(audio) / 16000 + 0.3)
                    self._tts_playing = False

                # ── 5. Auto-close after goodbye ───────────────────────────
                if self._patient_info_saved:
                    logger.info("Goodbye complete — closing call")
                    await self._out_queue.put(None)
                    return

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"_process_loop error: {e}")

        await self._out_queue.put(None)

    def _extract_and_save(self, response_text: str) -> str:
        """Parse <PATIENT_DATA>…</PATIENT_DATA> from LLM output, save it, return clean text."""
        match = re.search(r"<PATIENT_DATA>(.*?)</PATIENT_DATA>", response_text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1).strip())
                self.conversation_data["caller_name"] = data.get("caller_name")
                self.conversation_data["patient_id"]  = data.get("patient_id") or None
                self.conversation_data["reason"]      = data.get("reason")
                self._patient_info_saved = True
                logger.info(f"Patient info saved: {data}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse patient data JSON: {e}")
            response_text = re.sub(
                r"<PATIENT_DATA>.*?</PATIENT_DATA>", "", response_text, flags=re.DOTALL
            ).strip()

        # Strip any leaked instruction markers like [On call start], [If YES], etc.
        response_text = re.sub(r"\[.*?\]", "", response_text).strip()
        # Collapse multiple spaces/newlines left by stripping
        response_text = re.sub(r"\s{2,}", " ", response_text).strip()
        return response_text

    # ── Sarvam API calls ─────────────────────────────────────────────── #

    async def _stt(self, audio_pcm8k: bytes) -> Optional[str]:
        """Transcribe PCM 8 kHz audio → text via Sarvam Saaras v3."""
        try:
            wav_bytes = self._pcm_to_wav(audio_pcm8k, EXOTEL_RATE)
            resp = await self._http.post(
                "/speech-to-text",
                headers={"api-subscription-key": settings.sarvam_api_key},
                files={"file": ("audio.wav", wav_bytes, "audio/wav")},
                data={"model": "saaras:v3", "language_code": "en-IN"},
            )
            resp.raise_for_status()
            return resp.json().get("transcript", "")
        except httpx.HTTPStatusError as e:
            logger.error(f"STT error {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"STT error: {e}")
            return None

    def _trimmed_history(self):
        """Keep system message + first user/assistant turn + last 6 messages.
        Limits token growth so LLM stays fast as conversation lengthens."""
        system = [m for m in self._conv_history if m["role"] == "system"]
        rest   = [m for m in self._conv_history if m["role"] != "system"]
        # Always keep the [call connected] seed + greeting (first 2 non-system messages)
        # plus the most recent 6 messages for context
        seed   = rest[:2]
        recent = rest[max(2, len(rest) - 6):]
        return system + seed + recent

    async def _llm(self) -> Optional[str]:
        """Get next assistant turn from Sarvam LLM."""
        try:
            resp = await self._http.post(
                "/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.sarvam_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "sarvam-30b",
                    "messages": self._trimmed_history(),
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM error {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return None

    async def _tts(self, text: str) -> Optional[bytes]:
        """Convert text → PCM 8 kHz via Sarvam Bulbul v3; returns raw PCM bytes."""
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
                    "speaker": "priya",   # bulbul:v3 female; options: ritu, neha, pooja, shruti, kavya
                    "model": "bulbul:v3",
                    "speech_sample_rate": 8000,
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

    # ── Audio utilities ──────────────────────────────────────────────── #

    @staticmethod
    def _pcm_to_wav(pcm_data: bytes, sample_rate: int) -> bytes:
        """Wrap raw PCM16 mono data in a WAV container."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)   # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)
        return buf.getvalue()

    @staticmethod
    def _wav_to_pcm(wav_bytes: bytes) -> bytes:
        """Extract raw PCM frames from a WAV container."""
        buf = io.BytesIO(wav_bytes)
        with wave.open(buf, "rb") as wf:
            return wf.readframes(wf.getnframes())
