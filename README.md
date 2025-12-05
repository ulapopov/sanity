# Daily Insights Bot

A Telegram bot that automatically analyzes daily voice notes using Google AI and saves insights to Google Drive.

## Features

- 🎤 Collects voice-to-text messages throughout the day
- 🤖 Analyzes patterns and provides insights using Google AI
- 📁 Auto-saves inputs and insights to Google Drive
- 💬 Simple Telegram interface - just send `/analyze`

## Tech Stack

- Python 3.12+
- python-telegram-bot - Telegram Bot API
- Google AI (Gemini) - For analysis
- Google Drive API - For storage

## Setup

### 1. Environment Variables

Set these in your deployment platform:

```
ANALYZER_BOT_TOKEN=your_telegram_bot_token
SANITY_BOT_TOKEN=your_input_bot_token
YOUR_CHAT_ID=your_telegram_chat_id
GOOGLE_AI_API_KEY=your_google_ai_key
```

### 2. Google Drive Credentials

- Enable Google Drive API in Google Cloud Console
- Create OAuth2 credentials (Desktop app)
- Download and add `credentials.json` to project root

### 3. Deploy

Deploy to any Python hosting platform (Railway, Render, PythonAnywhere, etc.)

## Usage

1. Throughout the day: Send voice/text messages to your input bot
2. Anytime: Send `/analyze` to the insights bot
3. Get: AI analysis + Google Drive links to saved files

## Project Structure

```
├── insights_bot_clean.py  # Main bot code
├── requirements.txt       # Python dependencies
├── credentials.json       # Google Drive OAuth (not in repo)
└── README.md             # This file
```

## License

MIT
