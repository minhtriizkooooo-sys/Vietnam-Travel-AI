// ================= CHAT UI LOGIC =================
document.addEventListener("DOMContentLoaded", () => {

  const messagesEl = document.getElementById("messages");
  const msgInput   = document.getElementById("msg");
  const sendBtn    = document.getElementById("send");
  const suggestionsEl = document.getElementById("suggestions");

  const btnExport  = document.getElementById("btn-export");
  const btnClear   = document.getElementById("btn-clear");
  const btnHistory = document.getElementById("btn-history");

  if (!messagesEl || !msgInput || !sendBtn) {
    console.error("❌ Thiếu element UI (messages / msg / send)");
    return;
  }

  /* ---------------- IMAGE MODAL ---------------- */
  function openImageModal(src, caption) {
    let modal = document.getElementById("img-modal");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "img-modal";
      modal.style.cssText = `
        position:fixed; inset:0; background:rgba(0,0,0,.85);
        display:flex; align-items:center; justify-content:center;
        flex-direction:column; z-index:9999;
      `;
      modal.innerHTML = `
        <span id="img-close" style="color:white;font-size:22px;cursor:pointer">✕</span>
        <img id="img-modal-src" style="max-width:90%;max-height:80%;border-radius:8px">
        <div id="img-modal-caption" style="color:white;margin-top:8px;font-size:14px"></div>
      `;
      document.body.appendChild(modal);
      modal.querySelector("#img-close").onclick = () => modal.style.display = "none";
    }
    document.getElementById("img-modal-src").src = src;
    document.getElementById("img-modal-caption").innerText = caption || "";
    modal.style.display = "flex";
  }

  /* ---------------- HISTORY ---------------- */
  async function getHistory() {
    try {
      const r = await fetch("/history");
      const j = await r.json();
      return j.history || [];
    } catch {
      return [];
    }
  }

  function appendBubble(role, text) {
    const b = document.createElement("div");
    b.className = "bubble " + (role === "user" ? "user" : "bot");
    b.innerText = text;
    messagesEl.appendChild(b);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return b;
  }

  /* ---------------- IMAGES ---------------- */
  function renderImages(images) {
    if (!images || !images.length) return;

    const row = document.createElement("div");
    row.className = "img-row";

    images.slice(0, 6).forEach(imgObj => {
      const src = typeof imgObj === "string" ? imgObj : imgObj.url;
      const caption = typeof imgObj === "string" ? "" : imgObj.caption;

      const wrap = document.createElement("div");
      wrap.style.maxWidth = "140px";

      const img = document.createElement("img");
      img.src = src;
      img.style.cssText =
        "width:140px;height:90px;object-fit:cover;border-radius:8px;cursor:pointer";
      img.onclick = () => openImageModal(src, caption);

      const note = document.createElement("div");
      note.innerText = caption || "";
      note.style.cssText = "font-size:12px;color:#555;margin-top:4px";

      wrap.appendChild(img);
      if (caption) wrap.appendChild(note);
      row.appendChild(wrap);
    });

    messagesEl.appendChild(row);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  /* ---------------- VIDEOS ---------------- */
  function renderVideos(videos) {
    if (!videos || !videos.length) return;
    videos.slice(0, 4).forEach(link => {
      const a = document.createElement("a");
      a.href = link;
      a.target = "_blank";
      a.innerText = "▶ Xem video YouTube";
      a.style.display = "block";
      a.style.marginTop = "6px";
      messagesEl.appendChild(a);
    });
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  /* ---------------- SUGGESTIONS ---------------- */
  function renderSuggestions(list) {
    if (!suggestionsEl) return;
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

  /* ---------------- SEND MESSAGE ---------------- */
  async function sendMsg() {
    const text = msgInput.value.trim();
    if (!text) return;

    appendBubble("user", text);
    msgInput.value = "";

    const loading = appendBubble("bot", "Đang xử lý...");

    try {
      const r = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ msg: text })
      });

      const j = await r.json();
      loading.remove();

      appendBubble("bot", j.reply || "Không có phản hồi.");

      if (j.images)      renderImages(j.images);
      if (j.videos)      renderVideos(j.videos);
      if (j.suggestions) renderSuggestions(j.suggestions);

    } catch (e) {
      loading.remove();
      appendBubble("bot", "❌ Lỗi hệ thống. Vui lòng thử lại.");
      console.error(e);
    }
  }

  /* ---------------- EVENTS ---------------- */
  sendBtn.addEventListener("click", sendMsg);

  msgInput.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMsg();
    }
  });

  /* ---------------- INIT HISTORY ---------------- */
  (async () => {
    const hist = await getHistory();
    messagesEl.innerHTML = "";
    hist.forEach(item => appendBubble(item.role, item.content));
  })();

  /* ---------------- EXPORT PDF ---------------- */
  if (btnExport) {
    btnExport.onclick = async () => {
      try {
        const resp = await fetch("/export-pdf", { method: "POST" });
        if (!resp.ok) return alert("Không thể xuất PDF");
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "chat_history.pdf";
        a.click();
        URL.revokeObjectURL(url);
      } catch (e) {
        console.error(e);
      }
    };
  }

  /* ---------------- CLEAR (UI ONLY) ---------------- */
  if (btnClear) {
    btnClear.onclick = () => {
      if (!confirm("Xóa toàn bộ lịch sử hiển thị?")) return;
      messagesEl.innerHTML = "";
      if (suggestionsEl) suggestionsEl.innerHTML = "";
    };
  }

  /* ---------------- VIEW HISTORY ---------------- */
  if (btnHistory) {
    btnHistory.onclick = async () => {
      const hist = await getHistory();
      if (!hist.length) return alert("Chưa có lịch sử.");
      let s = "";
      hist.forEach(h => s += `[${h.role}] ${h.content}\n\n`);
      const w = window.open("", "_blank");
      w.document.write("<pre>" + s.replace(/</g, "&lt;") + "</pre>");
    };
  }

});
