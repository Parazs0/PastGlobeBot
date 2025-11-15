import os
import threading
import asyncio
from datetime import datetime, timezone
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from googlesearch import search
from dotenv import load_dotenv

load_dotenv()

# --- KEYS ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"status": "PastGlobeBot", "time": datetime.now(timezone.utc).isoformat()})

@app.route("/health")
def health():
    return "OK"

# --- Grok Answer ---
def get_grok_answer(question):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "HTTP-Referer": "https://t.me/PastGlobeBot",
        "X-Title": "PastGlobeBot",
        "Content-Type": "application/json"
    }
    data = {
        "model": "x-ai/grok-beta",
        "messages": [{"role": "user", "content": question + " (संक्षिप्त हिंदी में, November 2025 तक की latest info)"}]
    }
    try:
        r = requests.post(url, json=data, headers=headers, timeout=30)
        if r.status_code != 200:
            return f"API Error {r.status_code}"
        return r.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error: {str(e)}"

# --- Web Search ---
def web_search(query):
    try:
        results = list(search(query, num_results=2, lang="hi"))
        return "लेटेस्ट Info:\n" + "\n".join([f"• {r}" for r in results])
    except:
        return ""

# --- Telegram Bot ---
application = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("नमस्ते! लेटेस्ट जवाब मिलेगा!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text
    answer = get_grok_answer(user_msg)
    search = web_search(user_msg + " latest November 2025")
    if search:
        answer += "\n\n" + search
    await update.message.reply_text(answer)

def run_bot():
    global application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Telegram Bot Polling शुरू...")
    application.run_polling()

# --- Launch ---
if __name__ == "__main__":
    # Start Telegram Bot in background
    threading.Thread(target=run_bot, daemon=True).start()
    
    # Start Flask
    port = int(os.getenv("PORT", 10000))
    print(f"Flask LIVE on port {port}")
    app.run(host="0.0.0.0", port=port)
