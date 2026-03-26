# Google gemini-live-2.5-flash-native-audio
 Setup Guide

## Getting Your Google AI API Key

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Sign in with your Google account
3. Click "Get API Key" in the left sidebar
4. Click "Create API Key"
5. Copy the API key

## Add to Environment

Add to your `.env` file:
```
GOOGLE_API_KEY=your_api_key_here
```

## gemini-live-2.5-flash-native-audio
 Features

This implementation uses `gemini-2.0-flash-exp` with native audio support:

- **Native Audio I/O**: Processes audio directly without transcription step
- **Low Latency**: Optimized for real-time conversations
- **Voice Options**: Using "Puck" voice (warm, professional)
- **Audio Format**: Supports μ-law (G.711) used by Twilio

## Model Configuration

The voice handler configures Gemini with:
```python
{
    "generation_config": {
        "response_modalities": ["AUDIO"],
        "speech_config": {
            "voice_config": {
                "prebuilt_voice_config": {
                    "voice_name": "Puck"
                }
            }
        }
    }
}
```

## Available Voices

You can change the voice in `app/voice_handler.py`:
- **Puck**: Warm, conversational (default)
- **Charon**: Professional, clear
- **Kore**: Friendly, energetic
- **Fenrir**: Deep, authoritative
- **Aoede**: Soft, gentle

## Audio Format Details

- **Input**: μ-law (G.711) from Twilio at 8kHz
- **Output**: μ-law (G.711) back to Twilio
- **Encoding**: Base64 for WebSocket transmission
- **Buffering**: Processes audio in chunks for efficiency

## API Limits & Quotas

Check your quota at [Google AI Studio](https://aistudio.google.com/):
- Free tier: 15 requests per minute
- Paid tier: Higher limits available

## Troubleshooting

### "API key not valid"
- Verify key is copied correctly
- Check key hasn't been deleted in AI Studio
- Ensure no extra spaces in `.env`

### "Model not found"
- gemini-live-2.5-flash-native-audio
 is in preview
- Ensure your account has access
- Try `gemini-2.0-flash-exp` model name

### Audio quality issues
- Check Twilio audio format is μ-law
- Verify base64 encoding/decoding
- Monitor buffer sizes in logs

### Latency issues
- Reduce audio buffer size (currently 10 chunks)
- Check network connection to Google AI
- Monitor API response times in logs

## Cost Estimation

gemini-live-2.5-flash-native-audio
 pricing (as of Dec 2024):
- Audio input: $0.000125 per second
- Audio output: $0.000250 per second
- Average 2-minute call: ~$0.05

Much more cost-effective than OpenAI Realtime API!
