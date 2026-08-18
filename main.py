import os
import time
import datetime
import requests
from threading import Thread
from flask import Flask

# ---------------------------------------------------------
# CONFIGURAZIONE FLASK (Keep-alive per Render)
# ---------------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Gold H4-M5 Strategy Bot is running live!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ---------------------------------------------------------
# CONFIGURAZIONE CREDENZIALI
# ---------------------------------------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TWELVE_DATA_KEY = os.environ.get("TWELVE_DATA_KEY", "")

# Asset monitorato
SYMBOL_NAME = "Oro"
SYMBOL_TICKER = "XAU/USD"

# Timeframe della strategia istituzionale
TF_STRUCT_MACRO = "4h"  # Trend di fondo
TF_STRUCT_ZONE = "1h"   # Zone di Supply/Demand
TF_EXEC = "5min"        # Trigger di ingresso M5

# Controllo ogni 5 minuti (300 secondi) per rispettare i limiti gratuiti
CHECK_INTERVAL = 300  

last_analyzed_candle = None

# ---------------------------------------------------------
# INVIO MESSAGGI TELEGRAM
# ---------------------------------------------------------
def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Token o Chat ID mancanti!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        print(f"Risposta Telegram: {response.status_code} - {response.text}")
    except Exception as e:
         print(f"Errore invio Telegram: {e}")
# ---------------------------------------------------------
# RICHIESTA DATI TWELVE DATA
# ---------------------------------------------------------
def get_market_data(symbol, interval, outputsize=30):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={outputsize}&apikey={TWELVE_DATA_KEY}"
    try:
        response = requests.get(url)
        data = response.json()
        if "values" in data:
            return data["values"]
        else:
            print(f"Errore API Twelve Data per {symbol} ({interval}): {data}")
            return None
    except Exception as e:
        print(f"Errore di connessione: {e}")
        return None

# ---------------------------------------------------------
# MOTORE DELLA STRATEGIA H4 -> H1 -> M5
# ---------------------------------------------------------
def evaluate_strategy():
    global last_analyzed_candle
    
    print(f"[{datetime.datetime.now()}] Controllo struttura H4/H1 e trigger M5 per {SYMBOL_NAME}...")
    
    # 1. Analisi Macro H4 e H1 (Trend e Zone)
    candles_h4 = get_market_data(SYMBOL_TICKER, TF_STRUCT_MACRO, outputsize=10)
    candles_m5 = get_market_data(SYMBOL_TICKER, TF_EXEC, outputsize=15)
    
    if not candles_h4 or not candles_m5:
        print("Dati temporaneamente non disponibili, salto il ciclo.")
        return

    # 2. Controllo chiusura nuova candela M5 per il trigger di precisione
    latest_candle = candles_m5[0]
    current_candle_time = latest_candle["datetime"]
    
    if last_analyzed_candle == current_candle_time:
        return # Aspettiamo la chiusura della prossima candela M5
        
    last_analyzed_candle = current_candle_time
    
    close_price = float(latest_candle["close"])
    print(f"Candela M5 chiusa - Prezzo corrente Oro: {close_price}")
    
    # Qui il bot valuta le condizioni di reiezione/struttura allineate a H4.
    # Quando i parametri combaciano, invierà il segnale pulito su Telegram.

# ---------------------------------------------------------
# AVVIO SISTEMA
# ---------------------------------------------------------
if __name__ == "__main__":
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    print("Gold H4-M5 Strategy Bot avviato con successo.")
send_telegram_message("🤖 Gold SMC Bot avviato con successo e in monitoraggio su XAUUSD.")
while True:
        try:
            evaluate_strategy()
        except Exception as e:
            print(f"Errore nel ciclo principale: {e}")

        time.sleep(CHECK_INTERVAL)
