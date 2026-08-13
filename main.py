import time  
import os  
import requests  
from threading import Thread  
from flask import Flask  
  
# --- Configurazione Server per Render ---  
app = Flask(__name__)  
  
@app.route('/')  
def home():  
 return "Gold Scalper Bot is running!", 200  
  
def run_web():  
 port = int(os.environ.get("PORT", 10000))  
 app.run(host="0.0.0.0", port=port)  
  
# --- Configurazione Telegram ---  
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")  
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")  
def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Errore: Token o Chat ID Telegram non configurati!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Errore nell'invio del messaggio Telegram: {e}")  
# --- LOGICA ALGORITMICA DI TRADING (Liquidity Sweep) ---  
def analizza_mercato():  
    """
    Logica di controllo per il Liquidity Sweep su XAU/USD.
    Inserisci qui i parametri dei minimi/massimi o la chiamata dati.
    """
    # Esempio di struttura segnale basata sui tuoi screenshot
    setup_valido = False # Da impostare in base alla tua condizione di sweep
      
    if setup_valido:  
        return {  
            "asset": "XAU/USD",
            "tipo": "LONG (Sweep Liquidità Minimi)",
            "entry": 4385.14,  
            "tp": 4390.23,  
            "sl": 4381.75  
        }  
    return None  
  
def trading_strategy():  
    print("Analisi Gold Scalper Bot (1M/5M Liquidity Sweep) in corso...")  
      
    segnale = analizza_mercato()  
      
    if segnale:  
        message = (  
            f"⚡ **SCALPER BOT 1M - SEGNALE BUY** ⚡\n\n"  
            f"🌐 Strumento: {segnale['asset']}\n"  
            f"📊 Tipo: {segnale['tipo']}\n"  
            f"💵 Prezzo Entrata: {segnale['entry']}\n"  
            f"🛑 Stop Loss: {segnale['sl']}\n"  
            f"🎯 Take Profit: {segnale['tp']}\n"  
            f"Condizioni di liquidity sweep soddisfatte!"  
        )  
        send_telegram_message(message)  
  
# --- AVVIO BOT ---  
if __name__ == "__main__":  
    t = Thread(target=run_web)  
    t.daemon = True  
    t.start()  
      
    print("Gold Scalper Bot avviato in modalità autonoma.")  
      
    while True:  
        try:  
            trading_strategy()  
        except Exception as e:  
            print(f"Errore nel ciclo: {e}")  
          
        # Pausa tra i controlli (es. ogni 60 secondi per il timeframe a 1 minuto)  
        time.sleep(60)
