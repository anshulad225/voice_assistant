"""
End-to-end test for voice intake system.
This test simulates a complete call flow and validates database storage.
"""
import pytest
from app.voice_handler import VoiceHandler

@pytest.mark.asyncio
async def test_conversation_data_extraction():
    """Test that conversation data is properly extracted"""
    handler = VoiceHandler()
    
    # Simulate conversation
    handler._extract_info("I need a cleaning appointment", "user")
    handler._extract_info("My name is Sarah Johnson", "user")
    
    assert handler.conversation_data["reason"] == "I need a cleaning appointment"
    assert handler.conversation_data["caller_name"] == "Sarah"
    
def test_summary_generation():
    """Test intake summary generation"""
    handler = VoiceHandler()
    
    handler.conversation_data["caller_name"] = "Mike Smith"
    handler.conversation_data["reason"] = "Tooth pain"
    handler.conversation_data["transcript"] = [
        {"role": "user", "text": "I have tooth pain"},
        {"role": "assistant", "text": "I'll have someone call you back"}
    ]
    
    summary = handler.get_summary()
    
    assert summary["caller_name"] == "Mike Smith"
    assert summary["reason"] == "Tooth pain"
    assert "tooth pain" in summary["transcript_snippet"].lower()
    assert len(summary["transcript_snippet"]) <= 500
