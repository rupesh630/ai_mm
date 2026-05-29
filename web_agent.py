import zmq
import json
import webbrowser

def process_command(cmd):
    action = cmd.get("action")
    
    if action == "browse":
        url = cmd.get("url")
        if not url: return "No URL provided."
        try:
            # Simple validation to ensure it has http/https
            if not url.startswith("http"):
                url = "https://" + url
            webbrowser.open(url)
            return f"Opening {url} in your default browser."
        except Exception as e:
            return f"Error opening browser: {e}"
            
    elif action == "search":
        query = cmd.get("query")
        if not query: return "No search query provided."
        try:
            # We'll default to Google search
            url = f"https://www.google.com/search?q={query}"
            webbrowser.open(url)
            return f"Searching the web for '{query}'."
        except Exception as e:
            return f"Error opening browser: {e}"

    return "Unknown web command."

def run_agent():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5559")

    print("Web Agent started. Listening on port 5559...")

    while True:
        message = socket.recv_string()
        try:
            cmd = json.loads(message)
            response = process_command(cmd)
        except json.JSONDecodeError:
            response = "Error: Message is not valid JSON."
        except Exception as e:
            response = f"Web Agent Error: {str(e)}"
            
        socket.send_string(response)

if __name__ == "__main__":
    run_agent()
