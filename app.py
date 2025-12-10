import os
import io
import uuid
import sqlite3
import requests
from datetime import datetime
from flask import (
    Flask, request, jsonify, render_template, make_response, send_file
)
from fpdf import FPDF
from flask_cors import CORS

# -------- CONFIG --------
app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
DB_PATH = os.getenv("SQLITE_PATH", "chat_history.db")
SITE_URL = os.getenv("SITE_URL", "https://vietnam-travel-ai.onrender.com")
HOTLINE = os.getenv("HOTLINE", "+84-908-08-3566")
BUILDER_NAME = os.getenv("BUILDER_NAME", "Vietnam Travel AI - Lại Nguyễn Minh Trí")

# -------- DB HELPERS --------
def get_db_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        created_at TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        role TEXT,        -- 'user' or 'bot'
        content TEXT,
        created_at TEXT,
        FOREIGN KEY(session_id) REFERENCES sessions(id)
    )
    """)
    conn.commit()
    conn.close()

init_db()

# -------- UTIL --------
def ensure_session():
    # Get session_id from cookie, create if missing
    sid = request.cookies.get("session_id")
    if not sid:
        sid = str(uuid.uuid4())
        # insert session in DB
        conn = get_db_conn()
        conn.execute(
            "INSERT OR IGNORE INTO sessions (id, created_at) VALUES (?, ?)",
            (sid, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()
        # set cookie in response by caller
    else:
        # ensure session exists in DB
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO sessions (id, created_at) VALUES (?, ?)",
                    (sid, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
    return sid

def save_message(session_id, role, content):
    conn = get_db_conn()
    conn.execute(
        "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (session_id, role, content, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

def fetch_history(session_id, limit=None):
    conn = get_db_conn()
    cur = conn.cursor()
    q = "SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY id ASC"
    if limit:
        q += " LIMIT ?"
        cur.execute(q, (session_id, limit))
    else:
        cur.execute(q, (session_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# -------- EXTERNAL HELPERS --------
def call_openai_chat(system_prompt, user_content, temperature=0.6):
    if not OPENAI_API_KEY:
        return "OPENAI_API_KEY not configured."
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": temperature,
        "max_tokens": 700
    }
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    r = requests.post(url, json=payload, headers=headers, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]

def generate_suggestions_from_ai(context_text, n=3):
    system = "Bạn là trợ lý du lịch chuyên nghiệp. Dựa vào đoạn văn sau (là câu trả lời/đoạn chat cuối), hãy tạo ra {} câu hỏi gợi ý ngắn, phù hợp để người dùng hỏi tiếp (tiếng Việt). Trả về mỗi câu trên 1 dòng.".format(n)
    try:
        resp = call_openai_chat(system, context_text, temperature=0.9)
        # split by newlines and take top n
        lines = [l.strip() for l in resp.splitlines() if l.strip()]
        return lines[:n] if lines else []
    except Exception as e:
        print("Suggestion AI error:", e)
        return []

# -------- SERPAPI (optional) --------
def serpapi_image_search(query, num=3):
    if not SERPAPI_KEY:
        return []
    try:
        url = f"https://serpapi.com/search.json?q={query}&tbm=isch&num={num}&api_key={SERPAPI_KEY}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        results = r.json().get("images_results", [])
        return [item.get("original") for item in results if item.get("original")]
    except Exception as e:
        print("SerpAPI image error:", e)
        return []

def serpapi_video_search(query, num=2):
    if not SERPAPI_KEY:
        return []
    try:
        url = f"https://serpapi.com/search.json?q={query}&tbm=vid&num={num}&api_key={SERPAPI_KEY}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        results = r.json().get("video_results", [])
        return [item.get("link") for item in results if item.get("link")]
    except Exception as e:
        print("SerpAPI video error:", e)
        return []

# -------- ROUTES --------
@app.route("/", methods=["GET"])
def index():
    # ensure session and set cookie if new
    sid = request.cookies.get("session_id")
    if not sid:
        sid = ensure_session()
        resp = make_response(render_template("ui.html", HOTLINE=os.getenv("HOTLINE", "+84-908-08-3566"),
                                             BUILDER=os.getenv("BUILDER_NAME", "Vietnam Travel AI – Minh Trí")))
        resp.set_cookie("session_id", sid, httponly=True, samesite="Lax")
        return resp
    return render_template("ui.html", HOTLINE=os.getenv("HOTLINE", "+84-908-08-3566"),
                           BUILDER=os.getenv("BUILDER_NAME", "Vietnam Travel AI – Minh Trí"))

@app.route("/chat", methods=["POST"])
def chat():
    sid = ensure_session()
    # If cookie missing in request, will rely on ensure_session(), but client should keep cookie.
    data = request.json or {}
    msg = data.get("msg", "").strip()
    if not msg:
        return jsonify({"error": "empty message"}), 400

    # Save user message
    save_message(sid, "user", msg)

    # Build system prompt for travel expert (you can customize)
    system_prompt = (
        "Bạn là chuyên gia du lịch Việt Nam và thế giới. Trả lời với format:\n"
        "1) Thời gian\n"
        "2) Lịch trình\n"
        "3) Chi phí\n"
        "4) Hình ảnh minh họa và video\n        "
        "Trả bằng tiếng Việt. Không dùng HTML."
    )
    try:
        # Call OpenAI for the main reply
        bot_reply = call_openai_chat(system_prompt, msg, temperature=0.6)
    except Exception as e:
        print("OpenAI main chat error:", e)
        bot_reply = "Lỗi khi gọi OpenAI. Vui lòng thử lại sau."

    # Save bot reply to DB
    save_message(sid, "bot", bot_reply)

    # Try extract image/video queries from bot_reply (flexible)
    image_queries = []
    video_queries = []
    for line in bot_reply.splitlines():
        low = line.lower()
        if "hình ảnh" in low or "ảnh" in low:
            # take text after ':' if exists
            if ":" in line:
                q = line.split(":", 1)[1].strip()
            else:
                q = line.strip()
            if q:
                image_queries.append(q)
        if "video" in low:
            if ":" in line:
                q = line.split(":", 1)[1].strip()
            else:
                q = line.strip()
            if q:
                video_queries.append(q)

    images = []
    videos = []
    for q in image_queries:
        images.extend(serpapi_image_search(q, 3))
    for q in video_queries:
        videos.extend(serpapi_video_search(q, 2))

    # If no image suggestions, try fallback based on msg
    if not images:
        images = serpapi_image_search(msg.split(",")[0], 3)

    # Generate AI-based dynamic suggestions (based on bot_reply and recent context)
    # We'll use last bot reply as context for suggestions
    suggestions = generate_suggestions_from_ai(bot_reply, n=4)

    return jsonify({
        "reply": bot_reply,
        "images": images,
        "videos": videos,
        "suggested": suggestions
    })


@app.route("/history", methods=["GET"])
def history():
    sid = request.cookies.get("session_id")
    if not sid:
        return jsonify({"history": []})
    rows = fetch_history(sid)
    return jsonify({"history": rows})


@app.route("/export-pdf", methods=["POST"])
def export_pdf():
    sid = request.cookies.get("session_id")
    if not sid:
        return jsonify({"error": "No session"}), 400
    history = fetch_history(sid)
    if not history:
        return jsonify({"error": "No history"}), 400

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Lịch sử chat - Vietnam Travel AI", ln=True, align="C")
    pdf.ln(6)
    pdf.set_font("Arial", "", 12)

    for item in history:
        role = item.get("role", "")
        content = item.get("content", "")
        created = item.get("created_at", "")
        header = f"[{role.upper()} - {created}]"
        pdf.set_text_color(0, 70, 140)
        pdf.multi_cell(0, 7, header)
        pdf.set_text_color(0, 0, 0)
        # Ensure long lines wrap
        pdf.multi_cell(0, 7, content)
        pdf.ln(3)

    pdf_bytes = pdf.output(dest="S").encode("latin1")
    buf = io.BytesIO(pdf_bytes)
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", download_name="history.pdf", as_attachment=True)


@app.route("/clear-history", methods=["POST"])
def clear_history():
    sid = request.cookies.get("session_id")
    if not sid:
        return jsonify({"ok": True})
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM messages WHERE session_id = ?", (sid,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# -------- RUN --------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
