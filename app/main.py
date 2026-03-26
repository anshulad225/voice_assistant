from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import cast
import json
import base64
import asyncio
import logging
from app.voice_handler import VoiceHandler
from app.database import get_db, init_db
from app.models import IntakeRecord
from app.telephony.factory import get_telephony_provider
from app.config import settings

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)

app = FastAPI(title=f"Dental Voice Intake System - {settings.telephony_provider.title()}")

# Get telephony provider
telephony = get_telephony_provider()

@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info(f"Database initialized - Using {settings.telephony_provider.title()} provider")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "ai_provider": "gemini-2.5-flash-native-audio-preview-12-2025",
        "telephony_provider": settings.telephony_provider
    }

@app.api_route("/voice/incoming", methods=["GET", "POST"])
async def handle_incoming_call(request: Request):
    """Webhook for incoming calls — handles all providers"""
    host = request.headers.get("host", "localhost:8000")
    forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    protocol = "wss" if forwarded_proto == "https" else "ws"

    if settings.telephony_provider == "telecmi":
        # TeleCMI: log call notification (streaming is configured globally at startup)
        try:
            body = await request.json()
        except Exception:
            body = dict(await request.form())
        logger.info(f"TeleCMI call notification received: {body}")
        return {"status": "ok"}

    # Twilio / Exotel: return XML response
    response_body = telephony.generate_twiml_response(host, protocol)
    logger.info(f"Incoming call → {settings.telephony_provider}: stream URL = {protocol}://{host}/voice/stream")
    return Response(content=response_body, media_type=telephony.response_media_type)


@app.websocket("/voice/stream")
async def voice_stream(websocket: WebSocket, db: Session = Depends(get_db)):
    """Bidirectional audio proxy: Exotel ↔ Gemini Live API"""
    await websocket.accept()

    handler  = VoiceHandler()
    await handler.start_session()

    call_sid  = None
    stream_sid = None
    is_telecmi = settings.telephony_provider == "telecmi"

    # ── Task 1: receive audio from provider → forward to Gemini ─────────
    async def receive_from_provider():
        nonlocal call_sid, stream_sid
        try:
            while True:
                msg = await websocket.receive()

                # Guard: ignore non-text frames (e.g. ping/pong)
                raw = msg.get("text")
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning(f"Malformed JSON from provider, skipping: {raw[:80]}")
                    continue

                event = data.get("event")

                if event == "connected":
                    logger.info(f"{settings.telephony_provider} WebSocket connected")

                elif event == "start":
                    if is_telecmi:
                        call_sid = data.get("call_id")
                    else:
                        start_data = data.get("start", {})
                        call_sid   = start_data.get("call_sid") or start_data.get("callSid")
                        stream_sid = data.get("streamSid")
                    handler.call_sid = call_sid
                    logger.info(f"Call started: {call_sid}")

                elif event == "media":
                    try:
                        audio = data.get("payload") if is_telecmi else data["media"]["payload"]
                        await handler.send_audio(audio)
                    except Exception as e:
                        logger.error(f"Error forwarding audio chunk: {e}")

                elif event == "stop":
                    logger.info(f"Call ended: {call_sid}")
                    return

        except WebSocketDisconnect:
            logger.info("Provider WebSocket disconnected")

    # ── Task 2: receive audio from Gemini → stream back to provider ─────
    # Accumulate ~200 ms of PCM-8kHz before sending to reduce the number of
    # small WebSocket messages (8000 Hz × 2 bytes × 0.2 s = 3200 bytes).
    FLUSH_BYTES = 3200

    async def send_to_provider():
        buf = bytearray()
        while True:
            pcm = await handler.get_response_audio()
            if pcm is None:         # Gemini session ended — flush remainder
                if buf:
                    audio_b64 = base64.b64encode(bytes(buf)).decode()
                    payload = (
                        json.dumps({"event": "media", "payload": audio_b64})
                        if is_telecmi else
                        json.dumps({"event": "media", "streamSid": stream_sid, "media": {"payload": audio_b64}})
                    )
                    await websocket.send_text(payload)
                return
            buf.extend(pcm)
            if len(buf) >= FLUSH_BYTES:
                audio_b64 = base64.b64encode(bytes(buf)).decode()
                payload = (
                    json.dumps({"event": "media", "payload": audio_b64})
                    if is_telecmi else
                    json.dumps({"event": "media", "streamSid": stream_sid, "media": {"payload": audio_b64}})
                )
                await websocket.send_text(payload)
                buf.clear()

    receive_task = asyncio.create_task(receive_from_provider())
    send_task    = asyncio.create_task(send_to_provider())

    try:
        done, pending = await asyncio.wait(
            [receive_task, send_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
    except Exception as e:
        logger.error(f"voice_stream error: {e}")
    finally:
        if call_sid:
            try:
                summary = handler.get_summary()
                intake  = IntakeRecord(
                    call_sid         = call_sid,
                    caller_name      = summary["caller_name"],
                    patient_id       = summary["patient_id"],
                    reason           = summary["reason"],
                    transcript_snippet = summary["transcript_snippet"],
                )
                db.add(intake)
                db.commit()
                logger.info(f"Intake record saved for call {call_sid}")
            except Exception as e:
                logger.error(f"Error saving intake record: {e}")
                db.rollback()

        await handler.close()
        await websocket.close()

@app.post("/webhook/cdr")
async def handle_cdr(request: Request, db: Session = Depends(get_db)):
    """PIOPIY CDR webhook — fires after every call ends with full call details"""
    try:
        cdr = await request.json()
    except Exception:
        cdr = dict(await request.form())

    call_id   = cdr.get("cmiuuid") or cdr.get("conversation_uuid")
    caller    = cdr.get("from")
    duration  = cdr.get("duration")
    status    = cdr.get("status")
    logger.info(f"CDR received — call={call_id} from={caller} duration={duration}s status={status}")

    # Update caller_name with the actual phone number if not already captured by AI
    if call_id:
        intake = db.query(IntakeRecord).filter_by(call_sid=call_id).first()
        if intake and not intake.caller_name:
            intake.caller_name = caller
            db.commit()
            logger.info(f"Updated caller_name from CDR: {caller}")

    return {"status": "ok"}


@app.post("/webhook/live")
async def handle_live_event(request: Request):
    """PIOPIY Live Events webhook — real-time call status (stream_connected, stream_error, etc.)"""
    try:
        event = await request.json()
    except Exception:
        event = dict(await request.form())
    logger.info(f"Live event: {event}")
    return {"status": "ok"}


@app.get("/intakes")
async def list_intakes(db: Session = Depends(get_db)):
    """List all intake records"""
    intakes = db.query(IntakeRecord).order_by(IntakeRecord.created_at.desc()).limit(50).all()
    return [
        {
            "id": i.id,
            "caller_name": i.caller_name,
            "patient_id": i.patient_id,
            "reason": i.reason,
            "created_at": i.created_at.isoformat(),
            "call_sid": i.call_sid
        }
        for i in intakes
    ]

@app.get("/intakes/{call_sid}")
async def get_intake(call_sid: str, db: Session = Depends(get_db)):
    """Get specific intake record"""
    intake = db.query(IntakeRecord).filter_by(call_sid=call_sid).first()
    if not intake:
        return {"error": "Intake not found"}, 404
    
    return {
        "id": intake.id,
        "caller_name": intake.caller_name,
        "patient_id": intake.patient_id,
        "reason": intake.reason,
        "transcript_snippet": intake.transcript_snippet,
        "created_at": intake.created_at.isoformat(),
        "call_sid": intake.call_sid
    }
