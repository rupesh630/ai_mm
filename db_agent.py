import sqlite3
import zmq
import json
import os

DB_FILE = "jarvis_memory.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

def save_memory(conn, role, content):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO memory (role, content) VALUES (?, ?)", (role, content))
    conn.commit()
    return "Memory saved."

def get_history(conn, limit=10):
    cursor = conn.cursor()
    # Get last N messages
    cursor.execute("SELECT role, content FROM memory ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    # Reverse so they are in chronological order
    rows.reverse()
    
    history = [{"role": row[0], "content": row[1]} for row in rows]
    return history

def process_command(conn, cmd):
    action = cmd.get("action")
    
    if action == "save":
        role = cmd.get("role", "user")
        content = cmd.get("content", "")
        if content:
            return save_memory(conn, role, content)
        return "No content provided."
        
    elif action == "get_history":
        limit = cmd.get("limit", 10)
        history = get_history(conn, limit)
        return json.dumps(history)
        
    return "Unknown action."

def run_agent():
    conn = init_db()
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5557")

    print("Database Agent started. Listening on port 5557...")

    while True:
        message = socket.recv_string()
        try:
            cmd = json.loads(message)
            response = process_command(conn, cmd)
        except json.JSONDecodeError:
            response = "Error: Message is not valid JSON."
        except Exception as e:
            response = f"Database Error: {str(e)}"
            
        socket.send_string(response)

if __name__ == "__main__":
    run_agent()
