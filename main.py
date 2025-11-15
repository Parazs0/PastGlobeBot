import os
import threading
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

# ----------------------
# LOAD ENV
# ----------------------
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
app = Flask(__name__)

# Telegram dispatcher
application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()


# ----------------------
# OPENROUTER ANSWER
# ----------------------
def get_openrouter_answer(question):
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": "x-ai/grok-beta",
        "messages": [
            {
                "role": "user",
                "content": question + " (संक्षिप्त हिंदी में जवाब दो)"
            }
        ],
    }

    try:
        r = requests.post(url, json=data, headers=headers, timeout=20)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ OpenRouter Error: {e}"


# ----------------------
# GOOGLE SEARCH
# ----------------------
def web_search(query):
    try:
        results = list(search(query, num_results=2))
        if not results:
            return ""
        return "🔍 वेब खोज:\n" + "\n".join([f"• {r}" for r in results])
    except:
        return ""


# ----------------------
# TELEGRAM HANDLERS
# ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("नमस्ते! PastGlobeBot आपकी मदद के लिए तैयार है।")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    ai_answer = get_openrouter_answer(text)
    google = web_search(text + " latest")

    if google:
        ai_answer += "\n\n" + google

    await update.message.reply_text(ai_answer)


application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


# ----------------------
# WEBHOOK ROUTE
# ----------------------
@app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        application.process_update(update)
    except Exception as e:
        print("Webhook error:", e)
    return "OK", 200


# ----------------------
# HOME ROUTE
# ----------------------
@app.route("/", methods=["GET"])
def home():
    return {
        "status": "PastGlobeBot Running",
        "time": datetime.now(timezone.utc).isoformat()
    }


# ----------------------
# SET WEBHOOK SAFE
# ----------------------
def set_webhook_async():
    try:
        webhook_url = f"https://pastglobebot.onrender.com/webhook/{TELEGRAM_TOKEN}"
        bot.delete_webhook()
        bot.set_webhook(url=webhook_url)
        print("Webhook set:", webhook_url)
    except Exception as e:
        print("Webhook setup failed:", e)


# THREAD TO AUTO-SET WEBHOOK
threading.Thread(target=set_webhook_async).start()


# ----------------------
# RUN SERVER
# ----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
