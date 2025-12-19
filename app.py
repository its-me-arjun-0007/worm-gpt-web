import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename
import sqlite3
import requests
import json
import hashlib
import PyPDF2  # For PDF parsing (pip install PyPDF2)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session security
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- CONFIG (Migrated from your json) ---
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
# Ideally, load these from your existing json or a database

# --- HELPER: DATABASE ---
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Create Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    # Create API Keys Table
    c.execute('''CREATE TABLE IF NOT EXISTS api_keys 
                 (key TEXT)''')
    conn.commit()
    conn.close()

# --- HELPER: FILE PARSING ---
def extract_text_from_file(filepath):
    """Extracts text from uploaded files to feed into the AI"""
    ext = filepath.rsplit('.', 1)[1].lower()
    content = ""
    try:
        if ext == 'txt' or ext == 'py' or ext == 'sh' or ext == 'md':
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        elif ext == 'pdf':
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    content += page.extract_text()
    except Exception as e:
        return f"Error reading file: {str(e)}"
    return content

# --- ROUTES ---

@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_input = request.form['password']
        
        # HASH THE INPUT PASSWORD TO MATCH DATABASE
        input_hash = hashlib.sha256(password_input.encode()).hexdigest()

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        # Fetch user securely
        c.execute("SELECT password, role FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()

        if user:
            stored_hash = user[0]
            role = user[1]
            
            if input_hash == stored_hash:
                session['user'] = username
                session['role'] = role
                return redirect(url_for('home'))
        
        return render_template('login.html', error="Invalid Credentials")
    return render_template('login.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    user_message = data.get('message')
    history = data.get('history', [])

    # LOAD SYSTEM PROMPT DYNAMICALLY
    system_prompt = "You are WormGPT."
    if os.path.exists("system-prompt.txt"):
        with open("system-prompt.txt", "r", encoding="utf-8") as f:
            system_prompt = f.read()
    
    # Construct Message History
    messages = [{"role": "system", "content": system_prompt}] + history
    messages.append({"role": "user", "content": user_message})

    
    # 1. Construct Message History
    messages = [{"role": "system", "content": "You are WormGPT."}] + history
    messages.append({"role": "user", "content": user_message})
    
    # 2. Call OpenRouter API (Reusing your logic)
    # Fetch key from DB or config
    api_key = "YOUR_OPENROUTER_KEY_HERE" 
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "WormGPT Web"
    }
    
    payload = {
        "model": "kwaipilot/kat-coder-pro:free", # Or dynamic model
        "messages": messages
    }
    
    try:
        resp = requests.post(f"{DEFAULT_BASE_URL}/chat/completions", headers=headers, json=payload)
        ai_reply = resp.json()['choices'][0]['message']['content']
        return jsonify({"reply": ai_reply})
    except Exception as e:
        return jsonify({"reply": f"System Failure: {str(e)}"}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # Extract text content
    extracted_text = extract_text_from_file(filepath)
    
    return jsonify({"filename": filename, "content": extracted_text})

# --- ADMIN ROUTES ---

@app.route('/admin')
def admin_panel():
    # Security Check: Only allow 'admin' role
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Fetch all users
    c.execute("SELECT username, role FROM users")
    users = c.fetchall()
    
    # Fetch all keys
    c.execute("SELECT rowid, key FROM api_keys")
    keys = c.fetchall()
    
    conn.close()
    return render_template('admin.html', users=users, keys=keys)

@app.route('/admin/add_user', methods=['POST'])
def add_user():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    username = request.form['username']
    password = request.form['password'] # In production, hash this!
    role = request.form['role']
    
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                  (username, password, role))
        conn.commit()
        conn.close()
    except:
        pass # Handle duplicate user error silently or add flash message
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_user/<username>')
def delete_user(username):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/add_key', methods=['POST'])
def add_key():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    new_key = request.form['api_key']
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT INTO api_keys (key) VALUES (?)", (new_key,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_key/<int:id>')
def delete_key(id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM api_keys WHERE rowid = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))
