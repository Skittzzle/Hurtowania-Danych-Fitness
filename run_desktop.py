import os
import subprocess
import time
import webview
import threading
import sys

def run_streamlit():
    """Runs the streamlit server."""
    subprocess.run(["streamlit", "run", "app.py", "--server.headless", "true", "--server.port", "8501"])

def main():
    print("🚀 Uruchamianie Fitness Data Warehouse w trybie Desktop...")
    
    # Start streamlit in a separate thread
    thread = threading.Thread(target=run_streamlit, daemon=True)
    thread.start()
    
    # Wait for the server to start (simple delay)
    time.sleep(5)
    
    # Create a webview window
    try:
        webview.create_window('Fitness Data Warehouse - Desktop GUI', 'http://localhost:8501', 
                             width=1200, height=800, resizable=True)
        webview.start()
    except Exception as e:
        print(f"❌ Błąd podczas uruchamiania okna GUI: {e}")
        print("💡 Upewnij się, że masz zainstalowaną bibliotekę pywebview: pip install pywebview")
        sys.exit(1)

if __name__ == "__main__":
    main()
