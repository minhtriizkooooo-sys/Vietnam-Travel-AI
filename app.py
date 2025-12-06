from flask import Flask, request, jsonify, Response
import os
import requests

app = Flask(__name__)

# ========= ENV =========
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SITE_URL = os.getenv("SITE_URL", "https://vietnam-travel-ai.onrender.com")
HOTLINE = os.getenv("HOTLINE", "+84-908-08-3566")
BUILDER_NAME = os.getenv("BUILDER_NAME", "Vietnam Travel AI - Lại Nguyễn Minh Trí")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")          

# ========= HOME =========
@app.route("/", methods=["GET"])
def home():
    html = f"""
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Vietnam Travel AI</title>
<meta name="description" content="Tìm kiếm & tư vấn du lịch Việt Nam thông minh – lịch trình, giá cả, mùa đẹp nhất.">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{
    margin:0;
    font-family: Arial, Helvetica, sans-serif;
    background:#f4f6f8;
}}
header {{
    background:#0b7a3b;
    color:white;
    padding:12px 20px;
    display:flex;
    align-items:center;
}}
header img {{
    height:42px;
    margin-right:15px;
    border-radius:8px;
}}
main {{
    max-width:1000px;
    margin:auto;
    padding:20px;
}}
.chat-box {{
    background:white;
    border-radius:8px;
    padding:15px;
    height:420px;
    overflow-y:auto;
    border:1px solid #ddd;
}}
.user {{ text-align:right; color:#0b7a3b; margin:8px 0; }}
.bot {{ text-align:left; color:#333; margin:8px 0; }}
.typing {{ color:#999; font-style:italic; }}
.input-area {{
    display:flex;
    gap:10px;
    margin-top:12px;
}}
input {{
    flex:1;
    padding:12px;
    font-size:16px;
}}
button {{
    padding:12px 16px;
    border:none;
    cursor:pointer;
    background:#0b7a3b;
    color:white;
}}
.secondary {{
    background:#999;
}}
.search-box {{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
    gap:10px;
    margin-bottom:15px;
}}
footer {{
    margin-top:30px;
    padding:15px;
    background:#eee;
    font-size:14px;
    text-align:center;
}}
</style>
</head>

<body>
<header>
    <img src="/static/Logo_Marie_Curie.png" alt="Logo">
    <h2>Vietnam Travel AI</h2>
</header>

<main>

<h3>🔎 Google Travel-style Search</h3>
<div class="search-box">
    <input id="city" placeholder="Thành phố (Đà Nẵng, Phú Quốc…)">
    <input id="budget" placeholder="Ngân sách (VD: 10 triệu)">
    <input id="season" placeholder="Mùa (hè, đông…)">
    <button onclick="travelSearch()">Tìm kiếm</button>
</div>

<h3>💬 Chat tư vấn du lịch</h3>
<div id="chat" class="chat-box"></div>

<div class="input-area">
    <input id="msg" placeholder="Hỏi lịch trình, chi phí, mùa đẹp nhất...">
    <button onclick="sendMsg()">Gửi</button>
    <button class="secondary" onclick="clearChat()">Xóa</button>
</div>

</main>

<footer>
© 2025 – <strong>{BUILDER_NAME}</strong> | Hotline: <strong>{HOTLINE}</strong>
</footer>

<script>
function el(id){{return document.getElementById(id)}}

const chat = el("chat");

function appendUser(t){{chat.innerHTML += `<div class='user'>${{t}}</div>`}}
function appendBot(t){{chat.innerHTML += `<div class='bot'>${{t}}</div>`}}
function typing(){{chat.innerHTML += `<div id="typing" class="typing">Đang tìm thông tin...</div>`}}
function stopTyping(){{let t=el("typing"); if(t)t.remove();}}

function sendMsg(){{
    let text = el("msg").value.trim();
    if(!text) return;
    appendUser(text);
    el("msg").value = "";
    typing();

    fetch("/chat", {{
        method:"POST",
        headers:{{"Content-Type":"application/json"}},
        body:JSON.stringify({{message:text}})
    }})
    .then(r=>r.json())
    .then(d=>{{stopTyping(); appendBot(d.reply)}})
    .catch(()=>{{stopTyping(); appendBot("Lỗi kết nối server")}})
}}

function travelSearch(){{
    let q = `Du lịch ${{el("city").value}} ngân sách ${{el("budget").value}} mùa ${{el("season").value}}`;
    el("msg").value = q;
    sendMsg();
}}

function clearChat(){{chat.innerHTML="";}}
</script>

</body>
</html>
"""
    return Response(html, mimetype="text/html")

# ========= CHAT API =========
@app.route("/chat", methods=["POST"])
def chat_api():
    data = request.json or {}
    msg = data.get("message","").strip()
    if not msg:
        return jsonify({"reply":"Vui lòng nhập nội dung."})

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role":"system","content":
            "Bạn là chuyên gia du lịch Việt Nam. Trả lời rõ ràng, có lịch trình, giá tham khảo, thời điểm đẹp nhất, bullet points."},
            {"role":"user","content": msg}
        ],
        "temperature":0.6
    }

    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type":"application/json"
            },
            json=payload,
            timeout=60
        )
        reply = r.json()["choices"][0]["message"]["content"]
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply":"Hệ thống đang bận, thử lại sau."})

# ========= RUN =========
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
