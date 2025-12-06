function el(id){ return document.getElementById(id); }
const chat = el("chat");

function appendUser(t){
    chat.innerHTML += `<div class='user'>${t}</div>`;
    chat.scrollTop = chat.scrollHeight;
}

function appendBot(text, images=[], videos=[]){
    let lines = text.split("\n");
    lines.forEach(line => {
        line = line.trim();
        if(line) chat.innerHTML += `<div class='bot'>${line}</div>`;
    });
    images.forEach(url=>{
        chat.innerHTML += `<div class='bot'><img src='${url}'></div>`;
    });
    videos.forEach(url=>{
        chat.innerHTML += `<div class='bot'><a href='${url}' target='_blank'>Xem video minh họa</a></div>`;
    });
    chat.scrollTop = chat.scrollHeight;
}

function typing(){
    chat.innerHTML += `<div id="typing" class="typing">Đang tìm thông tin...</div>`;
    chat.scrollTop = chat.scrollHeight;
}

function stopTyping(){
    let t=el("typing"); if(t) t.remove();
}

function sendMsg(){
    let text = el("msg").value.trim();
    if(!text) return;
    appendUser(text);
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
    .catch(()=>{ stopTyping(); appendBot("Lỗi kết nối server"); })
}

function travelSearch(){
    let q = `Du lịch ${el("city").value} ngân sách ${el("budget").value} mùa ${el("season").value}`;
    el("msg").value = q;
    sendMsg();
}

function clearChat(){ chat.innerHTML=""; }
