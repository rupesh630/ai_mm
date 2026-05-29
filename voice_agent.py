import speech_recognition as sr
import zmq
import json
import time

def run_agent():
    context = zmq.Context()
    socket = context.socket(zmq.PUSH)
    socket.connect("tcp://localhost:5556")
    
    def send_status(text):
        socket.send_string(json.dumps({"type": "status", "text": text}))
        
    def send_voice(text):
        socket.send_string(json.dumps({"type": "voice", "text": text.lower()}))

    r = sr.Recognizer()
    m = sr.Microphone()

    print("Voice Agent started. Adjusting for ambient noise...")
    with m as source:
        r.adjust_for_ambient_noise(source)
    print("Ready to listen. Speak into the microphone.")
    send_status("Microphone ready. Say something...")

    while True:
        with m as source:
            print("Listening...")
            send_status("Listening...")
            try:
                # Add a timeout so it doesn't hang forever waiting for speech
                audio = r.listen(source, timeout=3, phrase_time_limit=10)
            except sr.WaitTimeoutError:
                # Timed out waiting for someone to speak. Just loop back.
                continue
            
        try:
            # Use OpenAI Whisper locally instead of the cloud!
            text = r.recognize_whisper(audio, model="base.en").lower()
            
            # Whisper sometimes includes punctuation or hallucinated artifacts like '[Silence]' or '.' 
            import re
            text = re.sub(r'\[.*?\]|\(.*?\)|\*.*?\*', '', text) # Remove bracketed text
            text = text.strip()
            
            if text:
                print(f"Heard: {text}")
            
            if "jarvis" in text:
                send_status("Jarvis is listening...")
                clean_text = text.replace("jarvis", "").strip()
                if clean_text:
                    print(f"Command: {clean_text}")
                    send_voice(clean_text)
                else:
                    send_status("Yes, sir? Awaiting command.")
            else:
                # Ignore background chatter that doesn't contain the wake word
                pass
                
        except sr.UnknownValueError:
            pass # Ignore random noise
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
            send_status(f"Network error: {e}")
        except Exception as e:
            err_str = str(e).lower()
            if "ffmpeg" in err_str or "winerror 2" in err_str:
                print("CRITICAL: ffmpeg is missing. Whisper requires ffmpeg to process audio.")
                send_status("Error: FFMPEG is not installed on this PC.")
            else:
                print(f"Whisper Error: {e}")
            
        time.sleep(0.1)

if __name__ == "__main__":
    run_agent()
