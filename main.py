# main.py
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

# Load env (Render पर भी ठीक)
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")

app = Flask(__name__)

# -------------------------
#        FLASK ROUTES
# -------------------------
@app.route("/")
def home():
    return jsonify({
        "status": "PastGlobeBot",
        "time": datetime.now(timezone.utc).isoformat()
    })

@app.route("/health")
def health():
    return "OK"


# -------------------------
#      GROK ANSWER API
# -------------------------
def get_grok_answer(question):
    """Blocking: runs inside async executor"""
    
    # 📌 Auto-detected today's date for daily updated info
    today = datetime.now().strftime("%d %B %Y")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Referer": "https://t.me/PastGlobeBot",
        "X-Title": "PastGlobeBot",
        "Content-Type": "application/json"
    }

    data = {
        "model": "x-ai/grok-beta",
        "messages": [
            {
                "role": "user",
                "content": (
                    f"{question} "
                    f"(संक्षिप्त हिंदी में, {today} तक की ताज़ा जानकारी)"
                )
            }
        ]
    }

    try:
        r = requests.post(url, json=data, headers=headers, timeout=60)
        if r.status_code != 200:
            return f"API Error {r.status_code}"

        j = r.json()
        return j.get("choices", [{}])[0].get("message", {}).get("content", "No content")

    except Exception as e:
        return f"Error: {str(e)}"


# -------------------------
#         WEB SEARCH
# -------------------------
def web_search(query):
    """Blocking: runs inside async executor"""
    try:
        results = list(search(query, num_results=2, lang="hi"))
        if results:
            return "लेटेस्ट वेब रिज़ल्ट्स:\n" + "\n".join(f"• {r}" for r in results)
        return ""
    except:
        return ""


# -------------------------
#       TELEGRAM BOT
# -------------------------
application = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("नमस्ते! मैं आपको ताज़ा अपडेट के साथ मदद करूँगा।")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text or ""

    loop = asyncio.get_event_loop()

    # Run blocking tasks async-safe
    grok_answer = await loop.run_in_executor(None, get_grok_answer, user_msg)
    search_result = await loop.run_in_executor(
        None, web_search, user_msg + " latest news"
    )

    final_reply = grok_answer or "उत्तर प्राप्त नहीं हुआ।"

    if search_result:
        final_reply += "\n\n" + search_result

    await update.message.reply_text(final_reply)


def run_bot():
    global application

    if not TELEGRAM_TOKEN:
        print("ERROR: TELEGRAM_TOKEN missing!")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("Telegram Bot Polling शुरू...")
    application.run_polling()


# -------------------------
#       ENTRY POINT
# -------------------------
if __name__ == "__main__":

    # Start Telegram polling bot in background thread
    threading.Thread(target=run_bot, daemon=True).start()

    # Start Flask (Render provides $PORT)
    port = int(os.getenv("PORT", "10000"))
    print(f"Flask LIVE on port {port}")

    app.run(host="0.0.0.0", port=port)
