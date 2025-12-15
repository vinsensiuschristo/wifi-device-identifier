"""
Run Flask with Ngrok tunnel for public access
"""
from pyngrok import ngrok
import threading
import time

# Set auth token (already saved in config, but just in case)
ngrok.set_auth_token("36p8miLkeB4zEKX6rOpFzcaNSMK_88gmM5hLd32DdaL6be75x")

# Import Flask app
from main import create_app
import config

# Create Flask app
app = create_app()

def run_flask():
    """Run Flask in a separate thread"""
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# Start Flask in background thread
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

# Wait for Flask to start
time.sleep(2)

# Start ngrok tunnel
print("\n[*] Starting ngrok tunnel...")
public_url = ngrok.connect(5000, "http")

print("\n" + "="*60)
print("🌐 WiFi Device Identifier - PUBLIC ACCESS via Ngrok")
print("="*60)
print(f"📱 PUBLIC URL:    {public_url}")
print(f"📍 Local URL:     http://localhost:5000")
print("="*60)
print(f"\n👉 Buka URL ini dari HP Anda:")
print(f"   {public_url}/login")
print(f"\n📊 Dashboard:")
print(f"   {public_url}/dashboard")
print("="*60)
print("\nTekan Ctrl+C untuk berhenti...")

# Keep running
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n[*] Stopping...")
    ngrok.disconnect(public_url)
    ngrok.kill()
