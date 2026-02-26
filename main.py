import os
from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

import google.generativeai as genai

LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if LINE_CHANNEL_SECRET is None or LINE_CHANNEL_ACCESS_TOKEN is None:
    raise ValueError("請設定 LINE_CHANNEL_SECRET 和 LINE_CHANNEL_ACCESS_TOKEN")

if GEMINI_API_KEY is None:
    raise ValueError("請設定 GEMINI_API_KEY")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

genai.configure(api_key=GEMINI_API_KEY)  # type: ignore
gemini_model = genai.GenerativeModel("gemini-flash-latest")  # type: ignore

app = Flask(__name__)


@app.route("/", methods=["GET"])
def home():
    return "LINE 機器人運行中", 200


@app.route("/callback", methods=["GET"])
def callback_get():
    return "OK", 200


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event: MessageEvent):
    user_text = event.message.text
    prompt = f"""你是一個翻譯助手。判斷下面這段文字是繁體中文還是英文，如果是繁體中文就翻譯成自然流暢的英文，如果是英文就翻譯成自然流暢的繁體中文。只輸出翻譯結果，不要加任何說明或標註。

待翻譯文字：
{user_text}
"""
    try:
        response = gemini_model.generate_content(prompt)
        translated_text = response.text.strip() or "翻譯結果為空，請再試一次。"
    except Exception as e:
        print("Gemini 錯誤：", e)
        translated_text = "抱歉，翻譯服務發生錯誤，請稍後再試。"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=translated_text))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
