import os
import threading
import asyncio
from datetime import datetime, timezone
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from googlesearch import search
from dotenv import load_dotenv  # local .env के लिए

# --- Load .env (local only) ---
load_dotenv()

# --- KEYS (Render पर env vars, local पर .env) ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")

# Flask
app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"status": "PastGlobeBot", "time": datetime.now(timezone.utc).isoformat()})

@app.route("/health")
def health():
    return "OK"

@app.route("/ping")
def ping():
    return "pong"

# --- Grok Real-Time Answer ---
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
            return f"सॉरी, API में दिक्कत है। (Status: {r.status_code})"
        return r.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"सॉरी, अभी दिक्कत है। ({str(e)})"

# --- Web Search (Extra Real-Time) ---
def web_search(query):
    try:
        results = list(search(query, num_results=2, lang="hi"))
        return "लेटेस्ट Info:\n" + "\n".join([f"• {r}" for r in results])
    except:
        return "Web search failed।"

# --- Telegram Bot ---
application = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "नमस्ते! \n"
        "मुझसे कुछ भी पूछो – **November 2025 तक की लेटेस्ट जानकारी** मिलेगी!\n\n"
        "उदाहरण: महाराष्ट्र के CM कौन हैं?"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text
    grok_answer = get_grok_answer(user_msg)
    search_info = web_search(user_msg + " latest news November 2025")
    final_answer = grok_answer
    if search_info and "failed" not in search_info:
        final_answer += "\n\n" + search_info
    await update.message.reply_text(final_answer)

def start_telegram_bot():
    global application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print("Telegram Bot LIVE!")
    loop.run_until_complete(application.run_polling())

# --- Daily Morning Update ---
def daily_update():
    print("Daily Update शुरू!")
    while True:
        now = datetime.now()
        if now.hour == 8 and now.minute == 0:
            news = web_search("आज की मुख्य खबरें भारत November 2025")
            # Add user IDs to send
            # application.bot.send_message(chat_id=123456789, text=news)
        threading.Event().wait(60)

# --- Launch ---
if __name__ == "__main__":
    threading.Thread(target=daily_update, daemon=True).start()
    threading.Thread(target=start_telegram_bot, daemon=True).start()
    port = int(os.getenv("PORT", 10000))
    print(f"Flask running on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
