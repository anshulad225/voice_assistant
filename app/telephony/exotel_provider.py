from app.telephony.base import TelephonyProvider
from typing import Dict, Any

class ExotelProvider(TelephonyProvider):
    """Exotel telephony provider"""
    
    def generate_twiml_response(self, host: str, protocol: str) -> str:
        """Generate response for Exotel"""
        # Exotel uses similar XML format
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{protocol}://{host}/voice/stream" />
    </Connect>
</Response>"""
    
    def parse_webhook_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Exotel webhook data"""
        return {
            "call_sid": data.get("CallSid") or data.get("Sid"),
            "from_number": data.get("From") or data.get("CallFrom"),
            "to_number": data.get("To") or data.get("CallTo"),
            "call_status": data.get("Status") or data.get("DialCallStatus")
        }
    
    def format_audio_for_provider(self, audio_base64: str) -> str:
        """Exotel uses base64 μ-law (same as Twilio)"""
        return audio_base64
