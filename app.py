from flask import Flask, request, jsonify
import os
import requests
from string import Template

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
HOTLINE = os.getenv("HOTLINE", "+84-908-08-3566")
BUILDER_NAME = os.getenv("BUILDER_NAME", "Vietnam Travel AI - Lại Nguyễn Minh Trí")


@app.route("/", methods=["GET"])
def home():

    html_tpl = Template(r"""
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Vietnam Travel AI</title>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
body {
    margin: 0;
    font-family: Arial, Helvetica, sans-serif;
    background: #f4f6f8;
}
header {
    background: #0b7a3b;
    color: white;
    padding: 12px 20px;
    display: flex;
    align-items: center;
}
header img {
    height: 48px;
    margin-right: 15px;
    border-radius: 8px;
}
main {
    padding: 20px;
    max-width: 900px;
    margin: auto;
}
.chat-box {
    background: white;
    border-radius: 8px;
    padding: 15px;
    height: 400px;
    overflow-y: auto;
    border: 1px solid #ddd;
}
.user {
    text-align: right;
    color: #0b7a3b;
    margin: 8px 0;
}
.bot {
    text-align: left;
    color: #333;
    margin: 8px 0;
}
.input-area {
    display: flex;
    margin-top: 10px;
}
.input-area input {
    flex: 1;
    padding: 10px;
    font-size: 16px;
}
.input-area button {
    padding: 10px 15px;
    font-size: 16px;
    background: #0b7a3b;
    color: white;
    border: none;
    cursor: pointer;
}
footer {
    margin-top: 30px;
    text-align: center;
    color: #666;
    font-size: 14px;
    padding: 15px;
}
</style>
</head>

<body>
<header>
    <img src="/static/Logo_Marie_Curie.png" alt="Logo">
    <h2>Vietnam Travel AI</h2>
</header>

<main>
    <h3>Tư vấn du lịch thông minh 🇻🇳</h3>
    <div id="chat" class="chat-box"></div>

    <div class="input-area">
        <input id="msg" type="text" placeholder="Hỏi về địa điểm, lịch trình, chi phí...">
        <button onclick="sendMsg()">Gửi</button>
    </div>
</main>

<footer>
    © 2025 – Thực hiện bởi <strong>$builder</strong> |
    Hotline: <strong>$hotline</strong>
</footer>

<script>
const chat = document.getElementById("chat");
const input = document.getElementById("msg");

function appendUser(text){
    chat.innerHTML += `<div class="user">$${text}</div>`;
    chat.scrollTop = chat.scrollHeight;
}

function appendBot(text){
    chat.innerHTML += `<div class="bot">$${text}</div>`;
    chat.scrollTop = chat.scrollHeight;
}

function sendMsg(){
    const text = input.value.trim();
    if(!text) return;
    appendUser(text);
    input.value = "";

    fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message: text})
    })
    .then(res => res.json())
    .then(data => appendBot(data.reply || "Lỗi hệ thống"))
    .catch(() => appendBot("Không kết nối được server"));
}
</script>

</body>
</html>
""")

    return html_tpl.safe_substitute(
        hotline=HOTLINE,
        builder=BUILDER_NAME
    )


@app.route("/chat", methods=["POST"])
def chat_api():
    data = request.json or {}
    msg = data.get("message", "").strip()
    if not msg:
        return jsonify({"reply": "Bạn vui lòng nhập nội dung."})

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Bạn là trợ lý tư vấn du lịch Việt Nam chuyên nghiệp."},
            {"role": "user", "content": msg}
        ],
        "temperature": 0.7
    }

    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        reply = r.json()["choices"][0]["message"]["content"]
        return jsonify({"reply": reply})
    except Exception:
        return jsonify({"reply": "Hệ thống đang bận, vui lòng thử lại sau."})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
