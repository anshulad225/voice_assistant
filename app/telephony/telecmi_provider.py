import json
import logging
import httpx
from app.telephony.base import TelephonyProvider
from typing import Dict, Any

logger = logging.getLogger(__name__)


class TeleCMIProvider(TelephonyProvider):
    """TeleCMI CHUB telephony provider"""

    response_media_type = "application/json"

    def generate_twiml_response(self, host: str, protocol: str) -> str:
        """Not used for TeleCMI — streaming is enabled via enable_streaming()."""
        return json.dumps({"status": "ok"})

    async def enable_streaming(self, call_id: str, ws_url: str) -> dict:
        """
        Call TeleCMI REST API to start streaming audio for the given call
        to our WebSocket endpoint.
        """
        from app.config import settings
        payload = {
            "appid": int(settings.telecmi_app_id),
            "secret": settings.telecmi_secret,
            "enable": True,
            "ws_url": ws_url,
            "listen_mode": "both"
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://rest.telecmi.com/v2/setting/stream",
                json=payload,
                timeout=10
            )
        result = resp.json()
        logger.info(f"TeleCMI enable_streaming for call {call_id}: {result}")
        return result

    def parse_webhook_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "call_sid": data.get("call_id"),
            "from_number": data.get("from"),
            "to_number": data.get("to"),
            "call_status": data.get("status")
        }

    def format_audio_for_provider(self, audio_base64: str) -> str:
        return audio_base64
