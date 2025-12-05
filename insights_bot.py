"""
Daily Insights Telegram Bot with Google Drive Integration
Fetches messages from Sanity bot, analyzes with Google AI, and saves to Google Drive
"""

import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pickle
import json

# Configuration from environment variables
ANALYZER_BOT_TOKEN = os.environ.get("ANALYZER_BOT_TOKEN")
SANITY_BOT_TOKEN = os.environ.get("SANITY_BOT_TOKEN")
YOUR_CHAT_ID = os.environ.get("YOUR_CHAT_ID")
GOOGLE_AI_API_KEY = os.environ.get("GOOGLE_AI_API_KEY")

# Google Drive settings
SCOPES = ['https://www.googleapis.com/auth/drive.file']
FOLDER_NAME = "Daily Insights"

def get_drive_service():
    """Get Google Drive service with authentication"""
    creds = None
    
    # Load saved credentials
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If no valid credentials, let user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Try to load from environment variable first
            creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
            if creds_json:
                # Write to temporary file
                with open('/tmp/credentials.json', 'w') as f:
                    f.write(creds_json)
                flow = InstalledAppFlow.from_client_secrets_file('/tmp/credentials.json', SCOPES)
            elif os.path.exists('credentials.json'):
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            else:
                return None, "Google Drive credentials not found. Set GOOGLE_CREDENTIALS_JSON environment variable."
            
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next time
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return build('drive', 'v3', credentials=creds), None

def get_or_create_folder(service):
    """Get or create the Daily Insights folder"""
    # Search for existing folder
    query = f"name='{FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    folders = results.get('files', [])
    
    if folders:
        return folders[0]['id']
    
    # Create new folder
    folder_metadata = {
        'name': FOLDER_NAME,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = service.files().create(body=folder_metadata, fields='id').execute()
    return folder.get('id')

def save_to_drive(service, folder_id, filename, content):
    """Save content to Google Drive"""
    # Create temporary file
    temp_file = f"/tmp/{filename}"
    with open(temp_file, 'w') as f:
        f.write(content)
    
    # Upload to Drive
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    media = MediaFileUpload(temp_file, mimetype='text/plain')
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()
    
    # Clean up temp file
    os.remove(temp_file)
    
    return file.get('webViewLink')

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
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_AI_API_KEY}"
    
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
    
    # Save to Google Drive
    await update.message.reply_text("💾 Saving to Google Drive...")
    
    drive_service, error = get_drive_service()
    
    if error:
        await update.message.reply_text(f"⚠️  {error}\nAnalysis sent but not saved to Drive.")
        return
    
    try:
        folder_id = get_or_create_folder(drive_service)
        
        # Save input messages
        today_str = datetime.now().strftime('%Y-%m-%d')
        input_filename = f"inputs_{today_str}.txt"
        input_content = f"Daily Input Messages - {today_str}\n\n{messages}"
        input_link = save_to_drive(drive_service, folder_id, input_filename, input_content)
        
        # Save insights
        insights_filename = f"insights_{today_str}.txt"
        insights_content = f"Daily Insights - {today_str}\n\n{analysis}"
        insights_link = save_to_drive(drive_service, folder_id, insights_filename, insights_content)
        
        await update.message.reply_text(
            f"✅ Saved to Google Drive!\n\n"
            f"📝 [View Inputs]({input_link})\n"
            f"📊 [View Insights]({insights_link})",
            parse_mode='Markdown'
        )
    
    except Exception as e:
        await update.message.reply_text(f"⚠️  Error saving to Drive: {str(e)}\nAnalysis was sent but not saved.")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "👋 Welcome to Daily Insights Bot!\n\n"
        "Send /analyze to get your daily summary.\n\n"
        "I'll fetch all your messages from today, analyze them, "
        "and save both inputs and insights to Google Drive!"
    )

def main():
    """Start the bot"""
    
    print("🤖 Bot is starting...")
    
    # Create application
    application = Application.builder().token(ANALYZER_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("analyze", analyze_command))
    
    # Start bot
    print("✅ Bot is running!")
    print("📁 Will save to Google Drive folder: 'Daily Insights'")
    print("Send /analyze to your bot to get daily insights!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
