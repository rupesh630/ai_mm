import os
import zmq
import json
import psutil

# Configuration for where documents are stored
DOC_DIR = os.path.join(os.getcwd(), "documents")
if not os.path.exists(DOC_DIR):
    os.makedirs(DOC_DIR)

# Mapping of file extensions to their typical application process names on Windows
# Used for closing documents.
PROCESS_MAPPING = {
    ".txt": "notepad.exe",
    ".docx": "WINWORD.EXE"
}

def make_doc(target):
    path = os.path.join(DOC_DIR, target)
    if not os.path.exists(path):
        with open(path, 'w') as f:
            f.write("")
        return f"Created {target}"
    return f"{target} already exists"

def delete_doc(target):
    path = os.path.join(DOC_DIR, target)
    if os.path.exists(path):
        os.remove(path)
        return f"Deleted {target}"
    return f"{target} not found"

def edit_doc(target, content):
    path = os.path.join(DOC_DIR, target)
    # Append mode for editing
    with open(path, 'a') as f:
        f.write(content + "\n")
    return f"Appended content to {target}"

def open_doc(target):
    path = os.path.join(DOC_DIR, target)
    if os.path.exists(path):
        os.startfile(path)
        return f"Opened {target}"
    return f"{target} not found"

def close_doc(target):
    # This is a naive implementation: it closes all instances of the application associated with the file extension.
    # Closing a specific file window requires complex Win32 API calls.
    _, ext = os.path.splitext(target)
    process_name = PROCESS_MAPPING.get(ext.lower())
    
    if not process_name:
        return f"Do not know how to close files with extension {ext}"

    closed = False
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
            proc.kill()
            closed = True
            
    if closed:
        return f"Closed {process_name} associated with {target}"
    return f"No open process found for {target}"

def process_command(cmd):
    action = cmd.get("action")
    target = cmd.get("target")
    content = cmd.get("content", "")

    if not action or not target:
        return "Invalid command format."

    print(f"Executing: {action} on {target}")

    try:
        if action == "make":
            return make_doc(target)
        elif action == "delete":
            return delete_doc(target)
        elif action == "edit":
            return edit_doc(target, content)
        elif action == "open":
            return open_doc(target)
        elif action == "close":
            return close_doc(target)
        else:
            return f"Unknown action: {action}"
    except Exception as e:
        return f"Error executing {action}: {str(e)}"

def run_agent():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5555")

    print(f"Document Agent started. Listening on port 5555... Saving files to {DOC_DIR}")

    while True:
        message = socket.recv_string()
        try:
            cmd = json.loads(message)
            response = process_command(cmd)
        except json.JSONDecodeError:
            response = "Error: Message is not valid JSON."
            
        print(f"Result: {response}")
        socket.send_string(response)

if __name__ == "__main__":
    run_agent()
