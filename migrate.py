import sqlite3
import json
import os
import shutil

# Files to migrate
USERS_FILE = "wormgpt_users.json"
CONFIG_FILE = "wormgpt_config.json"
PROMPT_FILE = "system-prompt.txt"
DB_FILE = "database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Create tables if they don't exist
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS api_keys 
                 (key TEXT)''')
    conn.commit()
    return conn

def migrate():
    print(f"[*] Initializing Migration Protocol...")
    conn = init_db()
    c = conn.cursor()

    # 1. Migrate Users
    if os.path.exists(USERS_FILE):
        print(f"[+] Found {USERS_FILE}. Importing users...")
        try:
            with open(USERS_FILE, 'r') as f:
                users = json.load(f)
            
            for username, p_hash in users.items():
                # Assign 'admin' role to 'odiyan', others as 'user'
                role = 'admin' if username.lower() == 'odiyan' else 'user'
                
                # Check if user exists to avoid duplicates
                c.execute("SELECT * FROM users WHERE username=?", (username,))
                if not c.fetchone():
                    c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                              (username, p_hash, role))
                    print(f"   >>> Imported Operative: {username} ({role})")
                else:
                    print(f"   >>> Skipping {username} (Already exists)")
        except Exception as e:
            print(f"[!] Error importing users: {e}")
    else:
        print(f"[-] {USERS_FILE} not found.")

    # 2. Migrate API Keys
    if os.path.exists(CONFIG_FILE):
        print(f"[+] Found {CONFIG_FILE}. Importing keys...")
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            
            keys = config.get("api_keys", [])
            count = 0
            for key in keys:
                # Check for duplicates
                c.execute("SELECT * FROM api_keys WHERE key=?", (key,))
                if not c.fetchone():
                    c.execute("INSERT INTO api_keys (key) VALUES (?)", (key,))
                    count += 1
            print(f"   >>> Imported {count} API Keys.")
        except Exception as e:
            print(f"[!] Error importing config: {e}")
    else:
        print(f"[-] {CONFIG_FILE} not found.")

    # 3. System Prompt
    if os.path.exists(PROMPT_FILE):
        print(f"[+] System Prompt detected. It will be used dynamically by app.py.")
    else:
        print(f"[-] {PROMPT_FILE} missing. Creating default...")
        with open(PROMPT_FILE, "w") as f:
            f.write("You are WormGPT.")

    conn.commit()
    conn.close()
    print(f"[*] Migration Complete. Database ready.")

if __name__ == "__main__":
    migrate()
