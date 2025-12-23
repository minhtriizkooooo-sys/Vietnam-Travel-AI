import os
import io
import uuid
import sqlite3
import requests
from datetime import datetime
from flask import (
    Flask, request, jsonify, render_template,
    make_response, send_file
)
from flask_cors import CORS

# PDF (Unicode)
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ---------------- CONFIG ----------------
app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
DB_PATH = os.getenv("SQLITE_PATH", "chat_history.db")

HOTLINE = os.getenv("HOTLINE", "+84-908-08-3566")
BUILDER_NAME = os.getenv("BUILDER_NAME", "Vietnam Travel AI – Lại Nguyễn Minh Trí")

# ---------------- DB ----------------
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    cur = db.cursor()

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
            role TEXT,
            content TEXT,
            created_at TEXT
        )
    """)

    # ===== ADD: lưu suggested questions =====
    cur.execute("""
        CREATE TABLE IF NOT EXISTS suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            question TEXT,
            created_at TEXT
        )
    """)

    db.commit()
    db.close()

init_db()

# ---------------- SESSION ----------------
def ensure_session():
    sid = request.cookies.get("session_id")
    if not sid:
        sid = str(uuid.uuid4())
        db = get_db()
        db.execute(
            "INSERT OR IGNORE INTO sessions VALUES (?,?)",
            (sid, datetime.utcnow().isoformat())
        )
        db.commit()
        db.close()
    return sid

def save_message(sid, role, content):
    db = get_db()
    db.execute(
        "INSERT INTO messages (session_id, role, content, created_at) VALUES (?,?,?,?)",
        (sid, role, content, datetime.utcnow().isoformat())
    )
    db.commit()
    db.close()

def fetch_history(sid):
    db = get_db()
    rows = db.execute(
        "SELECT role, content, created_at FROM messages WHERE session_id=? ORDER BY id",
        (sid,)
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]

def save_suggestions(sid, questions):
    db = get_db()
    for q in questions:
        db.execute(
            "INSERT INTO suggestions (session_id, question, created_at) VALUES (?,?,?)",
            (sid, q, datetime.utcnow().isoformat())
        )
    db.commit()
    db.close()

def fetch_suggestions(sid):
    db = get_db()
    rows = db.execute(
        "SELECT question FROM suggestions WHERE session_id=?",
        (sid,)
    ).fetchall()
    db.close()
    return [r["question"] for r in rows]

# ---------------- OPENAI ----------------
SYSTEM_PROMPT = """
Bạn là chuyên gia du lịch Việt Nam.

QUY TẮC:
- Nếu người dùng KHÔNG nêu địa điểm → mặc định tư vấn TP. Hồ Chí Minh, Việt Nam
- Sau đó mới mở rộng sang khu vực khác nếu cần

FORMAT:
1) Thời gian lý tưởng
2) Lịch trình
3) Chi phí
4) Gợi ý hình ảnh & video (mô tả, không link)

Trả lời bằng tiếng Việt, không HTML.
"""

def call_openai(user_msg):
    if not OPENAI_API_KEY:
        return "OPENAI_API_KEY chưa cấu hình."

    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg}
            ],
            "temperature": 0.6,
            "max_tokens": 700
        },
        timeout=60
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

# ===== ADD: sinh câu hỏi gợi ý =====
def generate_suggestions(question, answer):
    prompt = f"""
Dựa trên câu hỏi và câu trả lời sau, hãy gợi ý 3 câu hỏi tiếp theo tự nhiên cho người dùng.
Chỉ liệt kê danh sách, không giải thích.

Câu hỏi: {question}
Trả lời: {answer}
"""
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "Bạn là trợ lý gợi ý câu hỏi."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,
            "max_tokens": 200
        },
        timeout=60
    )
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"]
    return [x.strip("- ").strip() for x in text.splitlines() if x.strip()]

# ---------------- SERPAPI ----------------
def search_images(query):
    if not SERPAPI_KEY:
        return []
    r = requests.get(
        "https://serpapi.com/search.json",
        params={
            "q": f"{query} Ho Chi Minh City",
            "tbm": "isch",
            "num": 4,
            "api_key": SERPAPI_KEY
        },
        timeout=10
    )
    imgs = []
    for i in r.json().get("images_results", []):
        imgs.append({
            "url": i.get("original"),
            "caption": i.get("title") or f"Hình ảnh {query} – TP.HCM"
        })
    return imgs

def search_youtube(query):
    if not SERPAPI_KEY:
        return []
    r = requests.get(
        "https://serpapi.com/search.json",
        params={
            "q": f"{query} site:youtube.com",
            "tbm": "vid",
            "num": 3,
            "api_key": SERPAPI_KEY
        },
        timeout=10
    )
    vids = []
    for v in r.json().get("video_results", []):
        link = v.get("link", "")
        if "youtube.com" in link or "youtu.be" in link:
            vids.append(link)
    return vids

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    sid = ensure_session()
    resp = make_response(render_template(
        "ui.html",
        HOTLINE=HOTLINE,
        BUILDER=BUILDER_NAME
    ))
    resp.set_cookie("session_id", sid, httponly=True, samesite="Lax")
    return resp

@app.route("/chat", methods=["POST"])
def chat():
    sid = ensure_session()
    msg = (request.json or {}).get("msg", "").strip()
    if not msg:
        return jsonify({"error": "empty"}), 400

    save_message(sid, "user", msg)

    try:
        reply = call_openai(msg)
    except Exception:
        reply = "Lỗi hệ thống. Vui lòng thử lại."

    save_message(sid, "bot", reply)

    # ===== ADD: suggested questions =====
    suggestions = generate_suggestions(msg, reply)
    save_suggestions(sid, suggestions)

    return jsonify({
        "reply": reply,
        "images": search_images(msg),
        "videos": search_youtube(msg),
        "suggestions": suggestions
    })

@app.route("/history")
def history():
    sid = request.cookies.get("session_id")
    return jsonify({"history": fetch_history(sid) if sid else []})

# ---------------- EXPORT PDF (IMPROVED) ----------------
@app.route("/export-pdf", methods=["POST"])
def export_pdf():
    sid = request.cookies.get("session_id")
    history = fetch_history(sid)
    suggestions = fetch_suggestions(sid)

    if not history:
        return jsonify({"error": "No data"}), 400

    buffer = io.BytesIO()

    font_path = os.path.join(app.static_folder, "DejaVuSans.ttf")
    pdfmetrics.registerFont(TTFont("DejaVu", font_path))

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("VN", fontName="DejaVu", fontSize=11, leading=14))
    styles.add(ParagraphStyle("SUG", fontName="DejaVu", fontSize=10, italic=True))

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    story = [
        Paragraph("<b>LỊCH SỬ HỘI THOẠI</b>", styles["VN"]),
        Spacer(1, 12)
    ]

    for h in history:
        bg = colors.lightblue if h["role"] == "user" else colors.whitesmoke
        label = "NGƯỜI DÙNG" if h["role"] == "user" else "TRỢ LÝ"

        table = Table(
            [[label, h["content"]]],
            colWidths=[3*cm, 12*cm]
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), bg),
            ("FONT", (0,0), (-1,-1), "DejaVu"),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("RIGHTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ]))

        story.append(table)
        story.append(Spacer(1, 8))

    if suggestions:
        story.append(Spacer(1, 12))
        story.append(Paragraph("<b>GỢI Ý CÂU HỎI TIẾP THEO</b>", styles["VN"]))
        for s in suggestions:
            story.append(Paragraph(f"- {s}", styles["SUG"]))

    doc.build(story)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="travel_history.pdf",
        mimetype="application/pdf"
    )

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
