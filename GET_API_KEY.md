# How to Get Your Google AI API Key

## Step 1: Go to Google AI Studio

Visit: **https://aistudio.google.com/**

## Step 2: Sign In

- Sign in with your Google account
- Accept terms if prompted

## Step 3: Get API Key

1. Look for "Get API Key" in the left sidebar
2. Click "Create API Key"
3. Select "Create API key in new project" (or use existing project)
4. Copy the API key that appears

## Step 4: Add to .env File

Open `.env` file and replace:
```
GOOGLE_API_KEY=your_google_api_key_here
```

With your actual key:
```
GOOGLE_API_KEY=AIzaSyD...your_actual_key...
```

## Step 5: Test It

Run:
```bash
python -m app.db.init_db
```

You should see:
```
Initializing database...
Database initialized successfully!
```

## Important Notes

- Keep your API key secret (never commit to git)
- The `.env` file is already in `.gitignore`
- Free tier: 15 requests per minute
- Upgrade for higher limits if needed

## Troubleshooting

**"API key not valid"**
- Make sure you copied the entire key
- Check for extra spaces
- Try creating a new key

**"Model not found"**
- Gemini 2.0 Flash is in preview
- Your account should have automatic access
- Wait a few minutes and try again

## Next Steps

Once you have the API key:
1. Add it to `.env`
2. Run `python -m app.db.init_db`
3. Run `python run_dev.py`
4. Test with a phone call!
