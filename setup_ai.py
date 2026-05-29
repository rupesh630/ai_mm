import os

def main():
    print("="*60)
    print("      J.A.R.V.I.S. TRUE AI BRAIN INITIALIZATION")
    print("="*60)
    print("\nTo unlock natural language understanding and dynamic conversational")
    print("memory, Jarvis requires a Large Language Model API Key.\n")
    print("We recommend the Google Gemini API (it is incredibly fast and FREE).")
    print("Get your free key here: https://aistudio.google.com/app/apikey\n")
    
    key = input("Please paste your GEMINI_API_KEY (or press Enter to skip): ").strip()
    
    if key:
        with open(".env", "w") as f:
            f.write(f"GEMINI_API_KEY={key}\n")
            f.write("JARVIS_MODEL=gemini/gemini-1.5-flash\n")
        print("\n[SUCCESS] API Key saved to .env!")
        print("Jarvis is now running with a fully unlocked LLM Brain.")
        print("Please restart the background processes using run_all.bat to apply the upgrade.")
    else:
        print("\n[SKIPPED] No key provided. Jarvis will continue to use the rigid Fallback Parser.")
        
if __name__ == "__main__":
    main()
