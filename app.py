from flask import Flask, request, jsonify, Response
import os
import requests
import random

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
body {{
    margin:0; font-family: Arial, sans-serif; background:#eef1f4;
}}
header {{
    background:#0b7a3b; color:white; padding:15px 20px; display:flex;
    align-items:center; gap:15px;
}}
header img {{
    max-height:80px; width:auto; border-radius:8px;
}}
main {{
    max-width:900px; margin:auto; padding:20px;
}}

.search-box input {{
    padding:12px; border:2px solid #d0d4d8; border-radius:6px;
}}
.search-box button {{
    border-radius:6px;
}}

.chat-box {{
    background:white; border-radius:10px;
    padding:15px; height:380px; max-height:60vh;
    overflow-y:auto;
    border:2px solid #d6dce1;
    box-shadow:0 2px 6px rgba(0,0,0,0.05);
}}
.chat-box::-webkit-scrollbar {{
    width:8px;
}}
.chat-box::-webkit-scrollbar-thumb {{
    background:#ccc; border-radius:4px;
}}

.user {{
    text-align:right; background:#e6f5ec; display:inline-block;
    padding:8px 12px; border-radius:8px; margin:8px 0;
    color:#0b6533; max-width:75%;
}}
.bot {{
    text-align:left; background:#f7f7f7; display:inline-block;
    padding:8px 12px; border-radius:8px; margin:8px 0;
    color:#333; max-width:75%;
}}
.typing {{
    font-style:italic; color:#999;
}}

#suggestions {{
    margin-top:15px;
}}
.suggestion-btn {{
    background:#fff; border:1px solid #0b7a3b; color:#0b7a3b;
    padding:6px 10px; border-radius:6px; cursor:pointer;
    margin:4px; display:inline-block; font-size:13px;
}}
.suggestion-btn:hover {{
    background:#0b7a3b; color:white;
}}

.history-box {{
    background:white; border-radius:10px;
    border:2px solid #d6dce1;
    padding:10px; max-height:200px; overflow-y:auto;
    margin-bottom:15px;
}}
.history-item {{
    padding:6px; margin:4px 0; border-bottom:1px solid #eee;
    cursor:pointer; font-size:14px;
}}
.history-item:hover {{
    background:#f1f1f1;
}}

.input-area input {{
    border:2px solid #ccc; border-radius:8px;
}}
</style>
</head>

<body>

<header>
    <img src="/static/Logo_Marie_Curie.png">
    <h2>Vietnam Travel AI</h2>
</header>

<main>

<h3>Lịch sử trò chuyện</h3>
<div id="history" class="history-box"></div>

<h3>Tìm kiếm kiểu Google Travel</h3>
<div class="search-box" style="display:flex; gap:10px; flex-wrap:wrap;">
    <input id="city" placeholder="Thành phố (Đà Lạt, Phú Quốc…)">
    <input id="budget" placeholder="Ngân sách (VD: 10 triệu)">
    <input id="season" placeholder="Mùa (hè, đông…)">
    <button onclick="travelSearch()">Tìm kiếm</button>
</div>

<h3>Chat tư vấn du lịch</h3>
<div id="chat" class="chat-box"></div>

<div id="suggestions"></div>

<div class="input-area" style="display:flex; gap:10px; margin-top:12px;">
    <input id="msg" placeholder="Hỏi lịch trình, chi phí, mùa đẹp nhất...">
    <button onclick="sendMsg()">Gửi</button>
    <button onclick="clearChat()">Xóa</button>
</div>

</main>

<footer style="text-align:center; padding:20px; margin-top:40px; background:#eee;">
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
        return jsonify({"reply":"Vui lòng nhập nội dung."})

    # AI PROMPT
    prompt = (
        "Bạn là chuyên gia du lịch Việt Nam và thế giới. Trả lời văn bản rõ ràng:\n"
        "- Có mục: Thời gian, Lịch trình, Chi phí, Hình ảnh & Video\n"
        "- Mỗi ngày dùng bullet points\n"
        "- Không HTML, không iframe, không tự tạo link\n"
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

        # Extract keywords
        image_queries = []
        video_queries = []
        for line in ai_text.splitlines():
            if line.strip().startswith("- Hình ảnh minh họa:"):
                q = line.replace("- Hình ảnh minh họa:", "").strip()
                if q: image_queries.append(q)
            if line.strip().startswith("- Video tham khảo:"):
                q = line.replace("- Video tham khảo:", "").strip()
                if q: video_queries.append(q)

        images = []
        for q in image_queries:
            imgs = google_image_search(q, 1)
            images.extend(imgs)

        videos = []
        for q in video_queries:
            vids = youtube_search(q, 1)
            videos.extend(vids)

        # Gợi ý câu hỏi tiếp theo
        suggestions_list = [
            "Chi phí tổng cho chuyến đi này là bao nhiêu?",
            "Có nên đi vào mùa này không?",
            "Các món ăn nổi tiếng ở đó?",
            "Gợi ý khách sạn phù hợp ngân sách?",
            "Nếu đi thêm 1 ngày nữa thì lịch trình sao?",
        ]
        random.shuffle(suggestions_list)
        suggestions = suggestions_list[:3]

        return jsonify({
            "reply": ai_text,
            "images": images,
            "videos": videos,
            "suggestions": suggestions
        })

    except Exception as e:
        print(e)
        return jsonify({"reply":"Hệ thống đang bận, thử lại sau.", "images":[], "videos":[]})

# ========= RUN =========
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
