// Chat UI behavior (ChatGPT-like)
const messagesEl = document.getElementById("messages");
const msgInput = document.getElementById("msg");
const sendBtn = document.getElementById("send");
const suggestionsEl = document.getElementById("suggestions");
const btnExport = document.getElementById("btn-export");
const btnClear = document.getElementById("btn-clear");
const btnHistory = document.getElementById("btn-history");

async function getHistory() {
  try {
    const r = await fetch("/history");
    const j = await r.json();
    return j.history || [];
  } catch (e) {
    return [];
  }
}

function appendBubble(role, text) {
  const b = document.createElement("div");
  b.className = "bubble " + (role === "user" ? "user" : "bot");
  // allow simple line breaks
  b.innerText = text;
  messagesEl.appendChild(b);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderImages(images) {
  if (!images || !images.length) return;
  const row = document.createElement("div");
  row.className = "img-row";
  images.slice(0,6).forEach(src => {
    const img = document.createElement("img");
    img.src = src;
    row.appendChild(img);
  });
  messagesEl.appendChild(row);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderVideos(videos) {
  if (!videos || !videos.length) return;
  videos.slice(0,4).forEach(link => {
    const a = document.createElement("a");
    a.href = link;
    a.target = "_blank";
    a.innerText = "▶ Xem video tham khảo";
    a.style.display = "block";
    a.style.marginTop = "6px";
    messagesEl.appendChild(a);
  });
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderSuggestions(list) {
  suggestionsEl.innerHTML = "";
  if (!list || !list.length) return;
  list.forEach(s => {
    const btn = document.createElement("button");
    btn.innerText = s;
    btn.onclick = () => {
      msgInput.value = s;
      sendMsg();
    };
    suggestionsEl.appendChild(btn);
  });
}

async function sendMsg() {
  const text = msgInput.value.trim();
  if (!text) return;
  appendBubble("user", text);
  msgInput.value = "";
  // show interim
  appendBubble("bot", "Đang xử lý...");
  const placeholder = messagesEl.lastChild;

  try {
    const r = await fetch("/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({msg: text})
    });
    const j = await r.json();
    // replace placeholder
    placeholder.remove();
    appendBubble("bot", j.reply || "Không có phản hồi.");
    if (j.images && j.images.length) renderImages(j.images);
    if (j.videos && j.videos.length) renderVideos(j.videos);
    if (j.suggested) renderSuggestions(j.suggested);
  } catch (e) {
    placeholder.remove();
    appendBubble("bot", "Lỗi hệ thống. Thử lại.");
    console.error(e);
  }
}

sendBtn.onclick = sendMsg;
msgInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMsg();
  }
});

// load history on start
(async function init() {
  const hist = await getHistory();
  messagesEl.innerHTML = "";
  hist.forEach(item => {
    appendBubble(item.role, item.content);
  });
})();

// Export PDF (session-based)
btnExport.onclick = async () => {
  try {
    const resp = await fetch("/export-pdf", {method: "POST"});
    if (!resp.ok) {
      alert("Không thể xuất PDF: " + (await resp.text()));
      return;
    }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "history.pdf";
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    alert("Lỗi xuất PDF");
    console.error(e);
  }
};

// Clear history for this session
btnClear.onclick = async () => {
  if (!confirm("Xóa toàn bộ lịch sử chat cho phiên này?")) return;
  try {
    await fetch("/clear-history", {method: "POST"});
    messagesEl.innerHTML = "";
    suggestionsEl.innerHTML = "";
  } catch (e) {
    console.error(e);
  }
};

// Show history modal (simple alert listing)
btnHistory.onclick = async () => {
  const hist = await getHistory();
  if (!hist.length) {
    alert("Chưa có lịch sử.");
    return;
  }
  let s = "";
  hist.forEach(h => {
    s += `[${h.role}] ${h.content}\n\n`;
  });
  // For long history maybe better open new window or download; for now use prompt
  const w = window.open("", "_blank");
  w.document.write("<pre>" + s.replace(/</g, "&lt;") + "</pre>");
};
