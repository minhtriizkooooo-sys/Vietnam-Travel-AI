from flask import Flask, request, jsonify, Response, send_file
import os
import requests
from fpdf import FPDF

app = Flask(__name__)

# ========= ENV =========
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
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
<link rel="stylesheet" href="/static/style.css">
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

<h3>Lịch sử chat</h3>
<div id="history" class="chat-box"></div>

<div class="input-area">
    <input id="msg" placeholder="Hỏi lịch trình, chi phí, mùa đẹp nhất...">
    <button onclick="sendMsg()">Gửi</button>
    <button class="secondary" onclick="clearChat()">Xóa</button>
</div>
<div id="suggested" class="input-area"></div>
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
        "Bạn là chuyên gia du lịch Việt Nam. Trả lời chuẩn, phân chia khoa học:\n"
        "- Tiêu đề rõ ràng: Thời gian, Lịch trình, Chi phí, Hình ảnh & Video\n"
        "- Mỗi ngày: bullet points\n"
        "- Không dùng HTML, không tạo link hình/video\n"
        "- Ví dụ:\nNgày 1: ...\n- Hình ảnh minh họa: Đà Lạt Hồ Xuân Hương\n- Video tham khảo: Đà Lạt"
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
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}",
                     "Content-Type":"application/json"},
            json=payload,
            timeout=60
        )
        ai_text = r.json()["choices"][0]["message"]["content"]

        # --- Extract keywords for images/videos ---
        image_queries = []
        video_queries = []
        for line in ai_text.splitlines():
            if line.strip().startswith("- Hình ảnh minh họa:"):
                q = line.replace("- Hình ảnh minh họa:", "").strip()
                if q: image_queries.append(q)
            if line.strip().startswith("- Video tham khảo:"):
                q = line.replace("- Video tham khảo:", "").strip()
                if q: video_queries.append(q)

        # --- Search real images & videos ---
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
    content = data.get("content", "")
    images = data.get("images", [])
    videos = data.get("videos", [])

    pdf = FPDF()
    pdf.add_page()
    font_path = os.path.join(os.getcwd(), "static/fonts/DejaVuSans.ttf")
    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.set_font("DejaVu", "", 14)
    pdf.multi_cell(0, 8, content)
    pdf.ln(5)

    # Hình ảnh
    for img_url in images:
        try:
            resp = requests.get(img_url, stream=True, timeout=10)
            if resp.status_code == 200:
                img_file = os.path.join("/tmp", os.path.basename(img_url))
                with open(img_file, "wb") as f:
                    f.write(resp.content)
                pdf.image(img_file, w=pdf.epw/2)
                pdf.ln(5)
        except: pass

    # Video
    if videos:
        pdf.set_font("DejaVu", "", 12)
        pdf.multi_cell(0, 6, "Video tham khảo:")
        for v in videos:
            pdf.set_text_color(0,0,255)
            pdf.multi_cell(0, 6, v)
        pdf.set_text_color(0,0,0)

    pdf_file = "/tmp/lich_trinh.pdf"
    pdf.output(pdf_file)
    return send_file(pdf_file, as_attachment=True, download_name="Lich_trinh_du_lich.pdf")

# ========= RUN =========
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
