from flask import Flask, request, jsonify, Response, send_file
import os
import requests
import io
from fpdf import FPDF

app = Flask(__name__)

# ========= ENV =========
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
SITE_URL = os.getenv("SITE_URL", "https://vietnam-travel-ai.onrender.com")
HOTLINE = os.getenv("HOTLINE", "+84-908-08-3566")
BUILDER_NAME = os.getenv("BUILDER_NAME", "Vietnam Travel AI – Minh Trí")


# ========= GOOGLE SEARCH =========
def google_image_search(query, num=3):
    try:
        url = f"https://serpapi.com/search.json?q={query}&tbm=isch&num={num}&api_key={SERPAPI_KEY}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        results = r.json().get("images_results", [])
        return [item["original"] for item in results if "original" in item]
    except:
        return []


def youtube_search(query, num=2):
    try:
        url = f"https://serpapi.com/search.json?q={query}&tbm=vid&num={num}&api_key={SERPAPI_KEY}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        results = r.json().get("video_results", [])
        return [item["link"] for item in results if "link" in item]
    except:
        return []


# ========= HOME =========
@app.route("/", methods=["GET"])
def home():
    html = """
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Vietnam Travel AI</title>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
body {
    background:#f7f7f8;
    margin:0;
    font-family: Inter, "Segoe UI", Arial;
    color:#111;
}

/* ===== HEADER ===== */
header {
    background:white;
    padding:14px 22px;
    border-bottom:1px solid #e5e5e5;
    display:flex;
    align-items:center;
    gap:14px;
}
header img {
    height:42px;
}
header h1 {
    font-size:20px;
    margin:0;
    font-weight:700;
}

/* ===== MAIN CONTAINER ===== */
.container {
    max-width:820px;
    margin:0 auto;
    padding:20px 12px;
}

/* ===== CHAT BOX STYLE A (ChatGPT-like) ===== */
.chat-box {
    background:white;
    border-radius:14px;
    padding:20px;
    height:480px;
    overflow-y:auto;
    border:1px solid #ddd;
    box-shadow:0 4px 20px rgba(0,0,0,0.04);
}

.bubble-user {
    background:#0c7d42;
    color:white;
    padding:12px 14px;
    border-radius:12px;
    margin:14px 0;
    max-width:75%;
    margin-left:auto;
    white-space:pre-wrap;
}

.bubble-bot {
    background:#f2f2f2;
    padding:12px 14px;
    border-radius:12px;
    margin:14px 0;
    max-width:75%;
    white-space:pre-wrap;
}

/* suggestions */
#suggested {
    margin-top:12px;
    display:flex;
    flex-wrap:wrap;
    gap:8px;
}
.suggestion-btn {
    background:white;
    border:1px solid #ddd;
    border-radius:14px;
    padding:8px 12px;
    cursor:pointer;
    font-size:14px;
}
.suggestion-btn:hover {
    background:#f2f2f2;
}

/* input box */
.input-area {
    margin-top:16px;
    display:flex;
    gap:8px;
}
.input-area input {
    flex:1;
    padding:12px 14px;
    border-radius:12px;
    border:1px solid #ccc;
}
.input-area button {
    padding:12px 16px;
    background:#0c7d42;
    color:white;
    border:0;
    border-radius:12px;
    cursor:pointer;
    font-weight:600;
}

/* footer */
footer {
    text-align:center;
    margin-top:20px;
    color:#777;
    font-size:13px;
}
</style>
</head>

<body>

<header>
    <img src="/static/Logo_Marie_Curie.png">
    <h1>Vietnam Travel AI</h1>
</header>

<div class="container">

    <div id="chat" class="chat-box"></div>

    <div id="suggested"></div>

    <div class="input-area">
        <input id="msg" placeholder="Hãy hỏi lịch trình, khách sạn, chi phí, mùa đẹp nhất...">
        <button onclick="sendMsg()">Gửi</button>
    </div>

    <footer>
        Hotline: <b>__HOTLINE__</b><br>
        © 2025 – <b>__BUILDER__</b>
    </footer>

</div>

<script src="/static/chat.js"></script>

</body>
</html>
"""
    html = html.replace("__HOTLINE__", HOTLINE)
    html = html.replace("__BUILDER__", BUILDER_NAME)
    return Response(html, mimetype="text/html")


# ========= CHAT API =========
@app.route("/chat", methods=["POST"])
def chat_api():
    data = request.json or {}
    msg = data.get("msg", "").strip()

    if not msg:
        return jsonify({"reply": "Bạn cần nhập nội dung."})

    system_prompt = (
        "Bạn là chuyên gia du lịch Việt Nam và thế giới. Trả lời với format:\n"
        "1) Thời gian\n"
        "2) Lịch trình\n"
        "3) Chi phí\n"
        "4) Hình ảnh minh họa và video\n"
        "Không dùng HTML."
    )

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": msg}
        ],
        "temperature": 0.6
    }

    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json=payload,
            timeout=60
        )

        resp = r.json()
        reply = resp["choices"][0]["message"]["content"]

        image_queries = []
        video_queries = []
        for line in reply.splitlines():
            if line.startswith("- Hình ảnh minh họa:"):
                q = line.replace("- Hình ảnh minh họa:", "").strip()
                if q: image_queries.append(q)
            if line.startswith("- Video tham khảo:"):
                q = line.replace("- Video tham khảo:", "").strip()
                if q: video_queries.append(q)

        images = []
        videos = []
        for x in image_queries:
            images.extend(google_image_search(x, 2))
        for x in video_queries:
            videos.extend(youtube_search(x, 2))

        suggestions = [
            "Tính chi phí chi tiết?",
            "Gợi ý lịch trình tối ưu hơn?",
            "Đi mùa này có đẹp không?",
            "Có món đặc sản nào nên thử?"
        ]

        return jsonify({
            "reply": reply,
            "images": images,
            "videos": videos,
            "suggested": suggestions
        })

    except Exception as e:
        print("CHAT ERROR:", e)
        return jsonify({"reply": "Lỗi hệ thống. Thử lại sau."})


# ========= EXPORT PDF =========
@app.route("/export-pdf", methods=["POST"])
def export_pdf():
    data = request.json or {}
    history = data.get("history", [])

    if not history:
        return jsonify({"error": "Không có dữ liệu."}), 400

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Lịch trình du lịch", ln=True, align="C")
    pdf.ln(6)
    pdf.set_font("Arial", "", 12)

    for item in history:
        user_text = item.get("msg", "")
        bot_text = item.get("reply", "")

        pdf.set_text_color(0, 70, 140)
        pdf.multi_cell(0, 7, "Q: " + user_text)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 7, "A: " + bot_text)
        pdf.ln(3)

    pdf_bytes = pdf.output(dest="S").encode("latin1")
    buf = io.BytesIO(pdf_bytes)
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", download_name="Lich_trinh.pdf", as_attachment=True)


# ========= RUN =========
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
