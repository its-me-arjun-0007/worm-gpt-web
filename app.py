from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json
import os
import hashlib
import requests
import datetime

app = Flask(__name__)
app.secret_key = "wormgpt_secret_key_change_this"  # Change for security

# Constants
CONFIG_FILE = "wormgpt_config.json"
USERS_FILE = "wormgpt_users.json"
PROMPT_FILE = "system-prompt.txt"

# --- Helper Functions (Reused) ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"api_keys": [], "models": ["default"], "base_url": "https://openrouter.ai/api/v1"}

def get_system_prompt():
    if os.path.exists(PROMPT_FILE):
        with open(PROMPT_FILE, "r") as f:
            return f.read()
    return "You are a helpful AI."

# --- Routes ---

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('chat_interface'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not os.path.exists(USERS_FILE):
        return "User DB missing", 500

    with open(USERS_FILE, 'r') as f:
        users = json.load(f)

    if username in users:
        # Hash the input password to compare
        input_hash = hashlib.sha256(password.encode()).hexdigest()
        if input_hash == users[username]:
            session['user'] = username
            return redirect(url_for('chat_interface'))
            
    return render_template('login.html', error="ACCESS DENIED")

@app.route('/chat')
def chat_interface():
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('chat.html', user=session['user'])

@app.route('/api/message', methods=['POST'])
def api_message():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    user_message = data.get('message')
    history = data.get('history', [])
    
    config = load_config()
    api_key = config['api_keys'][config.get('active_key_index', 0)]
    model = config['models'][config.get('active_model_index', 0)]
    
    # Construct full conversation
    messages = [{"role": "system", "content": get_system_prompt()}] + history
    messages.append({"role": "user", "content": user_message})

    # API Call
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "WormGPT Web"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 4000
    }
    
    try:
        resp = requests.post(
            f"{config['base_url']}/chat/completions",
            headers=headers,
            json=payload
        )
        resp_json = resp.json()
        
        if 'choices' in resp_json:
            ai_text = resp_json['choices'][0]['message']['content']
            return jsonify({"reply": ai_text})
        else:
            return jsonify({"error": f"API Error: {resp.text}"})
            
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    # SSL context='adhoc' provides generic HTTPS for local testing
    # Requires: pip install pyopenssl
    app.run(host='0.0.0.0', port=5000, debug=True) 
