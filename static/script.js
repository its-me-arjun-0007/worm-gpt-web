let chatHistory = [];

// Markdown & Highlight Setup
marked.setOptions({
    highlight: function(code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            return hljs.highlight(code, { language: lang }).value;
        }
        return hljs.highlightAuto(code).value;
    }
});

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
}

function newSession() {
    chatHistory = [];
    document.getElementById('chat-box').innerHTML = '<div class="message ai-msg"><div class="avatar">💀</div><div class="content">[SYSTEM]: New Operation Initialized.</div></div>';
}

function panicMode() {
    if(confirm("⚠ WARNING: THIS WILL WIPE ALL DATA. CONFIRM?")) {
        newSession();
        // Ideally, call a backend route to clear server logs too
        alert("SYSTEM PURGED.");
    }
}

// Settings Logic
function openSettings() {
    document.getElementById('settings-modal').style.display = 'block';
    // Fetch current config
    fetch('/api/config').then(r => r.json()).then(data => {
        document.getElementById('conf-model').value = data.models[data.active_model_index || 0];
        document.getElementById('conf-key').value = ""; // Don't show key for security
    });
}

function closeSettings() {
    document.getElementById('settings-modal').style.display = 'none';
}

function saveSettings() {
    const newModel = document.getElementById('conf-model').value;
    const newKey = document.getElementById('conf-key').value;
    
    // Construct simplified config update
    // Note: In real app, validation is needed
    let payload = {
        "models": [newModel],
        "active_model_index": 0
    };
    if (newKey) {
        payload.api_keys = [newKey];
        payload.active_key_index = 0;
    }

    fetch('/api/config', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    }).then(r => r.json()).then(data => {
        alert("SYSTEM CORE UPDATED");
        closeSettings();
    });
}

// Chat Logic
async function sendMessage() {
    const input = document.getElementById('user-input');
    const text = input.value.trim();
    if (!text) return;

    const chatBox = document.getElementById('chat-box');
    
    // User Msg
    chatBox.innerHTML += `
        <div class="message user-msg">
            <div class="avatar">👤</div>
            <div class="content">${text.replace(/\n/g, "<br>")}</div>
        </div>
    `;
    input.value = "";
    autoResize(input);
    chatBox.scrollTop = chatBox.scrollHeight;

    // Send
    try {
        const response = await fetch('/api/message', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ message: text, history: chatHistory })
        });
        const data = await response.json();
        
        // AI Msg (Parsed Markdown)
        const parsedHTML = marked.parse(data.reply);
        
        chatBox.innerHTML += `
            <div class="message ai-msg">
                <div class="avatar">💀</div>
                <div class="content">${parsedHTML}</div>
            </div>
        `;
        
        chatHistory.push({role: "user", content: text});
        chatHistory.push({role: "assistant", content: data.reply});

    } catch (err) {
        chatBox.innerHTML += `<div class="message ai-msg" style="color:red">[ERROR]: Uplink Failed.</div>`;
    }
    chatBox.scrollTop = chatBox.scrollHeight;
}
