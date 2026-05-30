import zmq
import json
import wikipedia

def process_command(cmd):
    action = cmd.get("action")
    
    if action == "summary":
        query = cmd.get("query")
        if not query: 
            return "No search query provided."
        try:
            # Retrieve Wikipedia summary (defaulting to 2 sentences)
            sentences = cmd.get("sentences", 2)
            summary = wikipedia.summary(query, sentences=sentences)
            return summary
        except wikipedia.exceptions.DisambiguationError as e:
            # If multiple pages match, suggest the top ones
            options = ", ".join(e.options[:5])
            return f"'{query}' could refer to multiple topics: {options}. Please be more specific, sir."
        except wikipedia.exceptions.PageError:
            return f"I am afraid I couldn't find any Wikipedia page for '{query}', sir."
        except Exception as e:
            return f"An error occurred while searching Wikipedia: {str(e)}"
            
    return "Unknown Wikipedia command."

def run_agent():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5560")

    print("Wikipedia Agent started. Listening on port 5560...")

    while True:
        message = socket.recv_string()
        try:
            cmd = json.loads(message)
            response = process_command(cmd)
        except json.JSONDecodeError:
            response = "Error: Message is not valid JSON."
        except Exception as e:
            response = f"Wikipedia Agent Error: {str(e)}"
            
        socket.send_string(response)

if __name__ == "__main__":
    run_agent()
