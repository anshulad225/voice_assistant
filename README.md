# Dental Clinic Voice Intake System - Phase 1

## Core Voice Engine

A HIPAA-eligible voice intake system that converts missed calls into structured digital summaries using gemini-2.5-flash-native-audio-preview-12-2025
.

## 🎯 What It Does

- Answers missed calls with AI receptionist
- Collects caller name, reason, and patient ID
- Promises callback (never books or gives medical advice)
- Saves structured intake data to PostgreSQL
- Provides API to view all intakes

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Telephony**: Twilio Media Streams
- **AI**: gemini-2.5-flash-native-audio-preview-12-2025
 (`gemini-2.0-flash-exp`)
- **Database**: PostgreSQL + SQLAlchemy
- **Hosting**: AWS (HIPAA-eligible)

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Add your Twilio, Google AI, and database credentials

# 3. Initialize database
python -m app.db.init_db

# 4. Start server
python run_dev.py

# 5. Expose with ngrok (for Twilio webhook)
ngrok http 8000
```

See [QUICKSTART.md](QUICKSTART.md) for detailed setup instructions.

## 📞 How It Works

1. Caller dials Twilio number
2. Twilio streams audio to FastAPI WebSocket
3. Gemini 2.0 Flash processes conversation with guardrails
4. AI collects name, reason, patient ID
5. Promises callback and ends call
6. Intake saved to PostgreSQL

## 🛡️ Guardrails

The AI is strictly limited:
- ❌ **Never books appointments**
- ❌ **Never answers clinical questions**
- ❌ **Never discusses pricing**

Instead: "I'll have someone from our team call you back to help with that."

## 📊 API Endpoints

- `GET /health` - Health check
- `POST /voice/incoming` - Twilio webhook
- `WebSocket /voice/stream` - Audio streaming
- `GET /intakes` - List all intakes
- `GET /intakes/{call_sid}` - Get specific intake

## 🧪 Testing

```bash
# Run guardrail tests
pytest tests/test_guardrails.py -v

# All tests
pytest tests/ -v
```

See [TESTING.md](TESTING.md) for manual phone testing procedures.

## 💰 Cost

**Per 2-minute call:**
- Gemini API: ~$0.05
- Twilio: ~$0.01
- **Total**: ~$0.06/call

**90% cheaper than OpenAI Realtime API!**

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Step-by-step setup
- **[GEMINI_SETUP.md](GEMINI_SETUP.md)** - Google AI configuration
- **[TESTING.md](TESTING.md)** - Testing procedures
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - AWS deployment guide
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Developer cheat sheet
- **[PHASE1_STATUS.md](PHASE1_STATUS.md)** - Implementation status

## ✅ Phase 1 Success Criteria

- [x] WebSocket proxy (Twilio ↔ Gemini)
- [x] Conservative conversation flow
- [x] Structured data extraction
- [x] PostgreSQL storage
- [x] Guardrail test suite (7/7 passing)
- [ ] End-to-end phone test (requires credentials)
- [ ] Latency < 1.5s (test during live calls)

## 🔒 HIPAA Compliance

- Uses HIPAA-eligible services (AWS, Twilio)
- Minimal PHI handling
- Encryption at rest and in transit
- Full audit trails
- Signed BAAs required

## 🚧 Phase 1 Boundaries

**Included:**
- Voice intake collection
- Basic data extraction
- Database storage
- Guardrails

**Not Included (Future Phases):**
- SMS acknowledgment
- Admin dashboard
- Multi-clinic support
- Advanced NLP

## 🆘 Troubleshooting

See [TESTING.md](TESTING.md) troubleshooting section or [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for common issues.

## 📝 License

Proprietary - Dental Clinic SaaS System
