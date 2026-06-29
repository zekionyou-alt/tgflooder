from flask import Flask
import threading
import os
import subprocess
import sys

app = Flask(__name__)

@app.route('/')
def hello():
    return "Telegram Flood Bot is running 24/7 on Render!"

@app.route('/health')
def health():
    return "OK", 200

def run_flood():
    # Run the actual flood script
    try:
        subprocess.run([sys.executable, "tg_flood.py"], check=False)
    except Exception as e:
        print(f"Flood script error: {e}")

if __name__ == "__main__":
    # Start the flood script in a background thread
    thread = threading.Thread(target=run_flood, daemon=True)
    thread.start()
    print("✅ Flood script started in background thread.")
    print("🌐 Web server starting on port", os.environ.get('PORT', 10000))
    
    # Keep the web server running (this is what Render sees)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
