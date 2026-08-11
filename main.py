import os
import time
import datetime
import pytz
import requests
from threading import Thread
from flask import Flask

# --------------------------------------------------
# CONFIGURAZIONE FLASK (Keep-alive per Render)
# --------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Gold Scalper Bot (5M Liquidity Sweep + EMA Filter) is running live!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --------------------------------------------------
# CONFIGURAZIONE BOT TELEGRAM E TWELVE DATA
# --------------------------------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "TUO_TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "TUO_CHAT_ID")
TWELVE_DATA_KEY = os.environ.get("TWELVE_DATA_KEY", "fa500c91581d4b4685dd1040f541ac8e")

SYMBOL = "XAU/USD"
TIMEFRAME = "5min"          # Timeframe 5 Minuti
LOOKBACK = 12               # Candele per identificare il range recente
CHECK_INTERVAL = 60         # Controllo ogni 60 secondi

last_signal_time = None

# --------------------------------------------------
# FUNZIONI DI SUPPORTO
# --------------------------------------------------
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
    """Recupera le candele, l'ATR e la EMA 200 da Twelve Data"""
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={TIMEFRAME}&outputsize=250&apikey={TWELVE_DATA_KEY}&indicators=atr(timeperiod=14),ema(timeperiod=200)"
    try:
        res = requests.get(url, timeout=10).json()
        if "values" in res:
            data = res["values"]
            data.reverse()  # Ordine cronologico
            return data
    except Exception as e:
        print(f"Errore Twelve Data: {e}")
    return None

# --------------------------------------------------
# LOGICA DI TRADING: LIQUIDITY SWEEP & EMA FILTER
# --------------------------------------------------
def analyze_scalp():
    global last_signal_time

    candles = get_market_data()
    if not candles or len(candles) < LOOKBACK + 2:
        return

    # Ultima candela chiusa (index -2)
    last_candle = candles[-2]
    # Candele precedenti per identificare High e Low
    prev_candles = candles[-(LOOKBACK + 2):-2]

    time_str = last_candle['datetime']
    if last_signal_time == time_str:
        return # Evita segnali duplicati sulla stessa candela

    high_p = float(last_candle['high'])
    low_p = float(last_candle['low'])
    close_p = float(last_candle['close'])
    open_p = float(last_candle['open'])

    # Indicatore EMA 200 e ATR
    ema_200 = float(last_candle.get('ema', close_p))
    atr = float(last_candle.get('atr', 1.20))

    # Calcolo swing highs e lows recenti
    recent_high = max(float(c['high']) for c in prev_candles)
    recent_low = min(float(c['low']) for c in prev_candles)

    range_size = abs(high_p - low_p)
    if range_size == 0:
        return

    lower_wick = min(open_p, close_p) - low_p
    upper_wick = high_p - max(open_p, close_p)

    # Converti orario in fuso orario di Roma (Europe/Rome)
    try:
        dt_utc = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.utc)
        rome_tz = pytz.timezone("Europe/Rome")
        formatted_time = dt_utc.astimezone(rome_tz).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        formatted_time = time_str

    # --- CONDIZIONI LONG (SWEEP LOW + WICK RIALZISTA + SOPRA EMA 200) ---
    is_low_sweep = low_p < recent_low
    is_bullish_rejection = (lower_wick / range_size) > 0.45 and close_p > low_p

    if is_low_sweep and is_bullish_rejection and close_p > ema_200:
        last_signal_time = time_str
        
        sl = round(low_p - (1.5 * atr), 2)
        risk = round(close_p - sl, 2)
        tp = round(close_p + (risk * 2), 2)

        msg = (
            f"⚡ **SCALPER BOT 5M - SEGNALE BUY** ⚡\n\n"
            f"🌐 **Strumento:** {SYMBOL}\n"
            f"📊 **Tipo:** LONG (Sweep Liquidità Minimi)\n"
            f"💵 **Prezzo Entrata:** `{close_p}`\n"
            f"🛑 **Stop Loss:** `{sl}`\n"
            f"🎯 **Take Profit:** `{tp}`\n"
            f"⏰ **Orario:** {formatted_time}"
        )
        send_telegram_message(msg)
        print(f"[{datetime.datetime.now()}] BUY Scalp inviato!")
        return

    # --- CONDIZIONI SHORT (SWEEP HIGH + WICK RIBASSISTA + SOTTO EMA 200) ---
    is_high_sweep = high_p > recent_high
    is_bearish_rejection = (upper_wick / range_size) > 0.45 and close_p < high_p

    if is_high_sweep and is_bearish_rejection and close_p < ema_200:
        last_signal_time = time_str
        
        sl = round(high_p + (1.5 * atr), 2)
        risk = round(sl - close_p, 2)
        tp = round(close_p - (risk * 2), 2)

        msg = (
            f"⚡ **SCALPER BOT 5M - SEGNALE SELL** ⚡\n\n"
            f"🌐 **Strumento:** {SYMBOL}\n"
            f"📊 **Tipo:** SHORT (Sweep Liquidità Massimi)\n"
            f"💵 **Prezzo Entrata:** `{close_p}`\n"
            f"🛑 **Stop Loss:** `{sl}`\n"
            f"🎯 **Take Profit:** `{tp}`\n"
            f"⏰ **Orario:** {formatted_time}"
        )
        send_telegram_message(msg)
        print(f"[{datetime.datetime.now()}] SELL Scalp inviato!")
        return

# --------------------------------------------------
# MAIN LOOP
# --------------------------------------------------
if __name__ == '__main__':
    # Avvia Flask in un thread separato
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

    send_telegram_message("⚡ Gold Scalper Bot (5M Liquidity Sweep + EMA) Avviato e Attivo! 🚀")

    while True:
        try:
            analyze_scalp()
        except Exception as e:
            print(f"Errore durante l'esecuzione: {e}")
        time.sleep(CHECK_INTERVAL)
