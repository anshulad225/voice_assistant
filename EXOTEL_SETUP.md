# Exotel Setup Guide

## ✅ Your Code Now Supports BOTH Twilio and Exotel!

Switching between providers is just changing one line in `.env`

## How to Switch Providers

### Use Exotel (Current):
```
TELEPHONY_PROVIDER=exotel
```

### Use Twilio:
```
TELEPHONY_PROVIDER=twilio
```

That's it! No code changes needed.

## Setting Up Exotel

### Step 1: Sign Up
1. Go to: https://exotel.com/
2. Click "Start Free Trial"
3. Sign up with your details
4. Verify your account

### Step 2: Get Your Credentials
After signup, go to dashboard and get:
- **API Key**
- **API Token**  
- **SID** (Account SID)

### Step 3: Add to .env
```
EXOTEL_API_KEY=your_api_key_here
EXOTEL_API_TOKEN=your_api_token_here
EXOTEL_SID=your_sid_here
TELEPHONY_PROVIDER=exotel
```

### Step 4: Get an Exotel Number
1. In Exotel dashboard, go to "Phone Numbers"
2. Buy an Indian number (₹500-1000/month)
3. Note the number

### Step 5: Configure Webhook
1. Go to your Exotel number settings
2. Set "Incoming Call URL" to:
   ```
   https://your-ngrok-url.ngrok-free.dev/voice/incoming
   ```
3. Method: POST
4. Save

### Step 6: Set Up Call Forwarding
On your personal phone, dial:
```
**61*[YOUR_EXOTEL_NUMBER]#  (no answer)
**67*[YOUR_EXOTEL_NUMBER]#  (busy)
```

## Testing

1. Make sure server is running: `python run_dev.py`
2. Make sure ngrok is running: `ngrok http 8000`
3. Call your personal number
4. Don't answer
5. AI should take over!

## Switching Back to Twilio

### How Easy Is It?

**SUPER EASY!** Just change one line:

1. Open `.env`
2. Change: `TELEPHONY_PROVIDER=twilio`
3. Restart server: `python run_dev.py`

Done! Takes 10 seconds.

## Cost Comparison

### Exotel (India):
- Indian number: ₹500-1000/month
- Incoming calls: ₹0.30/min
- Outgoing calls: ₹0.50/min
- **Better for Indian customers**

### Twilio (US):
- US number: $1/month
- Indian number: $2/month  
- Incoming calls: $0.0085/min
- Outgoing calls: $0.02/min
- **Better for US customers**

## Which Should You Use?

### Use Exotel if:
- Your customers are in India
- You want Indian phone numbers
- You need local support
- You want easier compliance

### Use Twilio if:
- Your customers are international
- You need global coverage
- You're already familiar with Twilio
- You need advanced features

## Current Status

✅ Code supports both providers
✅ Switching is one config change
✅ No code rewrite needed
✅ Same AI, same features

**Recommendation:** Try Exotel for India, keep Twilio as backup!
