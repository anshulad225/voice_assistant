from abc import ABC, abstractmethod
from typing import Dict, Any

class TelephonyProvider(ABC):
    """Base class for telephony providers"""

    response_media_type: str = "application/xml"

    @abstractmethod
    def generate_twiml_response(self, host: str, protocol: str) -> str:
        """Generate response body for incoming calls (XML or JSON depending on provider)"""
        pass

    @abstractmethod
    def parse_webhook_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse incoming webhook data"""
        pass

    @abstractmethod
    def format_audio_for_provider(self, audio_base64: str) -> str:
        """Format audio for the provider"""
        pass
