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
BUILDER_NAME = os.getenv("BUILDER_NAME", "Vietnam Travel AI - Lại Nguyễn Minh Trí")


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
    # Không dùng format, không dùng f-string để tránh lỗi CSS { }
    html = """
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Vietnam Travel AI</title>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
body {{ margin:0; font-family: Arial, Helvetica, sans-serif; background:#e0f7fa; }}
header {{ background:#0b7a3b; color:white; padding:15px 20px; display:flex; align-items:center; justify-content:flex-start; flex-wrap:wrap; }}
header img {{ max-height:100px; width:auto; margin-right:20px; border-radius:8px; object-fit:contain; }}
main {{ max-width:1000px; margin:auto; padding:20px; }}
.chat-box {{ background:white; border-radius:8px; padding:15px; height:500px; max-height:70vh; overflow-y:auto; border:1px solid #ddd; line-height:1.6; font-size:14px; }}
.user {{ text-align:right; color:#0b7a3b; margin:8px 0; }}
.bot {{ text-align:left; color:#333; margin:8px 0; }}
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



.modal {{
    display:none;
    position: fixed;
    z-index: 1000;
    padding-top: 60px;
    left:0; top:0; width:100%; height:100%;
    overflow:auto; background-color: rgba(0,0,0,0.4);
}}
.modal-content {{
    background-color: #fefefe;
    margin: auto;
    padding: 20px;
    border:1px solid #888;
    width: 80%;
    max-height:80vh;
    overflow-y:auto;
    border-radius:8px;
}}
.close-modal {{
    color: #aaa;
    float:right;
    font-size:28px;
    font-weight:bold;
    cursor:pointer;
}}
.close-modal:hover {{ color: black; }}

@media (max-width: 768px) {{
    header {{ flex-direction: column; align-items:flex-start; }}
    header img {{ max-height:60px; margin-bottom:10px; }}
    .input-area {{ flex-direction: column; gap:8px; }}
    .search-box {{ grid-template-columns: 1fr; }}
    .chat-box {{ height:60vh; max-height:60vh; }}
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
    <input id="city" placeholder="Thành phố (Hà Nội, Đà Nẵng, Đà Lạt, Phú Quốc…)">
    <input id="budget" placeholder="Ngân sách (VD: , 20 triệu, 10 triệu...)">
    <input id="season" placeholder="Mùa (hè, đông…)">
    <button onclick="travelSearch()">Tìm kiếm</button>
</div>

<h3>Chat tư vấn du lịch</h3>
<div id="chat" class="chat-box"></div>

<div class="input-area">
    <input id="msg" placeholder="Hỏi lịch trình, chi phí, mùa đẹp nhất...">
    <button onclick="sendMsg()">Gửi</button>
    <button class="secondary" onclick="clearChat()">Xóa</button>
    <button class="secondary" onclick="showHistory()">Lịch sử chat</button>
    <button class="secondary" onclick="exportPDF()">Xuất PDF</button>
</div>
</main>

<div id="historyModal" class="modal">
    <div class="modal-content">
        <span class="close-modal" onclick="closeHistory()">&times;</span>
        <h3>Lịch sử chat</h3>
        <div id="historyContent"></div>
    </div>
</div>

<footer>
© 2025 – <strong>__BUILDER__</strong> | Hotline: <strong>__HOTLINE__</strong>
</footer>

<script src="/static/chat.js"></script>

</body>
</html>
"""

    # Thay thế biến safely
    html = html.replace("__BUILDER__", BUILDER_NAME)
    html = html.replace("__HOTLINE__", HOTLINE)

    return Response(html, mimetype="text/html")


# ========= CHAT API =========
@app.route("/chat", methods=["POST"])
def chat_api():
    data = request.json or {}
    msg = data.get("message", "").trim() if hasattr(str, "trim") else data.get("message", "").strip()

    if not msg:
        return jsonify({"reply": "Vui lòng nhập nội dung."})

    # --- AI TEXT RESPONSE ---
    
    prompt = (
        "Bạn là chuyên gia du lịch Việt Nam và thế giới. Trả lời **text chuẩn**, phân chia khoa học:\n"
        "- Tiêu đề rõ ràng: Thời gian, Lịch trình, Chi phí, Hình ảnh & Video\n"
        "- Mỗi ngày: liệt kê chi tiết bullet points\n"
        "- KHÔNG dùng HTML, KHÔNG iframe, không tự tạo link hình/video\n"
        "- Dễ đọc, chuyên nghiệp, ví dụ:\n"
        "Ngày 1: ...\n- Hình ảnh minh họa: Đà Lạt Hồ Xuân Hương\n- Video tham khảo: Đà Lạt"
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
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type":"application/json"
            },
            json=payload,
            timeout=60
        )
        ai_text = r.json()["choices"][0]["message"]["content"]

        # --- Extract keywords for images/videos (simple: lines with "Hình ảnh"/"Video") ---
        image_queries = []
        video_queries = []
        for line in ai_text.splitlines():
            if line.strip().startswith("- Hình ảnh minh họa:"):
                q = line.replace("- Hình ảnh minh họa:", "").strip()
                if q: image_queries.append(q)
            if line.strip().startswith("- Video tham khảo:"):
                q = line.replace("- Video tham khảo:", "").strip()
                if q: video_queries.append(q)

        # --- Search real images & videos via SerpAPI ---
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
    history = data.get("history", [])

    if not history:
        return jsonify({"error": "No content to export."})

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Lịch Trình Du Lịch", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "", 12)

    for item in reversed(history):
        pdf.set_text_color(2, 119, 189)
        pdf.multi_cell(0, 7, "Q: " + item.get("user", ""))
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 7, "A: " + item.get("bot", ""))
        pdf.ln(3)

    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)
    return send_file(output, download_name="Lich_trinh_du_lich.pdf", as_attachment=True)


# ========= RUN =========
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
