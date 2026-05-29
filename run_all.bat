@echo off
echo Starting Jarvis Multi-Agent System...
echo Note: Ensure your virtual environment is active and dependencies are installed.

start cmd /k ".\venv\Scripts\activate.bat && echo Starting Document Agent... && python doc_agent.py"
start cmd /k ".\venv\Scripts\activate.bat && echo Starting Voice Agent... && python voice_agent.py"
start cmd /k ".\venv\Scripts\activate.bat && echo Starting Gesture Agent... && python gesture_agent.py"
start cmd /k ".\venv\Scripts\activate.bat && echo Starting Database Agent... && python db_agent.py"
start cmd /k ".\venv\Scripts\activate.bat && echo Starting System Agent... && python sys_agent.py"
start cmd /k ".\venv\Scripts\activate.bat && echo Starting Web Agent... && python web_agent.py"
start cmd /k ".\venv\Scripts\activate.bat && echo Starting Orchestrator... && python orchestrator.py"

echo Waiting for backend to spin up...
timeout /t 3 /nobreak > NUL

echo Launching Jarvis Native UI...
start "" ".\venv\Scripts\python.exe" "native_ui.py"

echo All agents started!
