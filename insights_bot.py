"""
Daily Insights Telegram Bot (Simplified - No Google Drive)
Fetches messages from Sanity bot and analyzes with Google AI
"""

import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests
from datetime import datetime

# Configuration from environment variables
ANALYZER_BOT_TOKEN = os.environ.get("ANALYZER_BOT_TOKEN")
SANITY_BOT_TOKEN = os.environ.get("SANITY_BOT_TOKEN")
YOUR_CHAT_ID = os.environ.get("YOUR_CHAT_ID")
GOOGLE_AI_API_KEY = os.environ.get("GOOGLE_AI_API_KEY")

def get_todays_messages():
    """Fetch today's messages from Sanity bot"""
    url = f"https://api.telegram.org/bot{SANITY_BOT_TOKEN}/getUpdates"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if not data.get("ok"):
            return None, "Error fetching messages"
        
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        messages = []
        for update in data.get("result", []):
            if "message" in update:
                msg = update["message"]
                if str(msg["chat"]["id"]) == YOUR_CHAT_ID:
                    msg_date = datetime.fromtimestamp(msg["date"])
                    if msg_date >= today:
                        text = msg.get("text", "")
                        if text and text != "{input}":
                            time = msg_date.strftime("%H:%M")
                            messages.append(f"[{time}] {text}")
        
        if not messages:
            return None, "No messages found for today"
        
        return "\n".join(messages), None
    
    except Exception as e:
        return None, f"Error: {str(e)}"

def analyze_with_ai(messages_text):
    """Send messages to Google AI for analysis"""
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_AI_API_KEY}"
    
    prompt = f"""Analyze these daily voice notes and provide insights on:
- Main themes and topics discussed
- Emotional patterns throughout the day
- Key decisions or ideas mentioned
- Suggestions for follow-up actions
- Overall summary of the day

Here are today's notes:
{messages_text}
"""
    
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        data = response.json()
        
        if "candidates" in data and len(data["candidates"]) > 0:
            return data["candidates"][0]["content"]["parts"][0]["text"], None
        else:
            return None, f"AI Error: {data.get('error', {}).get('message', 'Unknown error')}"
    
    except Exception as e:
        return None, f"Error calling AI: {str(e)}"

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /analyze command"""
    
    if str(update.effective_chat.id) != YOUR_CHAT_ID:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    await update.message.reply_text("🔍 Fetching your messages from today...")
    
    # Get messages
    messages, error = get_todays_messages()
    
    if error:
        await update.message.reply_text(f"❌ {error}")
        return
    
    await update.message.reply_text(f"✅ Found {len(messages.splitlines())} messages\n\n🤖 Analyzing with AI...")
    
    # Analyze
    analysis, error = analyze_with_ai(messages)
    
    if error:
        await update.message.reply_text(f"❌ {error}")
        return
    
    # Send analysis to chat
    header = "📊 *DAILY INSIGHTS*\n" + "="*30 + "\n\n"
    response = header + analysis
    
    if len(response) > 4000:
        await update.message.reply_text(header, parse_mode='Markdown')
        chunks = [analysis[i:i+4000] for i in range(0, len(analysis), 4000)]
        for chunk in chunks:
            await update.message.reply_text(chunk)
    else:
        await update.message.reply_text(response, parse_mode='Markdown')
    
    await update.message.reply_text("\n💡 Note: Google Drive saving coming soon!")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "👋 Welcome to Daily Insights Bot!\n\n"
        "Send /analyze to get your daily summary.\n\n"
        "I'll fetch all your messages from today and analyze them!"
    )

def main():
    """Start the bot"""
    
    print("🤖 Bot is starting...")
    print(f"Debug - ANALYZER_BOT_TOKEN exists: {bool(ANALYZER_BOT_TOKEN)}")
    print(f"Debug - SANITY_BOT_TOKEN exists: {bool(SANITY_BOT_TOKEN)}")
    print(f"Debug - YOUR_CHAT_ID: {YOUR_CHAT_ID}")
    print(f"Debug - GOOGLE_AI_API_KEY exists: {bool(GOOGLE_AI_API_KEY)}")
    
    if not ANALYZER_BOT_TOKEN:
        print("❌ ERROR: ANALYZER_BOT_TOKEN not set!")
        return
    
    # Create application
    application = Application.builder().token(ANALYZER_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("analyze", analyze_command))
    
    # Start bot
    print("✅ Bot is running!")
    print("Send /analyze to your bot to get daily insights!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
