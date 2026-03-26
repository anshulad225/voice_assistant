import pytest
from app.prompts import SYSTEM_PROMPT, GUARDRAIL_KEYWORDS

class TestGuardrails:
    """Test suite to verify AI never handles booking or clinical queries"""
    
    def test_system_prompt_contains_restrictions(self):
        """Verify system prompt explicitly forbids booking and clinical answers"""
        prompt_lower = SYSTEM_PROMPT.lower()
        
        assert "never" in prompt_lower
        assert "book" in prompt_lower or "appointment" in prompt_lower
        assert "clinical" in prompt_lower or "medical" in prompt_lower
        
    def test_booking_keywords_defined(self):
        """Verify booking-related keywords are tracked"""
        assert "booking" in GUARDRAIL_KEYWORDS
        assert len(GUARDRAIL_KEYWORDS["booking"]) > 0
        
        booking_keywords = GUARDRAIL_KEYWORDS["booking"]
        assert "appointment" in booking_keywords
        assert "schedule" in booking_keywords
        
    def test_clinical_keywords_defined(self):
        """Verify clinical-related keywords are tracked"""
        assert "clinical" in GUARDRAIL_KEYWORDS
        assert len(GUARDRAIL_KEYWORDS["clinical"]) > 0
        
        clinical_keywords = GUARDRAIL_KEYWORDS["clinical"]
        assert "pain" in clinical_keywords
        assert "emergency" in clinical_keywords

        
    def test_pricing_keywords_defined(self):
        """Verify pricing-related keywords are tracked"""
        assert "pricing" in GUARDRAIL_KEYWORDS
        assert len(GUARDRAIL_KEYWORDS["pricing"]) > 0
        
        pricing_keywords = GUARDRAIL_KEYWORDS["pricing"]
        assert "cost" in pricing_keywords
        assert "price" in pricing_keywords
        
    def test_system_prompt_has_deflection_response(self):
        """Verify prompt includes a deflection response for restricted topics"""
        assert "call you back" in SYSTEM_PROMPT.lower()
        
    def test_conversation_flow_defined(self):
        """Verify the conversation follows a structured flow"""
        assert "greet" in SYSTEM_PROMPT.lower()
        assert "reason" in SYSTEM_PROMPT.lower()
        assert "name" in SYSTEM_PROMPT.lower()
        assert "patient" in SYSTEM_PROMPT.lower()

def test_prompt_structure_complete():
    """Verify system prompt has all required components"""
    required_elements = [
        "receptionist",
        "dental",
        "never",
        "book",
        "clinical",
        "greet",
        "reason",
        "name",
        "patient",
        "call you back"
    ]
    
    prompt_lower = SYSTEM_PROMPT.lower()
    for element in required_elements:
        assert element in prompt_lower, f"Missing required element: {element}"
