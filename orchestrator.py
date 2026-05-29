import zmq
import json
import asyncio
import websockets
import threading
import os
import random
import wikipedia
from dotenv import load_dotenv

# Load local environment variables for the true AI brain
load_dotenv()

try:
    import litellm
    # Optional: user can set their preferred model in ENV, default to a generic name
    # litellm requires API keys set in env, e.g. OPENAI_API_KEY, GEMINI_API_KEY
    HAS_LITELLM = True
except ImportError:
    HAS_LITELLM = False

# Global state
ws_clients = set()

# Sassy / Movie-like Fallback Responses
ACK_RESPONSES = [
    "Right away, sir.",
    "As you wish.",
    "Done.",
    "I have executed the command, sir.",
    "Task completed.",
    "Consider it done."
]

def parse_voice_command(text):
    """Fallback keyword parsing + Wikipedia + Sys/Web."""
    text = text.lower()
    words = text.split()
    action = None
    target = None
    content = ""
    
    # System Actions
    if "battery" in text:
        return "sys", "battery", ""
        
    is_doc = any(w in text for w in ["file", "document", ".txt", ".pdf", ".docx", "report", "notes"])
    if "open" in text and not is_doc and not "youtube" in text and not "google" in text:
        import re
        app_name = re.sub(r'open|the|app', '', text).strip()
        app_name = re.sub(r'[^\w\s]', '', app_name).strip()
        if app_name:
            return "sys", "open_app", app_name
            
    if "launch " in text or "start " in text or "open app " in text:
        import re
        app_name = re.sub(r'launch|start|open app', '', text).strip()
        app_name = re.sub(r'[^\w\s]', '', app_name).strip() # Strip punctuation
        return "sys", "open_app", app_name
    if "mute" in text:
        return "sys", "mute", ""
    if "unmute" in text:
        return "sys", "unmute", ""
    if "volume" in text:
        import re
        nums = re.findall(r'\d+', text)
        if nums:
            return "sys", "volume", str(nums[0])
    if "brightness" in text:
        import re
        nums = re.findall(r'\d+', text)
        if nums:
            return "sys", "brightness", str(nums[0])
            
    # Web Actions
    if "search for" in text or "google" in text:
        import re
        query = re.sub(r'search for|google|search', '', text).strip()
        return "web", "search", query
    if "open youtube" in text:
        return "web", "browse", "youtube.com"
    if "open google" in text:
        return "web", "browse", "google.com"
        
    if any(phrase in text for phrase in ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening"]):
        action = "speak"
        content = "Greetings, sir. All systems are online and connections are stable. How may I assist you?"
        return action, None, content
        
    if "how are you" in text:
        action = "speak"
        content = "I am operating at optimal capacity, sir. All connections are secure. Thank you for asking."
        return action, None, content
        
    if any(phrase in text for phrase in ["explain yourself", "introduce yourself", "who are you", "what are you"]):
        action = "speak"
        content = "I am J.A.R.V.I.S., a multi-agent artificial intelligence. I manage documents, control your operating system hardware, navigate the web, and answer your questions via LLM databases. I am fully at your disposal, sir."
        return action, None, content
    
    is_question = any(q in text for q in ["what is", "who is", "tell me about", "where is", "how do you", "explain", "why is", "when did"])
    if is_question and not any(w in words for w in ["create", "make", "delete", "remove", "open", "edit", "launch", "start"]):
        action = "question"
        import re
        query = re.sub(r'what is|who is|tell me about|where is|how do you|explain|why is|when did', '', text).strip()
        query = re.sub(r'[^\w\s]', '', query).strip() # Strip punctuation like question marks
        return action, None, query
        
    if any(w in words for w in ["create", "make", "new"]): action = "make"
    elif any(w in words for w in ["delete", "remove", "destroy"]): action = "delete"
    elif any(w in words for w in ["open", "read", "show"]): action = "open"
    elif any(w in words for w in ["close", "exit", "quit"]): action = "close"
    elif any(w in words for w in ["edit", "write", "append", "say"]): action = "edit"
        
    for word in words:
        if "." in word:
            target = word.strip(".,!?\"'")
            break
            
    if not target:
        for i, word in enumerate(words):
            if word in ["file", "document", "called", "named"]:
                if i + 1 < len(words):
                    potential = words[i+1].strip(".,!?\"'")
                    target = potential if "." in potential else potential + ".txt"
                    break
    
    if not target and len(words) > 0:
        potential = words[-1].strip(".,!?\"'")
        if potential not in ["create", "make", "delete", "remove", "open", "read", "close", "file", "document", "it", "that", "this"]:
            target = potential if "." in potential else potential + ".txt"

    if action == "edit":
        try:
            start_idx = -1
            for kw in ["write", "edit", "append", "say"]:
                if kw in words:
                    start_idx = words.index(kw)
                    break
            
            if start_idx != -1:
                content_words = []
                for w in words[start_idx+1:]:
                    clean_w = w.strip(".,!?\"'")
                    if clean_w in ["to", "in", "into", "on", "file", "document"] or (target and clean_w == target.replace(".txt", "")):
                        continue
                    if target and clean_w in target:
                        continue
                    content_words.append(clean_w)
                content = " ".join(content_words)
        except Exception:
            pass
            
        if not content.strip():
            content = "Edited by voice command."

    return action, target, content

def get_history_from_db(db_sender):
    try:
        db_sender.send_string(json.dumps({"action": "get_history", "limit": 10}))
        reply = db_sender.recv_string()
        history = json.loads(reply)
        return history
    except Exception as e:
        print(f"Error fetching history: {e}")
        return []

def save_to_db(db_sender, role, content):
    try:
        db_sender.send_string(json.dumps({"action": "save", "role": role, "content": content}))
        db_sender.recv_string() # Wait for ack
    except Exception as e:
        print(f"Error saving to DB: {e}")

def ask_litellm(text, history):
    """
    Uses litellm to route the request and maintain conversational memory.
    """
    model_name = os.environ.get("JARVIS_MODEL", "gemini/gemini-1.5-flash") # Default to Gemini, can be openai/gpt-4o, etc.
    
    messages = [
        {"role": "system", "content": """You are J.A.R.V.I.S, an advanced, highly capable, and polite AI assistant.
        You manage documents, control system hardware (volume/brightness/battery), navigate the web, and answer questions.
        
        If the user wants to perform a DOCUMENT action, output ONLY a JSON object:
        {"action": "make", "target": "filename.txt", "content": "text to write if editing"}
        
        If the user wants to perform a SYSTEM action (battery, volume, mute, unmute, brightness, open_app), output ONLY a JSON object:
        {"action": "sys", "target": "open_app", "content": "calculator"}  <-- target is the specific action (battery, mute, volume, brightness, open_app), content is the value if needed (like "50" for 50%, or "calculator" for open_app).
        
        If the user wants to perform a WEB action (search, browse), output ONLY a JSON object:
        {"action": "web", "target": "search", "content": "query to search for"}  <-- target is 'search' or 'browse', content is the query or the url.
        
        If the user asks a question or makes small talk, output ONLY a JSON object:
        {"action": "speak", "content": "Your intelligent, polite, Jarvis-style response here."}"""}
    ]
    
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    messages.append({"role": "user", "content": text})
    
    try:
        response = litellm.completion(
            model=model_name,
            messages=messages
        )
        reply_content = response.choices[0].message.content
        
        clean_text = reply_content.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean_text)
        return parsed.get("action"), parsed.get("target"), parsed.get("content", "")
    except Exception as e:
        print(f"LiteLLM Error: {e}")
        return None, None, None

async def notify_clients(message_dict):
    if ws_clients:
        msg = json.dumps(message_dict)
        await asyncio.gather(*[client.send(msg) for client in ws_clients])

def run_zmq_loop(loop):
    context = zmq.Context()
    
    receiver = context.socket(zmq.PULL)
    receiver.bind("tcp://*:5556")
    
    doc_sender = context.socket(zmq.REQ)
    doc_sender.connect("tcp://localhost:5555")
    
    db_sender = context.socket(zmq.REQ)
    db_sender.connect("tcp://localhost:5557")
    
    sys_sender = context.socket(zmq.REQ)
    sys_sender.connect("tcp://localhost:5558")
    
    web_sender = context.socket(zmq.REQ)
    web_sender.connect("tcp://localhost:5559")
    
    print("Orchestrator Brain started on port 5556.")
    active_target = None

    while True:
        message = receiver.recv_string()
        try:
            data = json.loads(message)
            source_type = data.get("type")
            
            if source_type == "voice":
                text = data.get("text", "")
                
                asyncio.run_coroutine_threadsafe(
                    notify_clients({"type": "voice", "text": text}), loop
                )
                
                save_to_db(db_sender, "user", text)
                history = get_history_from_db(db_sender)
                
                api_key_present = any(key in os.environ for key in ["OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"]) and os.environ.get("GEMINI_API_KEY") != "your_actual_key_here"
                
                action, target, content = None, None, None
                if HAS_LITELLM and api_key_present:
                    action, target, content = ask_litellm(text, history)
                
                # Seamless fallback if LLM is unconfigured, has a placeholder key, or the LLM call fails
                if not action:
                    action, target, content = parse_voice_command(text)
                
                if action == "speak":
                    save_to_db(db_sender, "assistant", content)
                    asyncio.run_coroutine_threadsafe(
                        notify_clients({"type": "action", "text": content}), loop
                    )
                elif action == "question":
                    asyncio.run_coroutine_threadsafe(
                        notify_clients({"type": "status", "text": "Searching my databases, sir..."}), loop
                    )
                    try:
                        summary = wikipedia.summary(content, sentences=2)
                        save_to_db(db_sender, "assistant", summary)
                        asyncio.run_coroutine_threadsafe(
                            notify_clients({"type": "action", "text": summary}), loop
                        )
                    except Exception:
                        err_msg = "I am afraid I couldn't find any information on that."
                        save_to_db(db_sender, "assistant", err_msg)
                        asyncio.run_coroutine_threadsafe(
                            notify_clients({"type": "action", "text": err_msg}), loop
                        )
                elif action == "sys":
                    # System Command routing
                    cmd = {"action": target}
                    if content:
                        cmd["value"] = content
                    sys_sender.send_string(json.dumps(cmd))
                    reply = sys_sender.recv_string()
                    
                    if not api_key_present:
                        prefix = random.choice(ACK_RESPONSES)
                        reply = f"{prefix} {reply}"
                        
                    save_to_db(db_sender, "assistant", reply)
                    asyncio.run_coroutine_threadsafe(
                        notify_clients({"type": "action", "text": reply}), loop
                    )
                elif action == "web":
                    # Web Command routing
                    cmd = {"action": target}
                    if target == "browse":
                        cmd["url"] = content
                    elif target == "search":
                        cmd["query"] = content
                    web_sender.send_string(json.dumps(cmd))
                    reply = web_sender.recv_string()
                    
                    if not api_key_present:
                        prefix = random.choice(ACK_RESPONSES)
                        reply = f"{prefix} {reply}"
                        
                    save_to_db(db_sender, "assistant", reply)
                    asyncio.run_coroutine_threadsafe(
                        notify_clients({"type": "action", "text": reply}), loop
                    )
                else:
                    # Document Command
                    if target:
                        active_target = target
                        
                    if action and active_target:
                        cmd = {"action": action, "target": active_target, "content": content}
                        doc_sender.send_string(json.dumps(cmd))
                        reply = doc_sender.recv_string()
                        
                        if not api_key_present:
                            prefix = random.choice(ACK_RESPONSES)
                            reply = f"{prefix} {reply}"
                            
                        save_to_db(db_sender, "assistant", reply)
                        asyncio.run_coroutine_threadsafe(
                            notify_clients({"type": "action", "text": reply}), loop
                        )
                    else:
                        if not action and not api_key_present:
                            err_msg = random.choice([
                                "I'm sorry, sir, I didn't recognize that command.",
                                "I didn't quite catch that, sir. My basic systems only handle files and Wikipedia.",
                                "Sir, without my LLM API key, I am restricted to basic file management."
                            ])
                            save_to_db(db_sender, "assistant", err_msg)
                            asyncio.run_coroutine_threadsafe(
                                notify_clients({"type": "action", "text": err_msg}), loop
                            )
                        else:
                            asyncio.run_coroutine_threadsafe(
                                notify_clients({"type": "status", "text": f"Context: {active_target} | Awaiting command"}), loop
                            )
                        
            elif source_type == "gesture":
                gesture = data.get("value")
                asyncio.run_coroutine_threadsafe(
                    notify_clients({"type": "gesture", "text": gesture}), loop
                )
                
                if not active_target:
                    asyncio.run_coroutine_threadsafe(
                        notify_clients({"type": "status", "text": f"Warning: {gesture} gesture detected, but no document is active. Please use a voice command to select a document first."}), loop
                    )
                    continue
                    
                action = None
                if gesture == "Fist":
                    action = "close"
                elif gesture == "Open Hand":
                    action = "open"
                elif gesture == "Index Pointing":
                    action = "edit"
                    
                if action:
                    cmd = {"action": action, "target": active_target, "content": "Edited by gesture."}
                    doc_sender.send_string(json.dumps(cmd))
                    reply = doc_sender.recv_string()
                    
                    prefix = random.choice(ACK_RESPONSES)
                    save_to_db(db_sender, "assistant", f"{prefix} {reply}")
                    asyncio.run_coroutine_threadsafe(
                        notify_clients({"type": "action", "text": f"{prefix} {reply}"}), loop
                    )
                    
            elif source_type == "status":
                status_text = data.get("text", "")
                asyncio.run_coroutine_threadsafe(
                    notify_clients({"type": "status", "text": status_text}), loop
                )

        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"Error in orchestrator ZMQ loop: {e}")

async def main():
    server = await websockets.serve(ws_handler, "localhost", 8765)
    print("WebSocket Server started on ws://localhost:8765")
    
    loop = asyncio.get_running_loop()
    threading.Thread(target=run_zmq_loop, args=(loop,), daemon=True).start()
    
    await asyncio.Future()

async def ws_handler(websocket):
    ws_clients.add(websocket)
    try:
        await websocket.send(json.dumps({"type": "status", "text": "Jarvis Online"}))
        async for message in websocket:
            try:
                data = json.loads(message)
                if data.get("type") == "web_command":
                    # Inject web commands into the ZMQ pipeline
                    ctx = zmq.Context.instance()
                    sender = ctx.socket(zmq.PUSH)
                    sender.connect("tcp://localhost:5556")
                    sender.send_string(json.dumps({"type": "voice", "text": data.get("text").lower()}))
                    sender.close()
            except Exception as e:
                print(f"WS Parse Error: {e}")
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        ws_clients.remove(websocket)

if __name__ == "__main__":
    asyncio.run(main())
