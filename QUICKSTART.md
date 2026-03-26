# Quick Start Guide - Phase 1

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Configure Environment

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
- `TWILIO_ACCOUNT_SID` - From Twilio Console
- `TWILIO_AUTH_TOKEN` - From Twilio Console
- `GOOGLE_API_KEY` - From Google AI Studio
- `DATABASE_URL` - PostgreSQL connection string

## 3. Initialize Database

```bash
python -m app.db.init_db
```

## 4. Run Tests

Verify guardrails are working:
```bash
pytest tests/test_guardrails.py -v
```

Expected output: All 7 tests pass ✓

## 5. Start Development Server

```bash
python run_dev.py
```

Server starts at `http://localhost:8000`

## 6. Expose with ngrok (for Twilio)

In a new terminal:
```bash
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)

## 7. Configure Twilio Webhook

1. Go to [Twilio Console](https://console.twilio.com)
2. Navigate to Phone Numbers → Manage → Active Numbers
3. Click your phone number
4. Under "Voice Configuration":
   - A CALL COMES IN: Webhook
   - URL: `https://your-ngrok-url.ngrok.io/voice/incoming`
   - HTTP: POST
5. Save

## 8. Test the System

Call your Twilio number and have a conversation:
- The AI will greet you
- Ask for your reason for calling
- Collect your name
- Promise a callback
- End the call

## 9. Verify Database Storage

Check the intakes endpoint:
```bash
curl http://localhost:8000/intakes
```

You should see your call data saved as JSON.

## Success Criteria Checklist

- [ ] Call completes successfully
- [ ] Intake record appears in `/intakes` endpoint
- [ ] AI deflects booking questions (test by asking to schedule)
- [ ] AI deflects clinical questions (test by asking about tooth pain)
- [ ] Response feels natural (< 1.5s latency)

## Troubleshooting

### "Connection refused" error
- Ensure server is running (`python run_dev.py`)
- Check ngrok is forwarding to port 8000

### "Database connection failed"
- Verify PostgreSQL is running
- Check `DATABASE_URL` in `.env`
- Run `python -m app.db.init_db`

### "OpenAI API error"
- Verify `GOOGLE_API_KEY` is correct
- Ensure you have Gemini API access enabled
- Check Google AI Studio for API quota

### Audio quality issues
- Check Twilio account status
- Verify WebSocket connection in logs
- Monitor latency in server logs
