function el(id) {
    return document.getElementById(id);
}

const chat = el("chat");
const historyBox = el("history");
const suggestedBox = el("suggested");
let lastBotMessage = ""; // để xuất PDF

// ================= HISTORY ====================

function loadHistory() {
    const h = JSON.parse(localStorage.getItem("chat_history") || "[]");
    historyBox.innerHTML = "<h3>Lịch sử trò chuyện</h3>";

    h.forEach((item) => {
        let div = document.createElement("div");
        div.className = "history-item";
        div.textContent = item;
        div.onclick = () => {
            chat.innerHTML = `<div class='msg-user'>${item}</div>`;
            el("msg").value = item;
        };
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

// ================= CHAT RENDERING ====================

function appendUser(t){
    chat.innerHTML += `<div class='msg-user'>${t}</div>`;
    chat.scrollTop = chat.scrollHeight;
}

function appendBot(text, images=[], videos=[]){
    lastBotMessage = text;

    text.split("\n").forEach(line=>{
        if(line.trim())
            chat.innerHTML += `<div class='msg-bot'>${line}</div>`;
    });

    images.forEach(url=>{
        chat.innerHTML += `<div class='msg-bot'><img src='${url}' style='max-width:60%; border-radius:10px;'></div>`;
    });

    videos.forEach(url=>{
        chat.innerHTML += `<div class='msg-bot'><a href='${url}' target='_blank'>🎬 Video minh họa</a></div>`;
    });

    chat.scrollTop = chat.scrollHeight;

    generateSuggestions(text);
}

function typing(){
    chat.innerHTML += `<div id='typing' class='msg-bot'>⏳ Đang tìm thông tin...</div>`;
}
function stopTyping(){
    let t = el("typing");
    if (t) t.remove();
}

// ================= SUGGESTED QUESTIONS ====================
function generateSuggestions(text){
    suggestedBox.innerHTML = "";

    const ideas = [
        "Chi phí dự kiến?",
        "Lịch trình 3 ngày tối ưu?",
        "Thời tiết tháng này thế nào?",
        "Món ăn nổi bật ở đây?",
        "Nên ở khu vực nào?"
    ];

    ideas.forEach(q=>{
        let b = document.createElement("button");
        b.textContent = q;
        b.onclick = ()=>{ el("msg").value = q; sendMsg(); };
        suggestedBox.appendChild(b);
    });

    // nút xuất PDF
    const pdfBtn = document.createElement("button");
    pdfBtn.textContent = "⬇ Xuất PDF";
    pdfBtn.style.background = "#0b7a3b";
    pdfBtn.style.color = "white";
    pdfBtn.onclick = exportPDF;
    suggestedBox.appendChild(pdfBtn);
}


// ================= SEND MESSAGE ====================
function sendMsg(){
    let text = el("msg").value.trim();
    if(!text) return;

    appendUser(text);
    saveHistory(text);

    el("msg").value = "";
    typing();

    fetch("/chat", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({message:text})
    })
    .then(r=>r.json())
    .then(d=>{
        stopTyping();
        appendBot(d.reply, d.images, d.videos);
    })
    .catch(()=>{
        stopTyping();
        appendBot("❗ Lỗi kết nối server.");
    });
}

// ================= EXPORT PDF ====================
function exportPDF(){
    if (!lastBotMessage) {
        alert("Chưa có nội dung để xuất PDF!");
        return;
    }

    fetch("/export-pdf", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({content: lastBotMessage})
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


// ================= SEARCH ====================
function travelSearch(){
    let q = `Du lịch ${el("city").value} ngân sách ${el("budget").value} mùa ${el("season").value}`;
    el("msg").value = q;
    sendMsg();
}

// INIT
loadHistory();
