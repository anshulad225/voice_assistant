import asyncio
import audioop
import base64
import logging
from typing import Optional

import google.genai as genai
from google.genai import types

from app.config import settings
from app.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

TELEPHONY_RATE = 8000    # Telephony sends/receives 8 kHz PCM16
GEMINI_IN_RATE = 16000   # Gemini Live input: 16 kHz PCM16
GEMINI_OUT_RATE = 24000  # Gemini Live output: 24 kHz PCM16 (default)

SAVE_PATIENT_DATA_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="save_patient_data",
            description=(
                "Save the patient's information after the caller has confirmed it. "
                "Call this ONLY once, immediately after the caller says YES to the confirmation."
            ),
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "caller_name": types.Schema(
                        type="STRING",
                        description="Full name of the caller, exactly as heard.",
                    ),
                    "reason": types.Schema(
                        type="STRING",
                        description="Reason for calling, in the caller's own words.",
                    ),
                    "patient_id": types.Schema(
                        type="STRING",
                        description="Patient ID if existing patient, empty string if new.",
                    ),
                },
                required=["caller_name", "reason", "patient_id"],
            ),
        )
    ]
)


class VoiceHandler:
    def __init__(self):
        self._out_queue: asyncio.Queue = asyncio.Queue()
        self._closed = False
        self._session_broken = False   # set when the Gemini WebSocket is unrecoverable
        self._context = None
        self._session = None
        self._recv_task: Optional[asyncio.Task] = None
        self._ratecv_state = None      # audioop state for input upsampling

        self.call_sid = None
        self.conversation_data = {
            "caller_name": None,
            "patient_id": None,
            "reason": None,
            "transcript": [],
        }
        self._patient_info_saved = False
        self._client = genai.Client(api_key=settings.google_api_key)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def start_session(self):
        """Open Gemini Live session and start the receive loop."""
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=SYSTEM_PROMPT,
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
                )
            ),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            tools=[SAVE_PATIENT_DATA_TOOL],
        )

        self._context = self._client.aio.live.connect(
            model="gemini-2.5-flash-native-audio-preview-12-2025",
            config=config,
        )
        self._session = await self._context.__aenter__()
        self._recv_task = asyncio.create_task(self._receive_loop())

        # Trigger the greeting
        await self._session.send(input="[call connected]", end_of_turn=True)
        logger.info("Gemini Live session started")

    async def send_audio(self, audio_base64: str):
        """Resample and send a PCM-8kHz chunk directly to Gemini."""
        if self._closed or self._session_broken or self._session is None:
            return
        try:
            pcm8k = base64.b64decode(audio_base64)
            pcm16k, self._ratecv_state = audioop.ratecv(
                pcm8k, 2, 1, TELEPHONY_RATE, GEMINI_IN_RATE, self._ratecv_state
            )
            await self._session.send_realtime_input(
                audio=types.Blob(data=pcm16k, mime_type=f"audio/pcm;rate={GEMINI_IN_RATE}")
            )
        except Exception as e:
            logger.error(f"send_audio error: {e}")
            self._session_broken = True

    async def get_response_audio(self) -> Optional[bytes]:
        """Block until a PCM-8kHz chunk is ready; None signals end of call."""
        return await self._out_queue.get()

    async def close(self):
        self._closed = True
        if self._recv_task:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass
        if self._context is not None:
            try:
                await self._context.__aexit__(None, None, None)
            except Exception:
                pass
        logger.info("Voice handler closed")

    def get_summary(self) -> dict:
        transcript_text = "\n".join(
            f"{t['role']}: {t['text']}" for t in self.conversation_data["transcript"]
        )
        return {
            "caller_name": self.conversation_data.get("caller_name"),
            "patient_id": self.conversation_data.get("patient_id"),
            "reason": self.conversation_data.get("reason") or "Not specified",
            "transcript_snippet": transcript_text[:500],
        }

    # ------------------------------------------------------------------ #
    # Internal receive loop                                                #
    # ------------------------------------------------------------------ #

    async def _receive_loop(self):
        """
        Receive audio, transcriptions, and tool calls from Gemini.

        Design notes:
        - session.receive() yields ONE complete turn then exhausts → outer while restarts it.
        - Per-message exceptions are caught inside the loop so one bad message
          does not kill the session.
        - APIError (WebSocket close / network error) is caught at the turn level;
          we retry up to MAX_RETRIES times with a short back-off before giving up.
        - go_away is handled gracefully — it means Gemini wants us to reconnect,
          so we treat it as a non-fatal end and close cleanly.
        """
        out_rate_state = None
        MAX_RETRIES = 3
        retry_count = 0

        try:
            while not self._closed:
                try:
                    async for msg in self._session.receive():
                        if self._closed:
                            return
                        retry_count = 0  # successful message resets retry counter

                        # ── go_away: Gemini wants to close the session ────────
                        if msg.go_away is not None:
                            logger.warning("Gemini sent go_away — closing gracefully")
                            await self._out_queue.put(None)
                            return

                        sc = msg.server_content
                        if sc:
                            # ── Audio chunks ──────────────────────────────────
                            if sc.model_turn and sc.model_turn.parts:
                                for part in sc.model_turn.parts:
                                    if not (part.inline_data and part.inline_data.data):
                                        continue
                                    try:
                                        out_rate = GEMINI_OUT_RATE
                                        if part.inline_data.mime_type and "rate=" in part.inline_data.mime_type:
                                            out_rate = int(
                                                part.inline_data.mime_type
                                                .split("rate=")[1].split(";")[0]
                                            )
                                        pcm8k, out_rate_state = audioop.ratecv(
                                            part.inline_data.data, 2, 1,
                                            out_rate, TELEPHONY_RATE, out_rate_state,
                                        )
                                        await self._out_queue.put(pcm8k)
                                    except Exception as e:
                                        logger.error(f"Audio resample error: {e}")

                            # ── Output transcription ──────────────────────────
                            if sc.output_transcription and sc.output_transcription.text:
                                text = sc.output_transcription.text.strip()
                                if text:
                                    logger.info(f"Assistant: {text[:120]}")
                                    self.conversation_data["transcript"].append(
                                        {"role": "assistant", "text": text}
                                    )

                            # ── Input transcription ───────────────────────────
                            if sc.input_transcription and sc.input_transcription.text:
                                text = sc.input_transcription.text.strip()
                                if text:
                                    logger.info(f"Caller: {text[:120]}")
                                    self.conversation_data["transcript"].append(
                                        {"role": "user", "text": text}
                                    )

                            # ── Turn complete ─────────────────────────────────
                            if sc.turn_complete:
                                logger.debug("Turn complete")
                                if self._patient_info_saved:
                                    logger.info("Goodbye complete — closing call")
                                    await self._out_queue.put(None)
                                    return
                                # else: outer while restarts receive() for next turn

                        # ── Tool calls ────────────────────────────────────────
                        if msg.tool_call:
                            for fc in msg.tool_call.function_calls:
                                if fc.name == "save_patient_data":
                                    try:
                                        args = fc.args or {}
                                        self.conversation_data["caller_name"] = args.get("caller_name")
                                        self.conversation_data["patient_id"] = args.get("patient_id") or None
                                        self.conversation_data["reason"] = args.get("reason")
                                        self._patient_info_saved = True
                                        logger.info(f"Patient data saved: {args}")
                                        await self._session.send_tool_response(
                                            function_responses=types.FunctionResponse(
                                                id=fc.id,
                                                name=fc.name,
                                                response={"status": "saved"},
                                            )
                                        )
                                    except Exception as e:
                                        logger.error(f"Tool response error: {e}")

                except asyncio.CancelledError:
                    raise  # let task cancellation propagate

                except Exception as e:
                    retry_count += 1
                    if retry_count > MAX_RETRIES or self._closed:
                        logger.error(f"Receive failed after {retry_count} attempts: {e}")
                        break
                    wait = retry_count * 0.5
                    logger.warning(f"receive() error (attempt {retry_count}/{MAX_RETRIES}), retrying in {wait}s: {e}")
                    await asyncio.sleep(wait)

        finally:
            await self._out_queue.put(None)
