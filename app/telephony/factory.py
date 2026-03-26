from app.config import settings
from app.telephony.base import TelephonyProvider
from app.telephony.twilio_provider import TwilioProvider
from app.telephony.exotel_provider import ExotelProvider
from app.telephony.telecmi_provider import TeleCMIProvider

def get_telephony_provider() -> TelephonyProvider:
    """Factory function to get the configured telephony provider"""
    if settings.telephony_provider == "twilio":
        return TwilioProvider()
    elif settings.telephony_provider == "exotel":
        return ExotelProvider()
    elif settings.telephony_provider == "telecmi":
        return TeleCMIProvider()
    else:
        raise ValueError(f"Unknown telephony provider: {settings.telephony_provider}")
