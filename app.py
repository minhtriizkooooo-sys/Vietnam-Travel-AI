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
    # Giữ nguyên UI nhưng chỉnh chatbox nhỏ gọn hơn và logo gọn
    html = """
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Vietnam Travel AI</title>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
/* Layout cơ bản */
body { margin:0; font-family: Inter, "Segoe UI", Roboto, Arial, Helvetica, sans-serif; background:#eef7f2; color:#1b1b1b; }
.container { max-width:1100px; margin:20px auto; padding:12px; }

/* Header */
header { background:#0b7a3b; color:white; padding:12px 18px; display:flex; align-items:center; gap:14px; border-radius:10px; }
header img { max-height:48px; width:auto; margin-right:8px; border-radius:6px; object-fit:contain; box-shadow: 0 1px 2px rgba(0,0,0,0.12); }
header h2 { font-size:20px; line-height:1; margin:0; font-weight:700; letter-spacing:0.2px; }

/* Main */
main { margin-top:14px; display:grid; grid-template-columns: 1fr 360px; gap:18px; align-items:start; }

/* Left column (chat + search) */
.left-col {}

/* Search box */
.search-box { display:grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap:10px; margin-bottom:12px; }
.search-box input { padding:10px 12px; border-radius:8px; border:1px solid #d7e9df; background:white; }

/* Chat box: nhỏ gọn, chuyên nghiệp */
.chat-box { background:white; border-radius:10px; padding:12px; height:360px; max-height:60vh; overflow-y:auto; border:1px solid #d6e6dd; box-shadow: 0 4px 16px rgba(11,122,59,0.04); font-size:14px; line-height:1.5; }
.msg-user { text-align:right; color:#073b21; margin:10px 0; }
.msg-bot { text-align:left; color:#0d0d0d; margin:10px 0; }
.msg-bot img { max-width:220px; border-radius:8px; display:block; margin-top:8px; }

/* Right column (controls + suggestions) */
.right-col { background:white; padding:12px; border-radius:10px; border:1px solid #d6e6dd; min-height:120px; }
.input-area { display:flex; gap:10px; margin-top:12px; }
.input-area input { flex:1; padding:10px 12px; border-radius:8px; border:1px solid #d7e9df; }
button { padding:10px 12px; border:none; cursor:pointer; border-radius:8px; background:#0b7a3b; color:white; font-weight:600; }
button.secondary { background:#6c6c6c; }

/* Suggestions */
#suggested { margin-top:10px; display:flex; gap:8px; flex-wrap:wrap; }
.suggestion-btn { background:#f0fff4; color:#0b7a3b; padding:8px 10px; border-radius:8px; border:1px solid #d7efe0; cursor:pointer; font-size:13px; }

/* Footer */
footer { margin-top:18px; padding:10px 12px; background:transparent; font-size:13px; text-align:center; color:#555; }

/* Modal history */
.modal {
    display:none;
    position: fixed;
    z-index: 1000;
    left:0; top:0; width:100%; height:100%;
    overflow:auto; background-color: rgba(0,0,0,0.4);
}
.modal-content {
    background-color: #ffffff;
    margin: 48px auto;
    padding: 18px;
    border:1px solid #ddd;
    width: 90%;
    max-width:800px;
    max-height:80vh;
    overflow-y:auto;
    border-radius:10px;
}
.close-modal { color: #888; float:right; font-size:22px; font-weight:bold; cursor:pointer; }

/* Responsive */
@media (max-width: 900px) {
    main { grid-template-columns: 1fr; }
    .right-col { order: 2; }
}
</style>
</head>

<body>
<div class="container">
<header>
    <img src="/static/Logo_Marie_Curie.png" alt="Logo">
    <h2>Vietnam Travel AI</h2>
</header>

<main>
    <div class="left-col">
        <h3 style="margin:10px 0 6px 0;">Google Travel-style Search</h3>
        <div class="search-box" style="margin-bottom:12px;">
            <input id="city" placeholder="Thành phố (Hà Nội, Đà Nẵng, Đà Lạt, Phú Quốc…)">
            <input id="budget" placeholder="Ngân sách (VD: 20 triệu, 10 triệu...)">
            <input id="season" placeholder="Mùa (hè, đông…)">
            <button onclick="travelSearch()">Tìm</button>
        </div>

        <h3 style="margin:10px 0 6px 0;">Chat tư vấn du lịch</h3>
        <div id="chat" class="chat-box"></div>

        <div id="suggested" style="margin-top:10px;"></div>
    </div>

    <div class="right-col">
        <div style="font-weight:700; margin-bottom:8px;">Tương tác nhanh</div>
        <div class="input-area">
            <input id="msg" placeholder="Hỏi lịch trình, chi phí, mùa đẹp nhất...">
            <button onclick="sendMsg()">Gửi</button>
        </div>

        <div style="margin-top:12px; display:flex; gap:8px; flex-wrap:wrap;">
            <button class="secondary" onclick="clearChat()">Xóa</button>
            <button class="secondary" onclick="showHistory()">Lịch sử chat</button>
            <button class="secondary" onclick="exportPDF()">Xuất PDF</button>
        </div>

        <div style="margin-top:12px; color:#666; font-size:13px;">
            Hotline: <strong>__HOTLINE__</strong><br>
            © 2025 – <strong>__BUILDER__</strong>
        </div>
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
    Giao diện đã được tinh gọn: chat-box nhỏ gọn, logo gọn để chữ trong logo nhìn rõ.
</footer>
</div>

<script src="/static/chat.js"></script>
</body>
</html>
"""
    html = html.replace("__BUILDER__", BUILDER_NAME)
    html = html.replace("__HOTLINE__", HOTLINE)
    return Response(html, mimetype="text/html")


# ========= CHAT API =========
@app.route("/chat", methods=["POST"])
def chat_api():
    data = request.json or {}
    # client trước đây dùng key "message" -> giữ nguyên để tương thích
    msg = data.get("message", "") or data.get("msg", "")
    msg = msg.strip() if isinstance(msg, str) else ""

    if not msg:
        return jsonify({"reply": "Vui lòng nhập nội dung."})

    prompt = (
        "Bạn là chuyên gia du lịch Việt Nam và thế giới. Trả lời text rõ ràng:\n"
        "- Phần 1: Thời gian\n"
        "- Phần 2: Lịch trình theo ngày\n"
        "- Phần 3: Chi phí\n"
        "- Phần 4: Hình ảnh & Video\n"
        "Không dùng HTML. Ví dụ:\n"
        "Ngày 1: ...\n"
        "- Hình ảnh minh họa: Đà Lạt Hồ Xuân Hương\n"
        "- Video tham khảo: Đà Lạt"
    )

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": msg}
        ],
        "temperature": 0.6
    }

    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=60
        )
        resp_json = r.json()
        # an toàn: kiểm tra cấu trúc
        ai_text = ""
        try:
            ai_text = resp_json["choices"][0]["message"]["content"]
        except Exception:
            ai_text = resp_json.get("error", {}).get("message", "Không nhận được phản hồi từ AI.")

        # --- Extract keywords for images/videos ---
        image_queries = []
        video_queries = []
        for line in ai_text.splitlines():
            if line.strip().startswith("- Hình ảnh minh họa:"):
                q = line.replace("- Hình ảnh minh họa:", "").strip()
                if q:
                    image_queries.append(q)
            if line.strip().startswith("- Video tham khảo:"):
                q = line.replace("- Video tham khảo:", "").strip()
                if q:
                    video_queries.append(q)

        # --- Search real images & videos via SerpAPI ---
        images = []
        for q in image_queries:
            images.extend(google_image_search(q, num=2))

        videos = []
        for q in video_queries:
            videos.extend(youtube_search(q, num=2))

        # thêm suggestions cơ bản (frontend có thể hiển thị)
        suggestions = [
            "Chi phí dự kiến?",
            "Lịch trình 3 ngày tối ưu?",
            "Thời tiết tháng này thế nào?"
        ]

        return jsonify({"reply": ai_text, "images": images, "videos": videos, "suggested": suggestions})

    except Exception as e:
        print("CHAT ERROR:", e)
        return jsonify({"reply": "Hệ thống đang bận, thử lại sau.", "images": [], "videos": [], "suggested": []})


# ========= EXPORT PDF =========
@app.route("/export-pdf", methods=["POST"])
def export_pdf():
    data = request.json or {}
    history = data.get("history", [])

    if not history:
        return jsonify({"error": "No content to export."}), 400

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Lịch Trình Du Lịch", ln=True, align="C")
    pdf.ln(6)
    pdf.set_font("Arial", "", 12)

    # history expected: list of dicts with keys user/reply or msg/reply
    for item in reversed(history):
        user_text = item.get("user") or item.get("msg") or ""
        bot_text = item.get("bot") or item.get("reply") or ""
        if user_text:
            pdf.set_text_color(2, 119, 189)
            pdf.multi_cell(0, 7, "Q: " + user_text)
        if bot_text:
            pdf.set_text_color(0, 0, 0)
            # ensure long lines wrap
            pdf.multi_cell(0, 7, "A: " + bot_text)
        pdf.ln(3)

    # output as bytes and return
    pdf_bytes = pdf.output(dest="S").encode("latin1")
    buf = io.BytesIO(pdf_bytes)
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", download_name="Lich_trinh_du_lich.pdf", as_attachment=True)


# ========= RUN =========
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
