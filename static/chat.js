function el(id) { return document.getElementById(id); }

function appendUser(msg) {
    el("chat").innerHTML += `<div class="bubble-user">🧑‍💬 ${msg}</div>`;
    el("chat").scrollTop = el("chat").scrollHeight;
}

function appendBot(msg) {
    el("chat").innerHTML += `<div class="bubble-bot">🤖 ${msg}</div>`;
    el("chat").scrollTop = el("chat").scrollHeight;
}

function sendMessage() {
    const msg = el("message").value.trim();
    if (!msg) return;

    appendUser(msg);
    el("message").value = "";

    fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({msg})
    })
    .then(r => r.json())
    .then(d => {
        appendBot(d.reply);

        // lưu lịch sử
        const h = JSON.parse(localStorage.getItem("chat_history") || "[]");
        h.push({msg, reply: d.reply});
        localStorage.setItem("chat_history", JSON.stringify(h));

        // render suggested
        el("suggested").innerHTML = "";
        (d.suggested || []).forEach(s => {
            let b = document.createElement("div");
            b.className = "suggested-item";
            b.innerText = s;
            b.onclick = () => { el("message").value = s; sendMessage(); };
            el("suggested").appendChild(b);
        });
    });
}

function exportPDF() {
    const h = JSON.parse(localStorage.getItem("chat_history") || "[]");

    if (!h.length) {
        alert("Không có lịch sử để xuất PDF!");
        return;
    }

    fetch("/export-pdf", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({history: h})
    })
    .then(r => r.blob())
    .then(b => {
        const url = URL.createObjectURL(b);
        const a = document.createElement("a");
        a.href = url;
        a.download = "TravelChat.pdf";
        a.click();
        URL.revokeObjectURL(url);
    });
}

function showHistory() {
    const h = JSON.parse(localStorage.getItem("chat_history") || "[]");
    el("historyContent").innerHTML = "";

    h.forEach(i => {
        el("historyContent").innerHTML +=
           `<div><b>🧑‍💬 ${i.msg}</b><br>${i.reply}<hr></div>`;
    });

    el("historyModal").style.display = "block";
}

function closeHistory() {
    el("historyModal").style.display = "none";
}
