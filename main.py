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
    return "Gold Scalper Bot (1M/3M Liquidity Sweep) is running live!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ---------------------------------------------------------
# CONFIGURAZIONE BOT TELEGRAM E TWELVE DATA
# ---------------------------------------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "TUO_TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "TUO_CHAT_ID")
TWELVE_DATA_KEY = os.environ.get("TWELVE_DATA_KEY", "fa500c91581d4b4685dd1040f541ac8e")

SYMBOL = "XAU/USD"
TIMEFRAME = "1min"      # Timeframe 1 Minuto per Scalping
LOOKBACK = 12          # Candele per identificare il range recente
CHECK_INTERVAL = 60    # Controllo ogni 60 secondi

last_signal_time = None

# ---------------------------------------------------------
# FUNZIONI DI SUPPORTO
# ---------------------------------------------------------
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Errore invio Telegram: {e}")

def get_market_data():
    """Recupera le candele da Twelve Data"""
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={TIMEFRAME}&outputsize=30&apikey={TWELVE_DATA_KEY}"
    try:
        res = requests.get(url, timeout=10).json()
        if "values" in res:
            data = res["values"]
            data.reverse()  # Ordine cronologico
            return data
    except Exception as e:
        print(f"Errore Twelve Data: {e}")
    return None

# ---------------------------------------------------------
# LOGICA DI TRADING: LIQUIDITY SWEEP & REJECTION
# ---------------------------------------------------------
def analyze_scalp():
    global last_signal_time

    candles = get_market_data()
    if not candles or len(candles) < LOOKBACK + 2:
        return

    # Ultima candela chiusa (index -2)
    last_candle = candles[-2]
    # Candele precedenti per identificare High e Low
    past_candles = candles[-(LOOKBACK+2):-2]

    open_p = float(last_candle['open'])
    high_p = float(last_candle['high'])
    low_p = float(last_candle['low'])
    close_p = float(last_candle['close'])
    time_str = last_candle['datetime']

    # Evita segnali duplicati sulla stessa candela
    if last_signal_time == time_str:
        return

    # Trova il massimo e minimo del range precedente
    past_highs = [float(c['high']) for c in past_candles]
    past_lows = [float(c['low']) for c in past_candles]
    
    recent_high = max(past_highs)
    recent_low = min(past_lows)

    range_size = high_p - low_p
    if range_size == 0:
        return

    # Calcolo dell'ombra (Wick)
    upper_wick = high_p - max(open_p, close_p)
    lower_wick = min(open_p, close_p) - low_p

    # --- CONDIZIONI LONG (SWEEP LOW + WICK RIALZISTA) ---
    is_low_sweep = low_p < recent_low
    is_bullish_rejection = (lower_wick / range_size) > 0.45 and close_p > low_p

    if is_low_sweep and is_bullish_rejection:
        last_signal_time = time_str
        sl = round(low_p - 0.80, 2)            # Stop Loss stretto ($0.80)
        tp = round(close_p + (close_p - sl) * 1.5, 2) # Risk/Reward 1:1.5

        msg = (
            f"⚡ **SCALPER BOT 1M - SEGNALE BUY** ⚡\n\n"
            f"🪙 **Strumento:** {SYMBOL}\n"
            f"📊 **Tipo:** LONG (Sweep Liquidità Minimi)\n"
            f"💵 **Prezzo Entrata:** `{close_p}`\n"
            f"🛑 **Stop Loss:** `{sl}`\n"
            f"🎯 **Take Profit:** `{tp}`\n"
            f"⏰ **Orario:** {time_str}"
        )
        send_telegram_message(msg)
        print(f"[{datetime.datetime.now()}] BUY Scalp inviato!")
        return

    # --- CONDIZIONI SHORT (SWEEP HIGH + WICK RIBASSISTA) ---
    is_high_sweep = high_p > recent_high
    is_bearish_rejection = (upper_wick / range_size) > 0.45 and close_p < high_p

    if is_high_sweep and is_bearish_rejection:
        last_signal_time = time_str
        sl = round(high_p + 0.80, 2)            # Stop Loss stretto ($0.80)
        tp = round(close_p - (sl - close_p) * 1.5, 2) # Risk/Reward 1:1.5

        msg = (
            f"⚡ **SCALPER BOT 1M - SEGNALE SELL** ⚡\n\n"
            f"🪙 **Strumento:** {SYMBOL}\n"
            f"📊 **Tipo:** SHORT (Sweep Liquidità Massimi)\n"
            f"💵 **Prezzo Entrata:** `{close_p}`\n"
            f"🛑 **Stop Loss:** `{sl}`\n"
            f"🎯 **Take Profit:** `{tp}`\n"
            f"⏰ **Orario:** {time_str}"
        )
        send_telegram_message(msg)
        print(f"[{datetime.datetime.now()}] SELL Scalp inviato!")
        return

# ---------------------------------------------------------
# LOOP PRINCIPALE
# ---------------------------------------------------------
def main_loop():
    print("🚀 Gold Scalper Bot (1M) Avviato!")
    send_telegram_message("⚡ **Gold Scalper Bot (1M Liquidity Sweep) Avviato e Attivo!** 🚀")
    
    while True:
        try:
            analyze_scalp()
        except Exception as e:
            print(f"Errore nel loop: {e}")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

    main_loop()
