from app.telephony.base import TelephonyProvider
from typing import Dict, Any

class TwilioProvider(TelephonyProvider):
    """Twilio telephony provider"""
    
    def generate_twiml_response(self, host: str, protocol: str) -> str:
        """Generate TwiML for Twilio"""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{protocol}://{host}/voice/stream" />
    </Connect>
</Response>"""
    
    def parse_webhook_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Twilio webhook data"""
        return {
            "call_sid": data.get("CallSid"),
            "from_number": data.get("From"),
            "to_number": data.get("To"),
            "call_status": data.get("CallStatus")
        }
    
    def format_audio_for_provider(self, audio_base64: str) -> str:
        """Twilio uses base64 μ-law"""
        return audio_base64
