import os
from flask import Flask, request
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from googlesearch import search
import requests
from datetime import datetime, timezone

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")

# Telegram bot instance
bot = Bot(token=TELEGRAM_TOKEN)

# Flask app
app = Flask(__name__)

# Telegram Application (V20)
application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()


# ===== GROK ANSWER =====
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
        "messages": [
            {"role": "user", "content": question + " (संक्षिप्त हिंदी में, daily updated info)"}
        ]
    }

    try:
        r = requests.post(url, json=data, headers=headers, timeout=30)
        return r.json()['choices'][0]['message']['content']
    except:
        return "Server error. Try again."


# ===== WEB SEARCH =====
def web_search(query):
    try:
        results = list(search(query, num_results=2))
        return "🔍 लेटेस्ट जानकारी:\n" + "\n".join([f"• {r}" for r in results])
    except:
        return ""


# ===== COMMAND HANDLER =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("नमस्ते! मैं PastGlobeBot हूँ — पूछिए कुछ भी!")


# ===== MESSAGE HANDLER =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text

    answer = get_grok_answer(user_msg)
    search_results = web_search(user_msg)

    if search_results:
        answer += "\n\n" + search_results

    await update.message.reply_text(answer)


# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


# ===== FLASK ROUTES =====

@app.route("/", methods=["GET"])
def home():
    return {"status": "PastGlobeBot", "time": datetime.now(timezone.utc).isoformat()}


# Webhook route
@app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    json_data = request.get_json(force=True)
    update = Update.de_json(json_data, bot)
    application.process_update(update)
    return "OK", 200


# Set webhook when app starts
@app.before_first_request
def set_webhook():
    webhook_url = f"https://pastglobebot.onrender.com/webhook/{TELEGRAM_TOKEN}"
    bot.delete_webhook()
    bot.set_webhook(url=webhook_url)


# Run Flask
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
