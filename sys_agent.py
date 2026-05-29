import zmq
import json
import psutil
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    import screen_brightness_control as sbc
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

def get_volume_interface():
    if not HAS_LIBS: return None
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))

def process_command(cmd):
    action = cmd.get("action")
    
    if action == "volume":
        if not HAS_LIBS: return "Volume control dependencies are missing."
        value = cmd.get("value")
        if value is None: return "Volume value not provided."
        try:
            val = max(0, min(100, int(value)))
            volume = get_volume_interface()
            # Pycaw SetMasterVolumeLevelScalar takes a float between 0.0 and 1.0
            volume.SetMasterVolumeLevelScalar(val / 100.0, None)
            return f"System volume set to {val}%."
        except Exception as e:
            return f"Error setting volume: {e}"
            
    elif action == "mute":
        if not HAS_LIBS: return "Volume control dependencies are missing."
        try:
            volume = get_volume_interface()
            volume.SetMute(1, None)
            return "System audio muted."
        except Exception as e:
            return f"Error muting: {e}"
            
    elif action == "unmute":
        if not HAS_LIBS: return "Volume control dependencies are missing."
        try:
            volume = get_volume_interface()
            volume.SetMute(0, None)
            return "System audio unmuted."
        except Exception as e:
            return f"Error unmuting: {e}"

    elif action == "open_app":
        app_name = cmd.get("value")
        if not app_name: return "App name not provided."
        try:
            from AppOpener import open as app_open
            # match_closest allows for fuzzy matching (e.g. 'whatsapp' instead of 'WhatsApp Desktop')
            app_open(app_name, match_closest=True)
            return f"Opening {app_name}."
        except Exception:
            try:
                import subprocess
                # Fallback to standard start command if AppOpener fails
                subprocess.Popen(f"start {app_name}", shell=True)
                return f"Opening {app_name}."
            except Exception as e:
                return f"Error opening application: {e}"

    elif action == "brightness":
        if not HAS_LIBS: return "Brightness control dependencies are missing."
        value = cmd.get("value")
        if value is None: return "Brightness value not provided."
        try:
            val = max(0, min(100, int(value)))
            sbc.set_brightness(val)
            return f"Screen brightness set to {val}%."
        except Exception as e:
            return f"Error setting brightness: {e}"
            
    elif action == "battery":
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                return "Battery information is not available on this system."
            percent = battery.percent
            plugged = "plugged in" if battery.power_plugged else "on battery power"
            return f"The system is at {percent}% battery and is currently {plugged}."
        except Exception as e:
            return f"Error getting battery status: {e}"

    return "Unknown system command."

def run_agent():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5558")

    print("System Agent started. Listening on port 5558...")

    while True:
        message = socket.recv_string()
        try:
            cmd = json.loads(message)
            response = process_command(cmd)
        except json.JSONDecodeError:
            response = "Error: Message is not valid JSON."
        except Exception as e:
            response = f"System Agent Error: {str(e)}"
            
        socket.send_string(response)

if __name__ == "__main__":
    run_agent()
