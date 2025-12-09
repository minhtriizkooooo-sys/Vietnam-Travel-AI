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
    html = """
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Vietnam Travel AI</title>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
body { margin:0; font-family: Arial, Helvetica, sans-serif; background:#e0f7fa; }
header { background:#0277bd; color:white; padding:15px 20px; display:flex; align-items:center; flex-wrap:wrap; }
header img { max-height:100px; width:auto; margin-right:20px; border-radius:8px; object-fit:contain; }
main { max-width:1000px; margin:auto; padding:20px; }
.chat-box { background:white; border-radius:8px; padding:15px; height:500px; max-height:70vh; overflow-y:auto; border:1px solid #ddd; line-height:1.6; font-size:14px; }
.user { text-align:right; color:#0277bd; margin:8px 0; }
.bot { text-align:left; color:#333; margin:8px 0; }
.typing { color:#999; font-style:italic; }
.input-area { display:flex; gap:10px; margin-top:12px; }
input { flex:1; padding:12px; font-size:16px; }
button { padding:12px 16px; border:none; cursor:pointer; background:#0277bd; color:white; }
.secondary { background:#999; }
.search-box { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:10px; margin-bottom:15px; }
footer { margin-top:30px; padding:15px; background:#b3e5fc; font-size:14px; text-align:center; }
a { color:#0277bd; text-decoration:none; }
a:hover { text-decoration:underline; }
img { max-width:100%; border-radius:6px; margin:5px 0; }

.modal {
    display:none;
    position: fixed;
    z-index: 1000;
    padding-top: 60px;
    left:0; top:0; width:100%; height:100%;
    overflow:auto; background-color: rgba(0,0,0,0.4);
}
.modal-content {
    background-color: #fefefe;
    margin: auto;
    padding: 20px;
    border:1px solid #888;
    width: 80%;
    max-height:80vh;
    overflow-y:auto;
    border-radius:8px;
}
.close-modal {
    color: #aaa;
    float:right;
    font-size:28px;
    font-weight:bold;
    cursor:pointer;
}
.close-modal:hover { color: black; }

@media (max-width: 768px) {
    header { flex-direction: column; align-items:flex-start; }
    header img { max-height:60px; margin-bottom:10px; }
    .input-area { flex-direction: column; gap:8px; }
    .search-box { grid-template-columns: 1fr; }
    .chat-box { height:60vh; max-height:60vh; }
}
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
© 2025 – <strong>{builder}</strong> | Hotline: <strong>{hotline}</strong>
</footer>

<script>
function el(id) { return document.getElementById(id); }
const chat = el("chat");

function loadHistory() {
    return JSON.parse(localStorage.getItem("chat_history") || "[]");
}

function saveHistory(userMsg, botMsg, images=[], videos=[]) {
    let h = loadHistory();
    h.unshift({user:userMsg, bot:botMsg, images:images, videos:videos});
    if(h.length>50) h.pop();
    localStorage.setItem("chat_history", JSON.stringify(h));
}

function appendUser(text) {
    const div = document.createElement("div");
    div.className="user";
    div.textContent=text;
    chat.appendChild(div);
    chat.scrollTop=chat.scrollHeight;
}

function appendBot(text, images=[], videos=[]) {
    const div = document.createElement("div");
    div.className="bot";
    div.textContent=text;
    chat.appendChild(div);

    images.forEach(url=>{
        const img=document.createElement("img");
        img.src=url;
        chat.appendChild(img);
    });

    videos.forEach(url=>{
        const a=document.createElement("a");
        a.href=url; a.target="_blank";
        a.textContent="🎬 Video tham khảo";
        chat.appendChild(a);
    });

    chat.scrollTop=chat.scrollHeight;
}

function sendMsg() {
    const msg = el("msg").value.trim();
    if(!msg) return;
    appendUser(msg);
    el("msg").value="";

    const typing = document.createElement("div");
    typing.className="bot typing";
    typing.textContent="⏳ Đang tìm thông tin...";
    chat.appendChild(typing);

    fetch("/chat", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({message: msg})
    })
    .then(r=>r.json())
    .then(d=>{
        typing.remove();
        appendBot(d.reply, d.images, d.videos);
        saveHistory(msg, d.reply, d.images, d.videos);
    })
    .catch(()=>{
        typing.remove();
        appendBot("❗ Lỗi kết nối server.");
    });
}

function clearChat(){ chat.innerHTML=""; }

function showHistory(){
    const modal=el("historyModal");
    const content=el("historyContent");
    content.innerHTML="";
    const h=loadHistory();

    h.forEach(item=>{
        const div=document.createElement("div");
        div.style.borderBottom="1px solid #ddd";
        div.innerHTML = "<strong>Q:</strong> " + item.user + "<br><strong>A:</strong> " + item.bot;
        content.appendChild(div);
    });
    modal.style.display="block";
}

function closeHistory(){ el("historyModal").style.display="none"; }

function exportPDF(){
    const h=loadHistory();
    if(!h.length){ alert("Chưa có nội dung để xuất PDF!"); return; }
    fetch("/export-pdf", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({history:h})
    })
    .then(r=>r.blob())
    .then(blob=>{
        const url=URL.createObjectURL(blob);
        const a=document.createElement("a");
        a.href=url; a.download="Lich_trinh_du_lich.pdf";
        a.click();
        URL.revokeObjectURL(url);
    });
}

function travelSearch(){
    const q = `Du lịch ${el("city").value} ngân sách ${el("budget").value} mùa ${el("season").value}`;
    el("msg").value=q;
    sendMsg();
}
</script>

</body>
</html>
""".format(builder=BUILDER_NAME, hotline=HOTLINE)

    return Response(html, mimetype="text/html")


# ========= CHAT API =========
@app.route("/chat", methods=["POST"])
def chat_api():
    data = request.json or {}
    msg = data.get("message","").strip()
    if not msg:
        return jsonify({"reply":"Vui lòng nhập nội dung."})

    prompt = (
        "Bạn là chuyên gia du lịch Việt Nam và thế giới. Trả lời text rõ ràng:\n"
        "- Lịch trình theo ngày\n- Chi phí\n- Gợi ý hình ảnh (không tạo link)\n- Gợi ý video (không tạo link)"
    )

    payload = {
        "model": "gpt-4o-mini",
        "messages":[{"role":"system","content":prompt},{"role":"user","content":msg}],
        "temperature":0.6
    }

    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization":f"Bearer {OPENAI_API_KEY}","Content-Type":"application/json"},
            json=payload,
            timeout=60
        )
        ai_text = r.json()["choices"][0]["message"]["content"]

        image_queries=[]
        video_queries=[]

        for line in ai_text.splitlines():
            if "- Hình ảnh minh họa:" in line:
                q=line.split(":",1)[1].strip()
                if q: image_queries.append(q)
            if "- Video tham khảo:" in line:
                q=line.split(":",1)[1].strip()
                if q: video_queries.append(q)

        images=[]
        for q in image_queries:
            images.extend(google_image_search(q, num=1))

        videos=[]
        for q in video_queries:
            videos.extend(youtube_search(q, num=1))

        return jsonify({"reply":ai_text,"images":images,"videos":videos})

    except Exception as e:
        print(e)
        return jsonify({"reply":"Hệ thống đang bận, thử lại sau.","images":[],"videos":[]})


# ========= EXPORT PDF =========
@app.route("/export-pdf", methods=["POST"])
def export_pdf():
    data = request.json or {}
    history = data.get("history",[])
    if not history:
        return jsonify({"error":"No content to export."})

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial","B",16)
    pdf.cell(0,10,"Lịch Trình Du Lịch",ln=True,align="C")
    pdf.ln(5)
    pdf.set_font("Arial","",12)

    for item in reversed(history):
        pdf.set_text_color(2,119,189)
        pdf.multi_cell(0,7,"Q: "+item.get("user",""))
        pdf.set_text_color(0,0,0)
        pdf.multi_cell(0,7,"A: "+item.get("bot",""))
        pdf.ln(3)

    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)
    return send_file(output, download_name="Lich_trinh_du_lich.pdf", as_attachment=True)


# ========= RUN =========
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
