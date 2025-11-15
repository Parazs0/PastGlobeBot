import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters
from googlesearch import search
from dotenv import load_dotenv
import requests
from datetime import datetime, timezone

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
app = Flask(__name__)

# Dispatcher
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=4)


# ========= GROK ANSWER =========
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
            {"role": "user", "content": question + " (संक्षिप्त हिंदी में, Daily updated info)"}
        ]
    }

    try:
        r = requests.post(url, json=data, headers=headers, timeout=30)
        if r.status_code != 200:
            return f"API Error {r.status_code}"
        return r.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error: {str(e)}"


# ========= WEB SEARCH =========
def web_search(query):
    try:
        results = list(search(query, num_results=2))
        return "🔍 लेटेस्ट जानकारी:\n" + "\n".join([f"• {r}" for r in results])
    except:
        return ""


# ========= COMMAND HANDLERS =========
def start(update, context):
    update.message.reply_text("नमस्ते! मैं PastGlobeBot हूँ — पूछिए कुछ भी!")


def handle_message(update, context):
    user_msg = update.message.text

    answer = get_grok_answer(user_msg)
    search_results = web_search(user_msg + " latest news")

    if search_results:
        answer += "\n\n" + search_results

    update.message.reply_text(answer)


dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


# ========= FLASK ROUTES =========

@app.route("/", methods=["GET"])
def home():
    return {
        "status": "PastGlobeBot",
        "time": datetime.now(timezone.utc).isoformat()
    }


# ======= CORRECT WEBHOOK ROUTE =======
@app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK", 200


# ========= SET WEBHOOK =========
@app.before_first_request
def set_webhook():
    webhook_url = f"https://pastglobebot.onrender.com/webhook/{TELEGRAM_TOKEN}"
    bot.delete_webhook()
    bot.set_webhook(url=webhook_url)


# ========= RUN =========
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
