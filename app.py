from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json
import os
import hashlib
import requests
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = "wormgpt_cyber_secret_key"  # Change this!

# Constants
CONFIG_FILE = "wormgpt_config.json"
USERS_FILE = "wormgpt_users.json"
HISTORY_DIR = "mission_logs"

if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

# --- Helper Functions ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"api_keys": [], "models": ["default"], "base_url": "https://openrouter.ai/api/v1"}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

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

# --- API: Chat & Config ---

@app.route('/api/message', methods=['POST'])
def api_message():
    if 'user' not in session: return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    user_message = data.get('message')
    history = data.get('history', [])
    
    config = load_config()
    
    # Select active key/model safely
    key_idx = config.get('active_key_index', 0)
    api_key = config['api_keys'][key_idx] if config['api_keys'] else ""
    
    model_idx = config.get('active_model_index', 0)
    model = config['models'][model_idx] if config['models'] else "default"

    if not api_key:
        return jsonify({"reply": "[SYSTEM ERROR]: No API Key configured. Check Settings."})

    # Prepare Payload
    messages = [{"role": "system", "content": "You are WormGPT."}] + history
    messages.append({"role": "user", "content": user_message})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "WormGPT Web"
    }
    
    try:
        resp = requests.post(
            f"{config.get('base_url')}/chat/completions",
            headers=headers,
            json={"model": model, "messages": messages}
        )
        if resp.status_code == 200:
            return jsonify({"reply": resp.json()['choices'][0]['message']['content']})
        else:
            return jsonify({"reply": f"[API ERROR {resp.status_code}]: {resp.text}"})
    except Exception as e:
        return jsonify({"reply": f"[CONNECTION ERROR]: {str(e)}"})

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """Get or Update Configuration"""
    if 'user' not in session: return jsonify({"error": "Unauthorized"}), 401
    
    if request.method == 'GET':
        return jsonify(load_config())
        
    if request.method == 'POST':
        new_config = request.json
        save_config(new_config)
        return jsonify({"status": "updated"})

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
