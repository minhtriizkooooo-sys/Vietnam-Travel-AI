from flask import Flask, request, jsonify, Response, send_file
import os
import requests
from fpdf import FPDF
from io import BytesIO

app = Flask(__name__)

# ========= ENV =========
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
SITE_URL = os.getenv("SITE_URL", "https://vietnam-travel-ai.onrender.com")
HOTLINE = os.getenv("HOTLINE", "+84-908-08-3566")
BUILDER_NAME = os.getenv("BUILDER_NAME", "Vietnam Travel AI - Lại Nguyễn Minh Trí")

# ========= GOOGLE IMAGE & VIDEO SEARCH =========
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
    html = f"""
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Vietnam Travel AI</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
<style>
body {{
    margin:0;
    font-family: 'Roboto', sans-serif;
    background:#f5f7fa;
    color:#333;
}}
header {{
    background:#0b7a3b;
    color:white;
    padding:15px 30px;
    display:flex;
    align-items:center;
    justify-content:space-between;
    flex-wrap:wrap;
    box-shadow:0 2px 5px rgba(0,0,0,0.1);
}}
header h1 {{
    margin:0;
    font-weight:700;
    font-size:24px;
}}
header img {{
    height:60px;
    border-radius:8px;
}}
main {{
    max-width:1000px;
    margin:auto;
    padding:20px;
}}
section {{
    background:white;
    border-radius:10px;
    padding:20px;
    margin-bottom:20px;
    box-shadow:0 2px 5px rgba(0,0,0,0.05);
}}
h2 {{
    margin-top:0;
    font-size:20px;
    color:#0b7a3b;
}}
.search-box {{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
    gap:10px;
    margin-top:10px;
}}
.search-box input, .input-area input {{
    padding:12px;
    border-radius:6px;
    border:1px solid #ccc;
    font-size:14px;
}}
button {{
    padding:12px;
    border:none;
    border-radius:6px;
    cursor:pointer;
    background:#0b7a3b;
    color:white;
    font-weight:500;
    transition:0.2s;
}}
button:hover {{
    background:#095a2a;
}}
.secondary {{
    background:#888;
}}
.chat-box {{
    background:#fdfdfd;
    border-radius:8px;
    padding:15px;
    height:400px;
    max-height:60vh;
    overflow-y:auto;
    border:1px solid #ddd;
    line-height:1.6;
    font-size:14px;
}}
.msg-user {{ text-align:right; color:#0b7a3b; margin:8px 0; }}
.msg-bot {{ text-align:left; color:#333; margin:8px 0; }}
.typing {{ color:#999; font-style:italic; }}
.input-area {{
    display:flex;
    gap:10px;
    margin-top:12px;
    flex-wrap:wrap;
}}
.suggested {{
    margin-top:10px;
}}
.suggested button {{
    margin:5px 5px 0 0;
    font-size:13px;
}}
#history {{
    max-height:200px;
    overflow-y:auto;
}}
footer {{
    text-align:center;
    padding:15px;
    font-size:14px;
    background:#eee;
    margin-top:30px;
    border-top:1px solid #ddd;
}}
a {{ color:#0b7a3b; text-decoration:none; }}
a:hover {{ text-decoration:underline; }}
img {{ max-width:100%; border-radius:6px; margin:5px 0; }}
@media(max-width:768px){{
    .search-box, .input-area {{ grid-template-columns:1fr; display:block; }}
    .input-area input {{ width:100%; margin-bottom:10px; }}
    header {{ flex-direction:column; align-items:flex-start; gap:10px; }}
}}
</style>
</head>
<body>
<header>
    <img src="/static/Logo_Marie_Curie.png" alt="Logo">
    <h1>Vietnam Travel AI</h1>
</header>

<main>
<section>
<h2>🔍 Tìm kiếm du lịch</h2>
<div class="search-box">
    <input id="city" placeholder="Thành phố (Đà Lạt, Phú Quốc…)">
    <input id="budget" placeholder="Ngân sách (VD: 10 triệu)">
    <input id="season" placeholder="Mùa (hè, đông…)">
    <button onclick="travelSearch()">Tìm kiếm</button>
</div>
</section>

<section>
<h2>💬 Chat tư vấn du lịch</h2>
<div id="chat" class="chat-box"></div>
<div class="input-area">
    <input id="msg" placeholder="Hỏi lịch trình, chi phí, mùa đẹp nhất...">
    <button onclick="sendMsg()">Gửi</button>
    <button class="secondary" onclick="clearChat()">Xóa</button>
</div>
<div class="suggested" id="suggested"></div>
<div id="history" class="chat-box"></div>
</section>

</main>

<footer>
© 2025 – <strong>{BUILDER_NAME}</strong> | Hotline: <strong>{HOTLINE}</strong>
</footer>

<script src="/static/chat.js"></script>
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
        return jsonify({"reply":"Vui lòng nhập nội dung.", "images":[], "videos":[]})

    prompt = (
        "Bạn là chuyên gia du lịch Việt Nam và thế giới. Trả lời **text chuẩn**, phân chia khoa học:\n"
        "- Tiêu đề rõ ràng: Thời gian, Lịch trình, Chi phí, Hình ảnh & Video\n"
        "- Mỗi ngày: liệt kê chi tiết bullet points\n"
        "- KHÔNG dùng HTML, KHÔNG iframe, không tự tạo link hình/video\n"
        "- Dễ đọc, chuyên nghiệp"
    )

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role":"system","content": prompt},
            {"role":"user","content": msg}
        ],
        "temperature":0.6
    }

    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}","Content-Type":"application/json"},
            json=payload,
            timeout=60
        )
        ai_text = r.json()["choices"][0]["message"]["content"]

        # --- Extract keywords for images/videos ---
        image_queries, video_queries = [], []
        for line in ai_text.splitlines():
            if "- Hình ảnh minh họa:" in line:
                q = line.split(":")[1].strip()
                if q: image_queries.append(q)
            if "- Video tham khảo:" in line:
                q = line.split(":")[1].strip()
                if q: video_queries.append(q)

        images = []
        for q in image_queries:
            imgs = google_image_search(q, num=1)
            images.extend(imgs)

        videos = []
        for q in video_queries:
            vids = youtube_search(q, num=1)
            videos.extend(vids)

        return jsonify({"reply": ai_text, "images": images, "videos": videos})

    except Exception as e:
        print(e)
        return jsonify({"reply":"Hệ thống đang bận, thử lại sau.", "images":[], "videos":[]})

# ========= EXPORT PDF =========
@app.route("/export-pdf", methods=["POST"])
def export_pdf():
    data = request.json or {}
    content = data.get("content","").strip()
    images = data.get("images", [])
    videos = data.get("videos", [])

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.multi_cell(0, 10, "Lịch trình du lịch")
    pdf.ln(5)
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, content)

    # Thêm hình ảnh
    for url in images:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                pdf.add_page()
                img_bytes = BytesIO(r.content)
                pdf.image(img_bytes, x=15, w=180)
        except:
            continue

    # Thêm video link
    if videos:
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.multi_cell(0, 10, "Video tham khảo")
        pdf.set_font("Arial", "", 12)
        for v in videos:
            pdf.multi_cell(0, 8, v)

    buf = BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="Lich_trinh_du_lich.pdf", mimetype="application/pdf")

# ========= RUN =========
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
