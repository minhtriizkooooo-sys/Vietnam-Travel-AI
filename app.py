# app.py
from flask import Flask, request, jsonify, Response, redirect
import os
import time
import requests
import html as html_lib
from functools import wraps
import xml.etree.ElementTree as ET

app = Flask(__name__)

# =========================
# CONFIG FROM ENV
# =========================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")          # Zapier / Make webhook
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY", "")# optional
AIRTABLE_BASE = os.getenv("AIRTABLE_BASE", "")
AIRTABLE_TABLE = os.getenv("AIRTABLE_TABLE", "")
GOOGLE_FORM_URL = os.getenv("GOOGLE_FORM_URL", "")  # optional: Google Form POST action URL
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "changeme") # set to secure token in production
HOTLINE = os.getenv("HOTLINE", "+84-908-08-3566")
BUILDER_NAME = os.getenv("BUILDER_NAME", "Vietnam Travel AI - Lại Nguyễn Minh Trí")
SITE_URL = os.getenv("SITE_URL", "https://vietnam-travel-ai.onrender.com")
DEFAULT_IMAGE = os.getenv("DEFAULT_IMAGE", "https://source.unsplash.com/1200x630/?vietnam,travel")

# In-memory storage (lightweight). Replace with DB in production.
LEADS = []
SEARCH_LOG = []  # store search queries for sitemap / rss

# =========================
# HELPERS
# =========================
def escape(s): return html_lib.escape(s or "")

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Check X-ADMIN-TOKEN header or ?admin_token=...
        token = request.headers.get("X-ADMIN-TOKEN") or request.args.get("admin_token")
        if not token or token != ADMIN_TOKEN:
            return jsonify({"error": "Unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper

def send_webhook(lead):
    if not WEBHOOK_URL: return False
    try:
        requests.post(WEBHOOK_URL, json=lead, timeout=6)
        return True
    except Exception:
        return False

def send_airtable(lead):
    if not (AIRTABLE_API_KEY and AIRTABLE_BASE and AIRTABLE_TABLE): return False
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE}/{AIRTABLE_TABLE}"
    headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}", "Content-Type": "application/json"}
    data = {"fields": lead}
    try:
        requests.post(url, json=data, headers=headers, timeout=6)
        return True
    except Exception:
        return False

def send_google_form(lead):
    if not GOOGLE_FORM_URL: return False
    try:
        # NOTE: GOOGLE_FORM_URL should be the form's action endpoint.
        # lead keys must match the input 'entry.xxxxxx' names of the form configured by user.
        requests.post(GOOGLE_FORM_URL, data=lead, timeout=6)
        return True
    except Exception:
        return False

# =========================
# OpenAI helpers (sync and streaming)
# =========================
def call_openai_chat(prompt, system=None, timeout=50):
    if not OPENAI_API_KEY:
        raise RuntimeError("Missing OPENAI_API_KEY")
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": ( [{"role":"system","content":system}] if system else [] ) + [{"role":"user","content":prompt}],
        "temperature": 0.45,
        "max_tokens": 700
    }
    r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def stream_openai_chat(prompt, system=None):
    """
    Stream OpenAI response using requests with stream=True.
    Yields SSE-compatible 'data: ...\\n\\n' chunks for EventSource client.
    """
    if not OPENAI_API_KEY:
        yield "data: ERROR: Missing OPENAI_API_KEY\n\n"
        return

    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": ( [{"role":"system","content":system}] if system else [] ) + [{"role":"user","content":prompt}],
        "temperature": 0.45,
        "max_tokens": 700,
        "stream": True
    }
    try:
        with requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=60, stream=True) as r:
            r.raise_for_status()
            # Iterate over lines and forward them. OpenAI stream sends lines beginning with "data: " and "data: [DONE]"
            for line in r.iter_lines(decode_unicode=True):
                if line:
                    # forward raw line to client as SSE
                    # ensure proper SSE framing
                    yield f"data: {line}\n\n"
            # stream end
            yield "data: [DONE]\n\n"
    except Exception as e:
        yield f"data: ERROR: {escape(str(e))}\n\n"

# =========================
# SEO helpers
# =========================
def render_meta(title, desc, image=DEFAULT_IMAGE, url=SITE_URL):
    return f"""
    <title>{escape(title)}</title>
    <meta name="description" content="{escape(desc)}">
    <link rel="canonical" href="{escape(url)}">
    <meta property="og:title" content="{escape(title)}" />
    <meta property="og:description" content="{escape(desc)}" />
    <meta property="og:image" content="{escape(image)}" />
    <meta property="og:url" content="{escape(url)}" />
    <meta name="twitter:card" content="summary_large_image" />
    """

def json_ld(site_name, description, url, image):
    import json
    ld = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": site_name,
        "url": url,
        "description": description,
        "publisher": {"@type":"Organization","name":site_name,"logo":{"@type":"ImageObject","url":image}}
    }
    return f'<script type="application/ld+json">{json.dumps(ld)}</script>'

# =========================
# LANDING / CHAT UI (main)
# =========================
@app.route("/", methods=["GET"])
def home():
    title = "Vietnam Travel AI — Tư vấn & Đặt tour"
    desc = "Vietnam Travel AI - trợ lý du lịch chuyên nghiệp. Tìm tour, xây lịch trình, ước tính chi phí, ảnh & video minh họa."
    meta = render_meta(title, desc)
    ld = json_ld("Vietnam Travel AI", desc, SITE_URL, DEFAULT_IMAGE)

    html = f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
{meta}
{ld}
<style>
body{{margin:0;font-family:Inter,Arial,Helvetica,sans-serif;background:#f7f9f8;color:#222}}
.header{{background:#0b7a3b;color:#fff;padding:18px 20px;display:flex;align-items:center;gap:16px}}
.header img{{height:56px;border-radius:8px}}
.container{{max-width:1100px;margin:20px auto;padding:0 16px}}
.card{{background:#fff;border-radius:10px;padding:14px;border:1px solid #e6eee6}}
.chat-box{{height:420px;overflow:auto;border-radius:8px;padding:12px;background:#fff;border:1px solid #e9f8ee}}
.user{{text-align:right;color:#0b7a3b;margin:8px 0;font-weight:600}}
.bot{{text-align:left;color:#333;margin:8px 0}}
.loading{{font-style:italic;color:#999}}
.controls{{display:flex;gap:8px;margin-top:10px}}
.controls input,.controls select{{flex:1;padding:10px;border-radius:8px;border:1px solid #ddd}}
.btn{{background:#0b7a3b;color:#fff;padding:10px 14px;border-radius:8px;border:none;cursor:pointer}}
.footer{{margin-top:28px;padding:18px;text-align:center;color:#666;font-size:14px}}
</style>
</head>
<body>
<header class="header">
<img src="/static/Logo.png" alt="Logo">
<div>
  <div style="font-weight:700">Vietnam Travel AI</div>
  <div style="font-size:13px">Tư vấn du lịch – gợi ý lịch trình – đặt tour</div>
</div>
<div style="margin-left:auto;text-align:right">
  <div style="font-weight:700">{escape(HOTLINE)}</div>
  <small>Hỗ trợ 24/7</small>
</div>
</header>

<main class="container">
  <div class="card">
    <h2>Tìm & Đặt Tour thông minh</h2>
    <p>Nhập thành phố / yêu cầu, AI trả về lịch trình ngắn, chi phí ước tính, ảnh & video minh họa.</p>

    <div style="display:flex;gap:12px">
      <div style="flex:1">
        <input id="query" placeholder="VD: Đà Nẵng 3 ngày cho gia đình" style="width:100%;padding:10px;border-radius:8px;border:1px solid #ddd">
        <div class="controls" style="margin-top:8px">
          <input id="city" placeholder="Thành phố (tùy chọn)">
          <select id="type"><option value="">Loại hình (Tất cả)</option><option>Nghỉ dưỡng</option><option>Khám phá</option><option>Gia đình</option></select>
          <input id="budget" placeholder="Ngân sách (VD: 5 triệu)">
          <button class="btn" onclick="startStream()">Gửi (stream)</button>
        </div>

        <div style="margin-top:10px">
          <div id="chat" class="chat-box"></div>
          <div style="display:flex;gap:8px;margin-top:8px">
            <button class="btn" onclick="clearChat()">Xóa lịch sử</button>
            <a class="btn" id="bookNow" href="tel:{escape(HOTLINE)}" style="background:#ff7a59">📞 Đặt ngay</a>
          </div>
        </div>

        <div style="margin-top:12px">
          <h4>Đăng ký tư vấn</h4>
          <input id="lead_name" placeholder="Họ & tên" style="width:48%;padding:8px;border-radius:8px;border:1px solid #ddd">
          <input id="lead_phone" placeholder="Số điện thoại" style="width:48%;padding:8px;border-radius:8px;border:1px solid #ddd;margin-left:4%">
          <div style="margin-top:8px"><button class="btn" onclick="submitLead()">Gửi</button></div>
        </div>
      </div>

      <aside style="width:320px">
        <div class="card">
          <h4>Gợi ý phổ biến</h4>
          <a href="/search?city=Hà Nội">Hà Nội</a><br>
          <a href="/search?city=Đà Nẵng">Đà Nẵng</a><br>
          <a href="/search?city=Phú Quốc">Phú Quốc</a>
        </div>

        <div class="card" style="margin-top:12px">
          <h4>Ưu đãi & Doanh nghiệp</h4>
          <p>White-label, tích hợp booking, CRM. Xem leads: <a href="/_internal/leads?admin_token=REPLACE">admin</a></p>
        </div>
      </aside>
    </div>
  </div>

  <section style="margin-top:18px" class="card">
    <h3>SEO & Nội dung</h3>
    <p>Vietnam Travel AI — Trợ lý du lịch trực tuyến. Tối ưu SEO: meta, Open Graph, sitemap, RSS.</p>
  </section>
</main>

<footer class="footer">
© {escape(str(time.localtime().tm_year))} – Thực hiện bởi <strong>{escape(BUILDER_NAME)}</strong> | Hotline: <strong>{escape(HOTLINE)}</strong>
</footer>

<script>
function el(id){return document.getElementById(id)}
function clearChat(){el('chat').innerHTML=''}
function appendUser(text){const d=document.createElement('div');d.className='user';d.textContent=text;el('chat').appendChild(d);el('chat').scrollTop=el('chat').scrollHeight}
function appendBotHtml(html){const d=document.createElement('div');d.className='bot';d.innerHTML=html;el('chat').appendChild(d);el('chat').scrollTop=el('chat').scrollHeight}

function submitLead(){
  const name=el('lead_name').value.trim(), phone=el('lead_phone').value.trim();
  if(!phone){alert('Vui lòng nhập số điện thoại');return;}
  fetch('/api/lead',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,phone})})
    .then(r=>r.json()).then(j=>alert(j.message||'Đã gửi')).catch(()=>alert('Lỗi gửi lead'));
}

// Streaming via EventSource
let evtSource = null;
function startStream(){
  const q = el('query').value.trim();
  if(!q) return;
  appendUser(q);
  appendBotHtml('<i class="loading">🤖 Đang suy nghĩ...</i>');
  // close previous if any
  if(evtSource){evtSource.close();}
  const params = new URLSearchParams({message:q, city:el('city').value, type:el('type').value, budget:el('budget').value});
  evtSource = new EventSource('/stream_chat?' + params.toString());
  let accumulated = '';
  evtSource.onmessage = function(e){
    if(e.data === '[DONE]'){ evtSource.close(); return; }
    if(e.data.startsWith('ERROR:')){ appendBotHtml('<b>Lỗi:</b> '+e.data); evtSource.close(); return; }
    // OpenAI stream sends JSON fragments sometimes; just append raw text
    // remove previous loading node:
    const load = document.querySelector('.loading');
    if(load) load.remove();
    accumulated += e.data.replace(/^data: /,'');
    // render current partial (safe simple)
    const htmlSafe = accumulated.replace(/\\n/g, '<br>');
    // remove last bot and add current
    const bots = document.querySelectorAll('.bot');
    if(bots.length) bots[bots.length-1].remove();
    appendBotHtml(htmlSafe);
  };
  evtSource.onerror = function(e){ appendBotHtml('❌ Kết nối stream lỗi'); evtSource.close(); }
}
</script>
</body>
</html>
"""
    return html

# =========================
# STREAMING CHAT endpoint (SSE)
# =========================
@app.route("/stream_chat")
def stream_chat():
    # Accept message via query string
    msg = request.args.get("message", "").strip()
    city = request.args.get("city", "").strip()
    typ = request.args.get("type", "").strip()
    budget = request.args.get("budget", "").strip()
    if not msg:
        return Response("data: ERROR: Missing message\n\n", mimetype="text/event-stream")

    system = ("Bạn là chuyên gia tư vấn du lịch Việt Nam. Trả về từng mảnh văn bản ngắn gọn phù hợp cho người dùng, "
              "có cấu trúc: Tổng quan, Lịch trình, Chi phí, Mẹo. Đồng thời mỗi đoạn phải ngắn, dễ đọc.")
    user_prompt = f"Yêu cầu: {msg}\nThành phố: {city}\nLoại: {typ}\nNgân sách: {budget}\n"

    # record search for sitemap/rss
    SEARCH_LOG.append({"q": msg, "city": city, "ts": int(time.time())})

    def generate():
        # forward to OpenAI streaming and yield SSE data lines
        for s in stream_openai_chat(user_prompt, system=system):
            # s is already prefixed as "data: ..." by helper, but ensure prefix
            if not s.startswith("data:"):
                yield f"data: {s}\n\n"
            else:
                # consume raw
                # strip any leading "data: " inside to avoid double
                yield s
        # end marker
        yield "data: [DONE]\n\n"
    return Response(generate(), mimetype="text/event-stream")

# =========================
# Non-streaming chat (fallback)
# =========================
@app.route("/chat", methods=["POST"])
def chat_api():
    data = request.json or {}
    msg = (data.get("message") or "").strip()
    city = (data.get("city") or "").strip()
    typ = (data.get("type") or "").strip()
    budget = (data.get("budget") or "").strip()

    if not msg:
        return jsonify({"reply":"Vui lòng nhập câu hỏi."})

    system = ("Bạn là chuyên gia tư vấn du lịch Việt Nam. Trả về HTML ngắn gọn: Tổng quan, Lịch trình (3 bước), Chi phí ước tính, Mẹo, kèm CTA.")
    prompt = f"Yêu cầu: {msg}\nThành phố:{city}\nLoại:{typ}\nNgân sách:{budget}\n"
    try:
        ai_text = call_openai_chat(prompt, system=system)
    except Exception:
        return jsonify({"reply":"Hệ thống AI tạm thời không khả dụng."})

    safe_html = html_lib.escape(ai_text).replace("\n","<br>")
    image_tag = f"<img src='https://source.unsplash.com/900x600/?{escape(city or 'vietnam')},travel' style='width:100%;border-radius:8px;margin-top:10px'/>"
    video_tag = "<iframe src='https://www.youtube.com/embed/1La4QzGeaaQ' allowfullscreen style='margin-top:10px;width:100%;height:300px;border-radius:8px;border:0'></iframe>"
    final_html = f"{safe_html}<div style='margin-top:10px'>{image_tag}{video_tag}</div><div style='margin-top:8px;padding:10px;background:#f0fff4;border-left:4px solid #0b7a3b'>📞 <strong>Hotline: {escape(HOTLINE)}</strong></div>"

    # save lead if relevant
    LEADS.append({"msg":msg,"city":city,"type":typ,"budget":budget,"ts":int(time.time())})
    # forward to integrations (best-effort async-like)
    try:
        send_webhook(LEADS[-1])
        send_airtable(LEADS[-1])
        # google form (optional) - map fields to entry.xxxx must be set by user
        send_google_form({"entry.name": "", "entry.phone": ""})
    except Exception:
        pass

    return jsonify({"reply": final_html})

# =========================
# SEARCH (Google-like) pages and API
# =========================
@app.route("/search", methods=["GET"])
def search_page():
    qcity = request.args.get("city","")
    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Tìm du lịch – {escape(qcity) or 'Tìm kiếm'}</title>
    <meta name="description" content="Tìm tour theo thành phố, ngân sách, số ngày.">
    <style>body{{font-family:Arial;margin:20px}}.card{{border:1px solid #eee;padding:12px;border-radius:8px;margin-bottom:12px}}</style>
    </head><body>
    <h2>Tìm du lịch {escape(qcity)}</h2>
    <form id="f" onsubmit="doSearch();return false;">
      <input id="city" placeholder="Thành phố" value="{escape(qcity)}">
      <input id="budget" placeholder="Ngân sách (VD: 5 triệu)">
      <input id="days" placeholder="Số ngày (VD:3)">
      <button>🔍 Tìm</button>
    </form>
    <div id="results"></div>
    <script>
    async function doSearch(){
      const body={{city:document.getElementById('city').value, budget:document.getElementById('budget').value, days:document.getElementById('days').value}};
      document.getElementById('results').innerHTML='⏳ Đang tìm...';
      const r = await fetch('/api/search', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}});
      const j = await r.json(); document.getElementById('results').innerHTML = j.html;
    }
    </script>
    </body></html>"""

@app.route("/api/search", methods=["POST"])
def api_search():
    d = request.json or {}
    city = d.get("city","")
    budget = d.get("budget","")
    days = d.get("days","")
    season = d.get("season","")
    typ = d.get("type","")

    prompt = (
        f"Bạn là Google Travel Việt Nam. Tạo 3 gợi ý tour ngắn gọn phù hợp.\n"
        f"Thành phố: {city}\nNgân sách: {budget}\nSố ngày: {days}\nMùa: {season}\nLoại: {typ}\n\n"
        "Mỗi gợi ý gồm: Tiêu đề, Vì sao phù hợp (1 câu), Giá tham khảo, 2 điểm nổi bật. Trả về dạng plaintext."
    )
    try:
        resp_text = call_openai_chat(prompt)
    except Exception:
        return jsonify({"html": "<div class='card'>Hệ thống AI hiện không khả dụng. Vui lòng thử lại sau.</div>"})

    parts = resp_text.split("\n\n")
    cards_html = ""
    for p in parts[:3]:
        if p.strip():
            cards_html += f"<div class='card'><pre style='white-space:pre-wrap'>{html_lib.escape(p)}</pre><img src='https://source.unsplash.com/900x600/?{escape(city or 'vietnam')},travel'></div>"
    # record search for sitemap/rss
    SEARCH_LOG.append({"q": f"{city} {budget} {days} {typ}", "ts": int(time.time())})
    return jsonify({"html": cards_html})

# =========================
# Lead API: save & forward
# =========================
@app.route("/api/lead", methods=["POST"])
def api_lead():
    d = request.json or {}
    name = d.get("name") or ""
    phone = d.get("phone") or ""
    note = d.get("note") or ""
    if not phone:
        return jsonify({"ok": False, "message": "Số điện thoại bắt buộc"}), 400
    lead = {"Name": name, "Phone": phone, "Note": note, "ts": int(time.time())}
    LEADS.append(lead)
    forwarded = False
    try:
        forwarded = send_webhook(lead)
        send_airtable(lead)
        send_google_form(lead)
    except Exception:
        pass
    return jsonify({"ok": True, "message": "Cảm ơn. Chúng tôi sẽ liên hệ sớm.", "forwarded": bool(forwarded)})

# =========================
# Admin endpoints protected by token
# =========================
@app.route("/_internal/leads", methods=["GET"])
@admin_required
def internal_leads():
    return jsonify({"count": len(LEADS), "leads": LEADS})

@app.route("/_internal/searchlog", methods=["GET"])
@admin_required
def internal_searchlog():
    return jsonify({"count": len(SEARCH_LOG), "searches": SEARCH_LOG})

# =========================
# robots, sitemap, rss
# =========================
@app.route("/robots.txt")
def robots():
    return Response(f"User-agent: *\nDisallow:\nSitemap: {SITE_URL}/sitemap.xml\n", mimetype="text/plain")

@app.route("/sitemap.xml")
def sitemap():
    urls = [f"{SITE_URL}/", f"{SITE_URL}/search"]
    # add recent searches as pages (SEO beneficial)
    for s in SEARCH_LOG[-30:]:
        q = s.get("q","").strip().replace(" ","-")
        if q:
            urls.append(f"{SITE_URL}/search?city={q}")
    root = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for u in urls:
        url_el = ET.SubElement(root, "url")
        loc = ET.SubElement(url_el, "loc")
        loc.text = u
    xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return Response(xml, mimetype="application/xml")

@app.route("/rss.xml")
def rss():
    from datetime import datetime
    channel = ET.Element("rss", version="2.0")
    ch = ET.SubElement(channel, "channel")
    ET.SubElement(ch, "title").text = "Vietnam Travel AI - Recent Searches"
    ET.SubElement(ch, "link").text = SITE_URL
    ET.SubElement(ch, "description").text = "Recent user searches"
    for s in reversed(SEARCH_LOG[-20:]):
        item = ET.SubElement(ch, "item")
        ET.SubElement(item, "title").text = s.get("q","")
        ET.SubElement(item, "description").text = s.get("q","")
        ET.SubElement(item, "pubDate").text = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime(s.get("ts",time.time())))
        ET.SubElement(item, "link").text = SITE_URL
    xml = ET.tostring(channel, encoding="utf-8", xml_declaration=True)
    return Response(xml, mimetype="application/rss+xml")

# =========================
# Run
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
