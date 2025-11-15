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
import threading

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
app = Flask(__name__)

application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()


# ===== GROK ANSWER =====
def get_grok_answer(question):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
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
        return "❌ Error: API response issue."


# ===== WEB SEARCH =====
def web_search(query):
    try:
        results = list(search(query, num_results=2))
        return "🔍 लेटेस्ट जानकारी:\n" + "\n".join([f"• {r}" for r in results])
    except:
        return ""


# ===== HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("नमस्ते! PastGlobeBot आपका स्वागत करता है!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    answer = get_grok_answer(text)
    results = web_search(text + " latest")

    if results:
        answer += "\n\n" + results

    await update.message.reply_text(answer)


# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


# ===== WEBHOOK ROUTE =====
@app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    json_data = request.get_json(force=True)
    update = Update.de_json(json_data, bot)
    application.process_update(update)
    return "OK", 200


# ===== HOME ROUTE =====
@app.route("/", methods=["GET"])
def home():
    return {
        "status": "PastGlobeBot live",
        "server_time": datetime.now(timezone.utc).isoformat()
    }


# ===== SET WEBHOOK (Thread) =====
def set_webhook_async():
    webhook_url = f"https://pastglobebot.onrender.com/webhook/{TELEGRAM_TOKEN}"
    try:
        bot.delete_webhook()
        bot.set_webhook(url=webhook_url)
        print("Webhook set:", webhook_url)
    except Exception as e:
        print("Webhook error:", e)


# Set webhook on startup
threading.Thread(target=set_webhook_async).start()


# ===== RUN FLASK =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
