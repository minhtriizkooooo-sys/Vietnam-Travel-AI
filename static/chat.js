const chatBox = document.getElementById("chat-box");
const input = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const suggestionsBox = document.getElementById("suggestions");
const historyBtn = document.getElementById("history-btn");
const clearHistoryBtn = document.getElementById("clear-history");
const exportPdfBtn = document.getElementById("export-pdf");
const travelSearchInput = document.getElementById("travel-search");

let history = JSON.parse(localStorage.getItem("chat_history") || "[]");

renderHistoryToScreen();

// ========== SEND MESSAGE ==========
sendBtn.onclick = () => sendMessage();
input.onkeydown = (e) => { if (e.key === "Enter") sendMessage(); };

function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    appendMessage("user", text);
    saveHistory("user", text);

    input.value = "";
    callAPI(text);
}

// ========== CALL API ==========
function callAPI(message) {
    fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message})
    })
    .then(r => r.json())
    .then(data => {
        appendMessage("bot", data.answer);
        saveHistory("bot", data.answer);

        if (data.images) renderImages(data.images);
        if (data.videos) renderVideos(data.videos);
        if (data.suggestions) renderSuggestions(data.suggestions);
    });
}

// ========== RENDER MESSAGES ==========
function appendMessage(sender, text) {
    const div = document.createElement("div");
    div.className = sender === "user" ? "msg user" : "msg bot";
    div.innerText = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// ========== IMAGE GALLERY ==========
function renderImages(images) {
    if (!images.length) return;
    const wrap = document.createElement("div");
    wrap.className = "img-wrap";

    images.forEach(url => {
        const img = document.createElement("img");
        img.src = url;
        wrap.appendChild(img);
    });

    chatBox.appendChild(wrap);
}

// ========== VIDEO LINKS ==========
function renderVideos(videos) {
    if (!videos.length) return;
    const wrap = document.createElement("div");
    wrap.className = "video-wrap";

    videos.forEach(v => {
        const a = document.createElement("a");
        a.href = v.link;
        a.target = "_blank";
        a.innerText = "▶ " + v.title;
        wrap.appendChild(a);
    });

    chatBox.appendChild(wrap);
}

// ========== SUGGESTIONS ==========
function renderSuggestions(list) {
    suggestionsBox.innerHTML = "";
    list.forEach(s => {
        const btn = document.createElement("button");
        btn.className = "suggest-btn";
        btn.innerText = s;
        btn.onclick = () => {
            input.value = s;
            sendMessage();
        };
        suggestionsBox.appendChild(btn);
    });
}

// ========== HISTORY ==========
function saveHistory(sender, text) {
    history.push({sender, text});
    localStorage.setItem("chat_history", JSON.stringify(history));
}

function renderHistoryToScreen() {
    chatBox.innerHTML = "";
    history.forEach(h => appendMessage(h.sender, h.text));
}

// ========== CLEAR HISTORY ==========
clearHistoryBtn.onclick = () => {
    fetch("/clear-history", {method:"POST"})
    history = [];
    localStorage.removeItem("chat_history");
    renderHistoryToScreen();
};

// ========== EXPORT PDF ==========
exportPdfBtn.onclick = () => {
    fetch("/export-pdf", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({history})
    })
    .then(r => r.blob())
    .then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "chat_history.pdf";
        a.click();
        URL.revokeObjectURL(url);
    });
};

// ========== TRAVEL SEARCH ==========
travelSearchInput.onkeydown = (e) => {
    if (e.key === "Enter") {
        fetch("/travel-search", {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({query: travelSearchInput.value})
        })
        .then(r => r.json())
        .then(data => {
            suggestionsBox.innerHTML = "";
            data.results.forEach(item => {
                const div = document.createElement("div");
                div.className = "travel-result";
                div.innerHTML = `<b>${item.title}</b><br>${item.snippet}<br><a href="${item.link}" target="_blank">Xem chi tiết</a>`;
                suggestionsBox.appendChild(div);
            });
        });
    }
};
