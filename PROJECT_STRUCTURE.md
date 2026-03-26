# Project Structure - Phase 1

```
dental-voice-intake/
│
├── app/                          # Main application code
│   ├── __init__.py
│   ├── main.py                   # FastAPI app, WebSocket endpoint, routes
│   ├── config.py                 # Environment configuration
│   ├── database.py               # Database connection & session management
│   ├── models.py                 # SQLAlchemy models (IntakeRecord)
│   ├── prompts.py                # AI system prompt & guardrail keywords
│   ├── voice_handler.py          # WebSocket proxy logic (Twilio ↔ OpenAI)
│   └── db/
│       ├── __init__.py
│       └── init_db.py            # Database initialization script
│
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── test_guardrails.py        # Guardrail verification tests ✓
│   ├── test_integration.py       # Database integration tests
│   └── test_e2e.py               # End-to-end conversation tests
│
├── .env.example                  # Environment variables template
├── .gitignore                    # Git ignore rules
├── requirements.txt              # Python dependencies
├── pytest.ini                    # Pytest configuration
├── run_dev.py                    # Development server launcher
│
├── README.md                     # Project overview
├── QUICKSTART.md                 # Step-by-step setup guide
├── TESTING.md                    # Testing procedures & scenarios
├── DEPLOYMENT.md                 # AWS deployment guide
├── PHASE1_STATUS.md              # Implementation status & success criteria
└── PROJECT_STRUCTURE.md          # This file

```

## Key Files Explained

### Core Application
- `app/main.py`: FastAPI WebSocket endpoint that accepts Twilio Media Streams
- `app/voice_handler.py`: Bidirectional audio proxy between Twilio and Gemini
- `app/prompts.py`: Conservative conversation flow with strict guardrails

### Data Layer
- `app/models.py`: IntakeRecord schema (name, reason, timestamp, transcript)
- `app/database.py`: PostgreSQL connection via SQLAlchemy

### Testing
- `tests/test_guardrails.py`: Verifies AI never attempts booking/clinical answers
- All tests pass: `pytest tests/test_guardrails.py -v`

### Configuration
- `.env.example`: Template for Twilio, Google AI, and database credentials
- `requirements.txt`: Exact versions of FastAPI, Twilio, google-generativeai, SQLAlchemy

## Data Flow

1. Caller → Twilio Phone Number
2. Twilio → `/voice/incoming` webhook → TwiML with Stream URL
3. Twilio Media Stream → `/voice/stream` WebSocket
4. FastAPI → Google gemini-2.5-flash-native-audio-preview-12-2025
 (audio + system prompt)
5. Gemini → FastAPI → Twilio (audio response)
6. Conversation ends → Parse transcript → Save to PostgreSQL
7. Team views intake via `/intakes` API endpoint

## Phase 1 Boundaries

✅ Included:
- WebSocket proxy (Twilio ↔ Gemini)
- Conservative conversation flow
- Structured data extraction
- PostgreSQL storage
- Guardrail test suite

❌ Not Included (Future Phases):
- SMS acknowledgment to caller
- Admin dashboard
- Multi-clinic support
- Advanced NLP for better extraction
- HIPAA audit logging
