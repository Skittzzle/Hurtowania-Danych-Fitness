import os
import subprocess
import sys

def main():
    print("🚀 Uruchamianie Fitness Data Warehouse Dashboard...")
    
    # Sprawdzenie czy streamlit jest zainstalowany
    try:
        import streamlit
    except ImportError:
        print("❌ Streamlit nie jest zainstalowany. Uruchom: pip install -r backend/requirements.txt")
        sys.exit(1)

    # Uruchomienie aplikacji
    try:
        subprocess.run(["streamlit", "run", "app.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Zamykanie aplikacji...")
    except Exception as e:
        print(f"❌ Wystąpił błąd: {e}")

if __name__ == "__main__":
    main()
