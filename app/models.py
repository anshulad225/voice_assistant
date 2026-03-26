from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class IntakeRecord(Base):
    __tablename__ = "intake_records"
    
    id = Column(Integer, primary_key=True, index=True)
    caller_name = Column(String(255), nullable=True)
    patient_id = Column(String(100), nullable=True)
    reason = Column(Text, nullable=False)
    transcript_snippet = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    call_sid = Column(String(100), unique=True, nullable=False)
