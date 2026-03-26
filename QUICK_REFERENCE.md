# Quick Reference Card

## 🚀 Start Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Setup environment
cp .env.example .env
# Edit .env with your credentials

# 3. Initialize database
python -m app.db.init_db

# 4. Run server
python run_dev.py

# 5. Expose with ngrok (separate terminal)
ngrok http 8000
```

## 🔑 Required Credentials

| Service | Where to Get | Environment Variable |
|---------|--------------|---------------------|
| Twilio | [console.twilio.com](https://console.twilio.com) | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` |
| Google AI | [aistudio.google.com](https://aistudio.google.com) | `GOOGLE_API_KEY` |
| PostgreSQL | Local or cloud | `DATABASE_URL` |

## 📞 Twilio Configuration

1. Go to Phone Numbers → Active Numbers
2. Click your number
3. Voice Configuration:
   - **A CALL COMES IN**: Webhook
   - **URL**: `https://your-ngrok-url.ngrok.io/voice/incoming`
   - **HTTP**: POST

## 🧪 Testing Commands

```bash
# Run guardrail tests
pytest tests/test_guardrails.py -v

# Run all tests
pytest tests/ -v

# Check health endpoint
curl http://localhost:8000/health

# List intakes
curl http://localhost:8000/intakes
```

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/voice/incoming` | POST | Twilio webhook (TwiML) |
| `/voice/stream` | WebSocket | Audio streaming |
| `/intakes` | GET | List all intakes |
| `/intakes/{call_sid}` | GET | Get specific intake |

## 🎙️ Voice Options

Change voice in `app/voice_handler.py`:

```python
"voice_name": "Puck"  # Default: warm, conversational
# Options: Puck, Charon, Kore, Fenrir, Aoede
```

## 🛡️ Guardrails

The AI will NEVER:
- ❌ Book appointments
- ❌ Answer clinical questions
- ❌ Discuss pricing

Instead, it says: "I'll have someone from our team call you back to help with that."

## 📁 Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app, WebSocket endpoint |
| `app/voice_handler.py` | Gemini integration, audio processing |
| `app/prompts.py` | System prompt, guardrails |
| `app/models.py` | Database schema |
| `.env` | Configuration (DO NOT COMMIT) |

## 🐛 Common Issues

### "Module not found"
```bash
pip install -r requirements.txt
```

### "Database connection failed"
```bash
# Check DATABASE_URL in .env
# Ensure PostgreSQL is running
python -m app.db.init_db
```

### "API key invalid"
```bash
# Verify GOOGLE_API_KEY in .env
# Get new key from aistudio.google.com
```

### "Twilio not connecting"
```bash
# Check ngrok is running
# Verify webhook URL in Twilio console
# Check server logs for errors
```

## 📝 Conversation Flow

1. **Greet**: "Thank you for calling [Clinic]. How can I help?"
2. **Reason**: "What's the reason for your call?"
3. **Name**: "May I have your name please?"
4. **Patient ID**: "Are you an existing patient?"
5. **Acknowledge**: "Thank you [Name]. I've noted..."
6. **Promise**: "Someone will call you back shortly."
7. **End**: "Have a great day!"

## 💰 Cost Estimate

**Per 2-minute call:**
- Gemini API: ~$0.05
- Twilio: ~$0.01
- **Total**: ~$0.06 per call

**Monthly (1000 calls):**
- ~$60/month

## 🔒 Security Checklist

- [ ] `.env` file in `.gitignore`
- [ ] Database encryption enabled
- [ ] SSL/TLS for production
- [ ] API keys rotated regularly
- [ ] Logs sanitized (no PII)
- [ ] HIPAA BAA signed with vendors

## 📚 Documentation

- **Setup**: QUICKSTART.md
- **Testing**: TESTING.md
- **Deployment**: DEPLOYMENT.md
- **Gemini**: GEMINI_SETUP.md
- **Status**: PHASE1_STATUS.md

## 🆘 Support

1. Check TESTING.md troubleshooting
2. Review logs: `tail -f logs/app.log`
3. Test with curl/Postman
4. Check Twilio debugger
5. Verify Gemini API quota

## ✅ Pre-Deployment Checklist

- [ ] All tests passing
- [ ] Environment variables set
- [ ] Database initialized
- [ ] Twilio webhook configured
- [ ] Test call successful
- [ ] Guardrails verified
- [ ] Latency acceptable (<1.5s)
- [ ] Database records saving
- [ ] Error handling tested
- [ ] Logs configured

---

**Need help?** See full documentation in project root.
