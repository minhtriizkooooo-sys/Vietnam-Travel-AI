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
<style>
body {{ margin:0; font-family: Arial, Helvetica, sans-serif; background:#f4f6f8; }}
header {{ background:#0b7a3b; color:white; padding:15px 20px; display:flex; align-items:center; justify-content:flex-start; flex-wrap:wrap; }}
header img {{ max-height:100px; width:auto; margin-right:20px; border-radius:8px; object-fit:contain; }}
main {{ max-width:1000px; margin:auto; padding:20px; }}
.chat-box {{ background:white; border-radius:8px; padding:15px; height:400px; max-height:60vh; overflow-y:auto; border:1px solid #ddd; line-height:1.6; font-size:14px; }}
.msg-user {{ text-align:right; color:#0b7a3b; margin:8px 0; }}
.msg-bot {{ text-align:left; color:#333; margin:8px 0; }}
.typing {{ color:#999; font-style:italic; }}
.input-area {{ display:flex; gap:10px; margin-top:12px; }}
input {{ flex:1; padding:12px; font-size:16px; }}
button {{ padding:12px 16px; border:none; cursor:pointer; background:#0b7a3b; color:white; }}
.secondary {{ background:#999; }}
.search-box {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:10px; margin-bottom:15px; }}
footer {{ margin-top:30px; padding:15px; background:#eee; font-size:14px; text-align:center; }}
a {{ color:#0b7a3b; text-decoration:none; }}
a:hover {{ text-decoration:underline; }}
img {{ max-width:100%; border-radius:6px; margin:5px 0; }}
.suggested button {{ margin:3px; padding:6px 10px; font-size:13px; }}
@media (max-width: 768px) {{
    header {{ flex-direction: column; align-items:flex-start; }}
    header img {{ max-height:60px; margin-bottom:10px; }}
    .input-area {{ flex-direction: column; gap:8px; }}
    .search-box {{ grid-template-columns: 1fr; }}
    .chat-box {{ height:50vh; max-height:50vh; }}
}}
</style>
</head>
<body>
<header>
    <img src="/static/Logo_Marie_Curie.png" alt="Logo">
    <h2>Vietnam Travel AI</h2>
</header>

<main>
<h3>Google Travel-style Search</h3>
<div class="search-box">
    <input id="city" placeholder="Thành phố (Đà Lạt, Phú Quốc…)">
    <input id="budget" placeholder="Ngân sách (VD: 10 triệu)">
    <input id="season" placeholder="Mùa (hè, đông…)">
    <button onclick="travelSearch()">Tìm kiếm</button>
</div>

<h3>Chat tư vấn du lịch</h3>
<div id="chat" class="chat-box"></div>

<div class="input-area">
    <input id="msg" placeholder="Hỏi lịch trình, chi phí, mùa đẹp nhất...">
    <button onclick="sendMsg()">Gửi</button>
    <button class="secondary" onclick="clearChat()">Xóa</button>
</div>

<div class="suggested" id="suggested"></div>
<div id="history" class="chat-box" style="margin-top:15px;"></div>

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
