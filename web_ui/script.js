const statusDot = document.querySelector('.dot');
const statusText = document.getElementById('status-text');
const voiceText = document.getElementById('voice-text');
const actionLog = document.getElementById('action-log');
const orb = document.getElementById('jarvis-orb');
const enableAudioBtn = document.getElementById('enable-audio-btn');

let audioEnabled = false;

// Explicit button to enable browser audio autoplay policies
enableAudioBtn.addEventListener('click', () => {
    if (!audioEnabled) {
        audioEnabled = true;
        speak("Audio systems initialized.");
        addLogEntry("System audio enabled.");
        enableAudioBtn.style.display = 'none'; // Hide after enabling
    }
});

// Add log entry helper
function addLogEntry(message) {
    const li = document.createElement('li');
    li.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    actionLog.appendChild(li);
    actionLog.scrollTop = actionLog.scrollHeight;
}

// Speech Synthesis Helper
function speak(text) {
    if (!audioEnabled) return; // Browser will block if user hasn't clicked
    
    // Stop any ongoing speech to prioritize new one
    window.speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    
    // Try to find a male English voice (e.g. Microsoft Mark or Google UK English Male)
    const voices = window.speechSynthesis.getVoices();
    let preferredVoice = voices.find(v => v.lang.includes('en') && (v.name.includes('Male') || v.name.includes('Mark')));
    if (preferredVoice) {
        utterance.voice = preferredVoice;
    }
    
    utterance.rate = 1.1; // Slightly faster
    utterance.pitch = 0.8; // Deeper pitch
    
    window.speechSynthesis.speak(utterance);
}

// Setup WebSocket
let ws = null;

function connect() {
    ws = new WebSocket('ws://localhost:8765');

    ws.onopen = () => {
        statusDot.className = 'dot connected';
        statusText.textContent = 'Connected to Core';
        addLogEntry('Connection to Orchestrator established. Click ENABLE AUDIO to allow Jarvis to speak.');
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            
            // Pulse the orb on any activity
            orb.classList.add('active');
            setTimeout(() => orb.classList.remove('active'), 500);

            if (data.type === 'voice') {
                orb.classList.remove('listening');
                voiceText.textContent = `"${data.text}"`;
            } else if (data.type === 'action') {
                orb.classList.remove('listening');
                addLogEntry(`Executed: ${data.text}`);
                // Jarvis speaks the result!
                speak(data.text);
            } else if (data.type === 'status') {
                addLogEntry(`Status: ${data.text}`);
                if (data.text.includes("listening")) {
                    orb.classList.add('listening');
                } else {
                    orb.classList.remove('listening');
                }
                // Only speak certain high-level status messages
                if (data.text.includes("Jarvis Online") || data.text.includes("Didn't catch that") || data.text.includes("Warning") || data.text.includes("Yes, sir?")) {
                    speak(data.text);
                }
            } else if (data.type === 'gesture') {
                addLogEntry(`Gesture Detected: ${data.text}`);
            }
        } catch (e) {
            console.error('Failed to parse message', e);
        }
    };

    ws.onclose = () => {
        statusDot.className = 'dot disconnected';
        statusText.textContent = 'Disconnected';
        
        // Prevent log spam if it's already disconnected
        if (actionLog.lastElementChild && !actionLog.lastElementChild.textContent.includes('Connection lost')) {
            addLogEntry('Connection lost. Reconnecting...');
        }
        setTimeout(connect, 3000);
    };

    ws.onerror = (err) => {
        console.error('WebSocket Error', err);
    };
}

// UI Command Input Logic
const commandInput = document.getElementById('command-input');
const sendBtn = document.getElementById('send-btn');

function sendCommand() {
    const text = commandInput.value.trim();
    if (text && ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'web_command', text: text }));
        addLogEntry(`You typed: ${text}`);
        commandInput.value = '';
        
        // Pulse orb to show it's processing
        orb.classList.add('listening');
    } else if (!ws || ws.readyState !== WebSocket.OPEN) {
        addLogEntry("Cannot send command: Disconnected from backend.");
    }
}

sendBtn.addEventListener('click', sendCommand);
commandInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendCommand();
});

// Load voices asynchronously then start connection
window.speechSynthesis.onvoiceschanged = () => {};
connect();
