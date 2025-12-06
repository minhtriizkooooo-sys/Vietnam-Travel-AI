import os
import time
import requests
from flask import Flask, request, jsonify, render_template_string
import openai

# ==========================
# Config & Environment
# ==========================
app = Flask(__name__)

# Environment variables (set trên Render)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

# Contact / branding (chỉnh theo ý bạn)
HOTLINE = os.getenv("HOTLINE", "0909 123 456")
ZALO_URL = os.getenv("ZALO_URL", "https://zalo.me/0909123456")
BUILDER = os.getenv("BUILDER_NAME", "Tên đơn vị / Cá nhân")

# Initialize OpenAI
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
    OPENAI_OK = True
else:
    OPENAI_OK = False

# ==========================
# Production Prompt (Commercial)
# ==========================
SYSTEM_PROMPT = """
Bạn là tư vấn viên du lịch cao cấp tại Việt Nam.
Yêu cầu khi trả lời:
- Chỉ tư vấn về du lịch trong lãnh thổ Việt Nam.
- Giọng văn: chuyên nghiệp, thân thiện, dễ hiểu, hướng tới chuyển đổi (booking).
- Không tiết lộ mình là AI.
- Luôn cung cấp: (1) Tổng quan điểm đến, (2) Thời điểm tốt nhất, (3) Gợi ý lịch trình ngắn (2-4 bước), (4) Giá tham khảo nếu có, (5) Mẹo & cảnh báo (những gì nên biết).
- Kết thúc bằng một lời kêu gọi hành động nhẹ nhàng: mời liên hệ hotline/Zalo để được tư vấn đặt tour.
"""

# ==========================
# In-memory lead tracking (lightweight)
# ==========================
LEADS = []         # list of dict: {q, filters, ip, ts}
RATE_LIMITS = {}   # ip -> list[timestamps]

# ==========================
# Utilities
# ==========================
def rate_limit_ok(ip, max_calls=6, per_seconds=10):
    """Simple per-IP rate limiting."""
    now = time.time()
    calls = RATE_LIMITS.get(ip, [])
    calls = [t for t in calls if now - t < per_seconds]
    calls.append(now)
    RATE_LIMITS[ip] = calls
    return len(calls) <= max_calls

def safe_serp_images(query, num=4):
    """Fetch images from SerpAPI (images). Returns list of image urls."""
    if not SERPAPI_API_KEY:
        return []
    try:
        r = requests.get(
            "https://serpapi.com/search.json",
            params={"q": query, "tbm": "isch", "num": num, "api_key": SERPAPI_API_KEY},
            timeout=8
        )
        data = r.json()
        imgs = []
        for it in data.get("images_results", [])[:num]:
            # some results contain 'original' or 'thumbnail'
            url = it.get("original") or it.get("thumbnail") or it.get("source")
            if url:
                imgs.append(url)
        return imgs
    except Exception:
        return []

def youtube_embed_search(query):
    """Return a YouTube embed URL that searches for the query (works as fallback)."""
    # Use search listType - YouTube will show a playlist-like search result
    safe_q = requests.utils.requote_uri(query)
    return f"https://www.youtube.com/embed?listType=search&list={safe_q}"

def call_openai_chat(user_question, filters):
    """Call OpenAI Chat API (ChatCompletion). Returns text answer."""
    if not OPENAI_OK:
        return ("AI chưa được cấu hình. Vui lòng cài đặt OPENAI_API_KEY trên môi trường.", False)

    # Build contextual prompt
    filter_text = ""
    if filters:
        parts = []
        for k in ("city", "type", "budget", "duration"):
            v = filters.get(k)
            if v:
                parts.append(f"- {k}: {v}")
        if parts:
            filter_text = "Thông tin bổ trợ:\n" + "\n".join(parts) + "\n\n"

    user_prompt = f"""
{filter_text}
Khách hỏi: {user_question}

Yêu cầu định dạng trả lời:
1) Tổng quan ngắn (2-3 câu)
2) Thời điểm tốt nhất
3) Gợi ý lịch trình ngắn (3-4 bước)
4) Giá tham khảo (nếu có) / Lưu ý
5) Mẹo & CTA liên hệ (hotline/zalo)
"""

    try:
        # Use ChatCompletion (compatible with most OpenAI python SDKs)
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=700,
            temperature=0.6
        )
        text = resp.choices[0].message.content.strip()
        return (text, True)
    except Exception as e:
        # Return error message but keep server stable
        return (f"Lỗi khi gọi OpenAI: {e}", False)

# ==========================
# Inline UI (home) - header with /static/Logo.png and footer with builder & copyright
# ==========================
@app.route("/")
def home():
    # Inline HTML with Bootstrap, referencing /static/Logo.png
    return render_template_string(f"""
<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Vietnam Travel AI – Smart Tourism</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {{ background:#f4f6f8; }}
    header {{ background:#0f5132; color:#fff; padding:12px 18px; }}
    header .brand {{ display:flex; align-items:center; gap:12px; justify-content:center; }}
    header img.logo {{ height:52px; border-radius:8px; }}
    .chat {{ height:420px; overflow:auto; background:#fff; padding:12px; border-radius:10px; box-shadow:0 2px 6px rgba(0,0,0,0.06); }}
    .bot {{ background:#e9f7ef; padding:10px; border-radius:10px; margin-bottom:8px; }}
    .user {{ background:#d1ecf1; padding:10px; border-radius:10px; margin-bottom:8px; text-align:right; }}
    .cta {{ background:#198754; color:#fff; padding:8px 10px; border-radius:8px; display:inline-block; margin-top:8px; }}
    footer {{ background:#0f5132; color:#fff; padding:12px; text-align:center; margin-top:18px; }}
    img.resp {{ width:100%; max-height:320px; object-fit:cover; border-radius:8px; margin-top:8px; }}
    iframe.resp {{ width:100%; height:260px; border-radius:8px; margin-top:8px; border:none; }}
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <img src="/static/Logo.png" alt="Logo" class="logo">
      <div>
        <h4 class="mb-0">Vietnam Travel AI</h4>
        <small>Smart Tourism Assistant – Tư vấn & Đặt tour</small>
      </div>
    </div>
  </header>

  <main class="container my-3">
    <div class="row">
      <div class="col-lg-8 offset-lg-2">
        <div class="chat mb-3" id="chat"></div>

        <div class="mb-2">
          <input id="q" class="form-control" placeholder="Bạn muốn đi đâu? (ví dụ: 'Đà Nẵng 3 ngày cho gia đình')">
        </div>

        <div class="row g-2 mb-2">
          <div class="col"><input id="city" class="form-control" placeholder="Địa điểm (tùy chọn)"></div>
          <div class="col"><input id="type" class="form-control" placeholder="Loại hình (tùy chọn)"></div>
          <div class="col"><input id="budget" class="form-control" placeholder="Ngân sách (tùy chọn)"></div>
          <div class="col"><input id="duration" class="form-control" placeholder="Thời gian (tùy chọn)"></div>
        </div>

        <div class="d-grid gap-2">
          <button class="btn btn-success" id="sendBtn">Tư vấn & Tạo lead</button>
        </div>
      </div>
    </div>
  </main>

  <footer>
    <div>Website được xây dựng & phát triển bởi <strong>{BUILDER}</strong></div>
    <div>© {time.strftime("%Y")} Vietnam Travel AI. All rights reserved. Hotline: <strong>{HOTLINE}</strong></div>
    <div style="margin-top:6px"><a href="{ZALO_URL}" style="color:#fff;text-decoration:underline">Liên hệ Zalo</a></div>
  </footer>

<script>
const chat = document.getElementById("chat");
const sendBtn = document.getElementById("sendBtn");
const qInput = document.getElementById("q");
const city = document.getElementById("city");
const type = document.getElementById("type");
const budget = document.getElementById("budget");
const duration = document.getElementById("duration");

function appendUser(text){ chat.innerHTML += `<div class="user">${text}</div>`; chat.scrollTop = chat.scrollHeight; }
function appendBot(html){ chat.innerHTML += `<div class="bot">${html}</div>`; chat.scrollTop = chat.scrollHeight; }

sendBtn.onclick = async function(){
  const q = qInput.value.trim();
  if(!q) return;
  appendUser(q);
  qInput.value = "";
  sendBtn.disabled = true;
  appendBot("Đang suy nghĩ...");

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({
        question: q,
        filters: {
          city: city.value,
          type: type.value,
          budget: budget.value,
          duration: duration.value
        }
      })
    });
    const data = await res.json();
    // Remove last "Đang suy nghĩ..." bot (the last element)
    const bots = Array.from(document.querySelectorAll(".bot"));
    if(bots.length) bots[bots.length-1].remove();

    // Render answer (may contain newlines -> convert to <br>)
    let answer_html = (data.answer || "Không có phản hồi").replace(/\\n/g, "<br>");
    // Add CTA block (hotline/zalo)
    answer_html += `<div class="cta">📞 {HOTLINE} | 💬 <a href="{ZALO_URL}" style="color:#fff;text-decoration:underline">Zalo</a></div>`;

    appendBot(answer_html);

    // Images
    (data.images || []).forEach(src => {
      appendBot(`<img class="resp" src="${src}" alt="img">`);
    });

    // Video
    if(data.video){
      appendBot(`<iframe class="resp" src="${data.video}" allowfullscreen></iframe>`);
    }

  } catch (err) {
    // Replace last bot message and show error
    const bots = Array.from(document.querySelectorAll(".bot"));
    if(bots.length) bots[bots.length-1].remove();
    appendBot("Lỗi kết nối hoặc lỗi server. Vui lòng thử lại sau.");
  } finally {
    sendBtn.disabled = false;
  }
};
</script>
</body>
</html>
""")

# ==========================
# API: Chat endpoint
# - rate limit
# - store lead in-memory
# - return answer, images, video
# ==========================
@app.route("/api/chat", methods=["POST"])
def api_chat():
    ip = request.remote_addr or "unknown"
    if not rate_limit_ok(ip):
        return jsonify({"answer": "Bạn gửi quá nhanh. Vui lòng đợi vài giây trước khi gửi tiếp."})

    data = request.get_json() or {}
    question = data.get("question", "").strip()
    filters = data.get("filters", {})

    if not question:
        return jsonify({"answer": "Vui lòng nhập câu hỏi hoặc yêu cầu du lịch."})

    # Record as a lead (in-memory). In production, you can forward to DB / GoogleSheet / webhook
    LEADS.append({
        "question": question,
        "filters": filters,
        "ip": ip,
        "ts": time.time()
    })

    # Call OpenAI
    answer_text, ok = call_openai_chat(question, filters)
    # If AI failed, provide fallback friendly message
    if not ok:
        answer_text = ("Xin lỗi, hiện hệ thống tư vấn bằng AI đang tạm thời gặp sự cố. "
                       "Bạn vẫn có thể liên hệ hotline để được tư vấn: " + HOTLINE)

    # Get images & video suggestions
    image_query = " ".join([filters.get("city",""), filters.get("type",""), "du lịch"]).strip() or question
    images = safe_serp_images(image_query, num=3)
    video = youtube_embed_search(image_query or question)

    # Replace newlines with <br> on server-side for convenience
    answer_text = answer_text.replace("\n\n", "\n").replace("\n", "<br>")

    return jsonify({
        "answer": answer_text,
        "images": images,
        "video": video
    })

# ==========================
# Admin debug endpoints (optional)
# - Note: leave available for now; you can remove or protect later
# ==========================
@app.route("/_internal/leads")
def internal_leads():
    """Return in-memory leads (JSON) — for admin/debug only."""
    # WARNING: This endpoint is unauthenticated. In production protect it.
    return jsonify({"count": len(LEADS), "leads": LEADS})

@app.route("/_internal/health")
def internal_health():
    return jsonify({
        "status": "ok",
        "openai_configured": OPENAI_OK,
        "serpapi_configured": bool(SERPAPI_API_KEY)
    })

# ==========================
# Run (for local dev; Render will use gunicorn start command)
# ==========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
