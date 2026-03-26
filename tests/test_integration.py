import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, IntakeRecord
from datetime import datetime

@pytest.fixture
def test_db():
    """Create in-memory test database"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(bind=engine)
    db = TestSessionLocal()
    yield db
    db.close()

def test_intake_record_creation(test_db):
    """Test creating and saving an intake record"""
    intake = IntakeRecord(
        call_sid="CA1234567890",
        caller_name="John Doe",
        patient_id="P12345",
        reason="Toothache follow-up",
        transcript_snippet="user: I need to follow up\nassistant: I'll have someone call you back"
    )
    
    test_db.add(intake)
    test_db.commit()
    
    saved = test_db.query(IntakeRecord).filter_by(call_sid="CA1234567890").first()
    assert saved is not None
    assert saved.caller_name == "John Doe"
    assert saved.reason == "Toothache follow-up"
    assert saved.created_at is not None
