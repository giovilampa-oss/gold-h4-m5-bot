import time
import requests
import os
from threading import Thread
from flask import Flask

# --- MINI-SERVER PER MANTENERE APERTA LA PORTA SU RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Gold Scalper Bot is running!", 200

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
# -----------------------------------------------------------

# Configurazioni Telegram (prelevate in automatico da Render)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Token o Chat ID Telegram non configurati!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"Errore nell'invio del messaggio Telegram: {e}")

def gold_scalper_strategy():
    print("Analisi Gold Scalper (Breakout/Sweep) in corso...")
    
    # --- LOGICA DI SCALPING XAUUSD ---
    # Qui inserisci i controlli sui prezzi di mercato in tempo reale.
    # Quando la tua condizione di scalping si verifica, imposta setup_trovato = True
    setup_trovato = False 
    
    if setup_trovato:
        entry_price = 4391.00  # Esempio di prezzo
        stop_loss = 4386.50
        tp1 = 4398.00
        tp2 = 4405.00
        
        messaggio = (
            f"⚡ *GOLD SCALPER SIGNAL* ⚡\n\n"
            f"🪙 *Asset:* XAUUSD\n"
            f"📍 *Entrata:* {entry_price}\n"
            f"🛑 *Stop Loss:* {stop_loss}\n"
            f"🎯 *Take Profit 1:* {tp1}\n"
            f"🎯 *Take Profit 2:* {tp2}"
        )
        send_telegram_message(messaggio)

# Ciclo continuo 24/7 in background
if __name__ == "__main__":
    # Avvia il mini-server Flask in un thread separato per tenere aperta la porta
    t = Thread(target=run_web)
    t.daemon = True
    t.start()
    
    print("Gold Scalper Bot avviato in modalità autonoma con supporto Web.")
    
    while True:
        try:
            gold_scalper_strategy()
        except Exception as e:
            print(f"Errore nel ciclo di scalping: {e}")
        
        # Intervallo di controllo (es. ogni 60 secondi)
        time.sleep(60)
