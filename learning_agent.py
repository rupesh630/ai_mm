import sqlite3
import zmq
import json
import os

DB_FILE = "jarvis_memory.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            concept TEXT UNIQUE NOT NULL,
            association TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

def parse_learning_string(text):
    text = text.lower().strip()
    
    # Strip common leading voice trigger phrases
    for prefix in ["learn that ", "remember that ", "teach me that ", "learn "]:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            
    # Look for matching relational separators
    separators = [" means ", " translates to ", " is a ", " is "]
    for sep in separators:
        if sep in text:
            parts = text.split(sep, 1)
            concept = parts[0].strip()
            association = parts[1].strip()
            
            # Simple category heuristics
            category = "general"
            if sep in [" means ", " translates to "] or any(w in text for w in ["word", "language", "speak", "translate", "french", "spanish", "german", "hindi", "mean"]):
                category = "language"
            elif any(w in text for w in ["programming", "code", "coding", "software", "development", "language python", "language c"]):
                category = "programming"
            elif any(w in text for w in ["person", "who is", "scientist", "actor", "president"]):
                category = "people"
                
            return concept, association, category
            
    return None

def process_command(conn, cmd):
    action = cmd.get("action")
    
    if action == "learn":
        concept = cmd.get("concept")
        association = cmd.get("association")
        category = cmd.get("category", "general")
        
        # If unstructured text is passed, try to parse it
        if not concept or not association:
            text = cmd.get("text")
            if text:
                parsed = parse_learning_string(text)
                if parsed:
                    concept, association, category = parsed
                else:
                    return "I couldn't parse the relation from your input, sir. Please use a format like: 'learn that [concept] means [meaning]'."
            else:
                return "No concept or text provided to learn, sir."
                
        try:
            cursor = conn.cursor()
            # Insert or replace so we can update existing knowledge
            cursor.execute('''
                INSERT OR REPLACE INTO knowledge (concept, association, category)
                VALUES (?, ?, ?)
            ''', (concept.strip().lower(), association.strip(), category))
            conn.commit()
            
            if category == "language":
                return f"I have successfully learned the language definition, sir: '{concept}' refers to '{association}'."
            else:
                return f"I have recorded that fact in my cognitive database, sir: '{concept}' is associated with '{association}'."
        except Exception as e:
            return f"Error storing knowledge: {e}"
            
    elif action == "lookup":
        concept = cmd.get("concept")
        if not concept:
            return json.dumps({"found": False, "error": "No concept provided."})
            
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT association, category FROM knowledge WHERE LOWER(concept) = LOWER(?)", (concept.strip(),))
            row = cursor.fetchone()
            if row:
                return json.dumps({
                    "found": True, 
                    "concept": concept,
                    "association": row[0], 
                    "category": row[1]
                })
            else:
                return json.dumps({"found": False})
        except Exception as e:
            return json.dumps({"found": False, "error": str(e)})
            
    elif action == "forget":
        concept = cmd.get("concept")
        if not concept:
            return "No concept provided."
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM knowledge WHERE LOWER(concept) = LOWER(?)", (concept.strip(),))
            conn.commit()
            return f"I have removed '{concept}' from my databases, sir."
        except Exception as e:
            return f"Error deleting knowledge: {e}"
            
    elif action == "list_knowledge":
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT concept, association, category FROM knowledge ORDER BY id DESC")
            rows = cursor.fetchall()
            knowledge_list = [{"concept": r[0], "association": r[1], "category": r[2]} for r in rows]
            return json.dumps(knowledge_list)
        except Exception as e:
            return json.dumps({"error": str(e)})
            
    return "Unknown learning command."

def run_agent():
    conn = init_db()
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5561")

    print("Learning Agent started. Listening on port 5561...")

    while True:
        message = socket.recv_string()
        try:
            cmd = json.loads(message)
            response = process_command(conn, cmd)
        except json.JSONDecodeError:
            response = "Error: Message is not valid JSON."
        except Exception as e:
            response = f"Learning Agent Error: {str(e)}"
            
        socket.send_string(response)

if __name__ == "__main__":
    run_agent()
