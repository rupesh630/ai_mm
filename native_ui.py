import customtkinter as ctk
import asyncio
import websockets
import json
import threading
import comtypes.client

# Use modern dark mode theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class JarvisNativeUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("J.A.R.V.I.S. Command Center")
        self.geometry("900x700")
        self.minsize(600, 500)
        
        # WebSocket Reference
        self.ws = None
        self.loop = None
        
        # Configure Grid Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Main Frame
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # Header (Status + Orb)
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, pady=(0, 20), sticky="ew")
        
        self.status_label = ctk.CTkLabel(self.header_frame, text="🔴 Offline", font=ctk.CTkFont(size=18, weight="bold"), text_color="#ff5555")
        self.status_label.pack(pady=10)
        
        # The Action Log (Textbox)
        self.log_box = ctk.CTkTextbox(self.main_frame, state="disabled", font=ctk.CTkFont(size=14))
        self.log_box.grid(row=1, column=0, sticky="nsew")
        self.log_box.tag_config("user", foreground="#00e5ff")
        self.log_box.tag_config("jarvis", foreground="#00ffaa")
        self.log_box.tag_config("system", foreground="#aaaaaa")
        
        # Command Input Area
        self.input_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.input_frame.grid(row=2, column=0, pady=(20, 0), sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        self.cmd_input = ctk.CTkEntry(self.input_frame, placeholder_text="Type a command to Jarvis...", height=40, font=ctk.CTkFont(size=14))
        self.cmd_input.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.cmd_input.bind("<Return>", lambda event: self.send_command())
        
        self.send_btn = ctk.CTkButton(self.input_frame, text="SEND", height=40, width=100, font=ctk.CTkFont(weight="bold"), command=self.send_command)
        self.send_btn.grid(row=0, column=1)

        self.add_log("System initialized. Connecting to Orchestrator...", "system")

        # Start the WebSocket client in a background thread
        self.ws_thread = threading.Thread(target=self.start_asyncio_loop, daemon=True)
        self.ws_thread.start()

    def add_log(self, text, tag="system"):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n", tag)
        self.log_box.configure(state="disabled")
        self.log_box.see("end")

    def update_status(self, text, color):
        self.status_label.configure(text=text, text_color=color)

    def send_command(self):
        text = self.cmd_input.get().strip()
        if text and self.ws and self.loop:
            self.add_log(f"You: {text}", "user")
            self.cmd_input.delete(0, "end")
            
            # Send message safely from UI thread to Asyncio thread
            payload = json.dumps({"type": "web_command", "text": text})
            asyncio.run_coroutine_threadsafe(self.ws.send(payload), self.loop)
        elif not self.ws:
            self.add_log("Error: Disconnected from backend.", "system")

    def start_asyncio_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.connect_ws())

    def speak(self, text):
        def _speak():
            try:
                speaker = comtypes.client.CreateObject("SAPI.SpVoice")
                speaker.Speak(text)
            except Exception as e:
                print(f"Speech synthesis error: {e}")
        threading.Thread(target=_speak, daemon=True).start()

    async def connect_ws(self):
        uri = "ws://localhost:8765"
        while True:
            try:
                async with websockets.connect(uri) as websocket:
                    self.ws = websocket
                    self.update_status("🟢 Jarvis Online", "#00ffaa")
                    self.add_log("Connected to Orchestrator.", "system")
                    
                    # Speak when successfully connected
                    self.speak("Jarvis Online")
                    
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            msg_type = data.get("type")
                            text = data.get("text", "")
                            
                            if msg_type in ["status", "action", "voice"]:
                                self.add_log(f"Jarvis: {text}", "jarvis")
                                
                                # Voice synthesis matching Web UI behavior
                                if msg_type == "action":
                                    self.speak(text)
                                elif msg_type == "status":
                                    if any(phrase in text for phrase in ["Jarvis Online", "Didn't catch that", "Warning", "Yes, sir?"]):
                                        self.speak(text)
                        except Exception as e:
                            print(f"JSON Parse Error: {e}")
                            
            except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError):
                self.ws = None
                self.update_status("🔴 Disconnected", "#ff5555")
                # Wait before reconnecting
                await asyncio.sleep(3)

if __name__ == "__main__":
    app = JarvisNativeUI()
    app.mainloop()
