from pydantic_settings import BaseSettings
from typing import Optional, Literal

class Settings(BaseSettings):
    # Telephony provider selection
    telephony_provider: Literal["twilio", "exotel", "telecmi"] = "twilio"

    # Twilio Configuration
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None

    # Exotel Configuration
    exotel_api_key: Optional[str] = None
    exotel_api_token: Optional[str] = None
    exotel_sid: Optional[str] = None

    # TeleCMI Configuration
    telecmi_app_id: Optional[str] = None
    telecmi_secret: Optional[str] = None
    # WebSocket URL from HTTP ngrok, e.g. wss://xxxx.ngrok-free.dev/voice/stream
    telecmi_ws_url: Optional[str] = None

    # Sarvam AI (STT + TTS)
    sarvam_api_key: str

    # Google AI (not used)
    google_api_key: Optional[str] = None
    
    # Database
    database_url: str
    environment: str = "development"
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
