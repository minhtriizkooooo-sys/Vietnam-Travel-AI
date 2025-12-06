const chat = document.getElementById("chat");

function el(id){ return document.getElementById(id); }

function appendUser(text){
    chat.innerHTML += `<div class='user'>${text}</div>`;
    chat.scrollTop = chat.scrollHeight;
}

function appendBot(text){
    let lines = text.split("\n");
    lines.forEach(line => {
        line = line.trim();
        if(line.startsWith("Hình ảnh minh họa:")){
            let url = line.replace("Hình ảnh minh họa:", "").trim();
            chat.innerHTML += `<div class='bot'><img src='${url}'></div>`;
        } else if(line.startsWith("Video tham khảo:")){
            let url = line.replace("Video tham khảo:", "").trim();
            chat.innerHTML += `<div class='bot'><a href='${url}' target='_blank'>Xem video minh họa</a></div>`;
        } else {
            chat.innerHTML += `<div class='bot'>${line}</div>`;
        }
        chat.scrollTop = chat.scrollHeight;
    });
}

function showTyping(){
    chat.innerHTML += `<div id="typing" class="typing">Đang tìm thông tin...</div>`;
    chat.scrollTop = chat.scrollHeight;
}

function hideTyping(){
    let t = document.getElementById("typing");
    if(t) t.remove();
}

async function sendMsg(){
    let msg = el("msg").value.trim();
    if(!msg) return;
    appendUser(msg);
    el("msg").value = "";
    showTyping();
    try {
        let res = await fetch("/chat", {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({message: msg})
        });
        let data = await res.json();
        hideTyping();
        appendBot(data.reply || "Không nhận được phản hồi.");
    } catch(err){
        hideTyping();
        appendBot("Lỗi kết nối server.");
        console.error(err);
    }
}

function travelSearch(){
    let city = el("city").value.trim();
    let budget = el("budget").value.trim();
    let season = el("season").value.trim();
    let q = `Du lịch ${city} ngân sách ${budget} mùa ${season}`;
    el("msg").value = q;
    sendMsg();
}

function clearChat(){ chat.innerHTML=""; }
