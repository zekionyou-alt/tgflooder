from flask import Flask
import threading
import os
import subprocess

app = Flask(__name__)

@app.route('/')
def hello():
    return "Telegram Flood Bot is running 24/7!"

def run_flood():
    # Run the actual script
    subprocess.run(["python", "tg_flood_cloud.py"])

if __name__ == "__main__":
    # Start the flood script in a background thread
    thread = threading.Thread(target=run_flood)
    thread.daemon = True
    thread.start()
    
    # Keep the web server running
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
