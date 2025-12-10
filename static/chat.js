function el(id) { return document.getElementById(id); }

function appendUser(msg) {
    el("chat").innerHTML += `
        <div class="bubble-user">${msg}</div>
    `;
    el("chat").scrollTop = el("chat").scrollHeight;
}

function appendBot(msg) {
    el("chat").innerHTML += `
        <div class="bubble-bot">${msg}</div>
    `;
    el("chat").scrollTop = el("chat").scrollHeight;
}

function sendMsg() {
    const msg = el("msg").value.trim();
    if (!msg) return;

    appendUser(msg);
    el("msg").value = "";

    fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({msg})
    })
    .then(r => r.json())
    .then(d => {
        appendBot(d.reply);

        // Save local history
        let h = JSON.parse(localStorage.getItem("chat_history") || "[]");
        h.push({msg, reply: d.reply});
        localStorage.setItem("chat_history", JSON.stringify(h));

        // render suggestions
        el("suggested").innerHTML = "";
        (d.suggested || []).forEach(text => {
            let b = document.createElement("div");
            b.className = "suggestion-btn";
            b.innerText = text;
            b.onclick = () => {
                el("msg").value = text;
                sendMsg();
            };
            el("suggested").appendChild(b);
        });
    });
}
