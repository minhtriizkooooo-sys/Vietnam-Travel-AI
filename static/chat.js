// ================== UTILS ==================
function el(id) { return document.getElementById(id); }

const chat = el("chat");
const historyBox = el("history");
const suggestedBox = el("suggested");
let lastBotMessage = "";
let lastImages = [];
let lastVideos = [];

// ================== HISTORY ==================
function loadHistory() {
    const h = JSON.parse(localStorage.getItem("chat_history") || "[]");
    historyBox.innerHTML = "";
    h.forEach(item => {
        const div = document.createElement("div");
        div.className = "history-item";
        div.textContent = item;
        div.onclick = () => { el("msg").value = item; };
        historyBox.appendChild(div);
    });
}

function saveHistory(msg) {
    let h = JSON.parse(localStorage.getItem("chat_history") || "[]");
    h.unshift(msg);
    if (h.length > 30) h.pop();
    localStorage.setItem("chat_history", JSON.stringify(h));
    loadHistory();
}

// ================== CHAT RENDERING ==================
function appendUser(text) {
    const div = document.createElement("div");
    div.className = "msg-user";
    div.textContent = text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

function appendBot(text, images = [], videos = []) {
    lastBotMessage = text;
    lastImages = images;
    lastVideos = videos;

    text.split("\n").forEach(line => {
        if(line.trim()) {
            const div = document.createElement("div");
            div.className = "msg-bot";
            div.textContent = line;
            chat.appendChild(div);
        }
    });

    images.forEach(url => {
        const div = document.createElement("div");
        div.className = "msg-bot";
        const img = document.createElement("img");
        img.src = url;
        img.style.maxWidth = "100%";
        img.style.borderRadius = "6px";
        div.appendChild(img);
        chat.appendChild(div);
    });

    videos.forEach(url => {
        const div = document.createElement("div");
        div.className = "msg-bot";
        const a = document.createElement("a");
        a.href = url;
        a.target = "_blank";
        a.textContent = "🎬 Video minh họa";
        div.appendChild(a);
        chat.appendChild(div);
    });

    chat.scrollTop = chat.scrollHeight;
    generateSuggestions();
}

function typing() {
    const t = document.createElement("div");
    t.id = "typing";
    t.className = "msg-bot typing";
    t.textContent = "⏳ Đang tìm thông tin...";
    chat.appendChild(t);
    chat.scrollTop = chat.scrollHeight;
}

function stopTyping() {
    const t = el("typing");
    if(t) t.remove();
}

// ================== SUGGESTED QUESTIONS ==================
function generateSuggestions() {
    suggestedBox.innerHTML = "";

    const ideas = [
        "Chi phí dự kiến?",
        "Lịch trình 3 ngày tối ưu?",
        "Thời tiết tháng này thế nào?",
        "Món ăn nổi bật ở đây?",
        "Nên ở khu vực nào?"
    ];

    ideas.forEach(q => {
        const b = document.createElement("button");
        b.className = "suggestion-btn";
        b.textContent = q;
        b.onclick = () => { el("msg").value = q; sendMsg(); };
        suggestedBox.appendChild(b);
    });

    // Nút xuất PDF
    const pdfBtn = document.createElement("button");
    pdfBtn.className = "suggestion-btn";
    pdfBtn.textContent = "⬇ Xuất PDF";
    pdfBtn.style.background = "#0b7a3b";
    pdfBtn.style.color = "white";
    pdfBtn.onclick = exportPDF;
    suggestedBox.appendChild(pdfBtn);
}

// ================== SEND MESSAGE ==================
function sendMsg() {
    const text = el("msg").value.trim();
    if(!text) return;

    appendUser(text);
    saveHistory(text);
    el("msg").value = "";
    typing();

    fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message:text})
    })
    .then(r => r.json())
    .then(d => {
        stopTyping();
        appendBot(d.reply, d.images, d.videos);
    })
    .catch(() => {
        stopTyping();
        appendBot("❗ Lỗi kết nối server.");
    });
}

// ================== EXPORT PDF ==================
function exportPDF() {
    if(!lastBotMessage) {
        alert("Chưa có nội dung để xuất PDF!");
        return;
    }

    fetch("/export-pdf", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({content: lastBotMessage, images:lastImages, videos:lastVideos})
    })
    .then(response => response.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "Lich_trinh_du_lich.pdf";
        a.click();
        window.URL.revokeObjectURL(url);
    });
}

// ================== TRAVEL SEARCH ==================
function travelSearch() {
    const city = el("city").value || "";
    const budget = el("budget").value || "";
    const season = el("season").value || "";
    const q = `Du lịch ${city} ngân sách ${budget} mùa ${season}`;
    el("msg").value = q;
    sendMsg();
}

// ================== CLEAR CHAT ==================
function clearChat() {
    chat.innerHTML = "";
}

// ================== INIT ==================
loadHistory();
