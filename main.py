import os
import time
import datetime
import pytz
import requests
from threading import Thread
from flask import Flask

# ---------------------------------------------------------
# CONFIGURAZIONE FLASK (Keep-alive per Render)
# ---------------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Gold Scalper Bot (Liquidity Sweep + EMA Filter) is running live!"

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
TIMEFRAME = "1min"      
LOOKBACK = 12           
CHECK_INTERVAL = 60     

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
    """Recupera le candele, l'ATR e l'EMA da Twelve Data"""
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={TIMEFRAME}&outputsize=50&apikey={TWELVE_DATA_KEY}&indicators=atr(timeperiod=14),ema(timeperiod=50)"
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
# LOGICA DI TRADING: LIQUIDITY SWEEP + EMA FILTER
# ---------------------------------------------------------
def analyze_scalp():
    global last_signal_time

    candles = get_market_data()
    if not candles or len(candles) < LOOKBACK + 2:
        return

    # Ultima candela chiusa (index -2)
    last_candle = candles[-2]
    past_candles = candles[-(LOOKBACK+2):-2]

    open_p = float(last_candle['open'])
    high_p = float(last_candle['high'])
    low_p = float(last_candle['low'])
    close_p = float(last_candle['close'])
    time_str = last_candle['datetime']
    
    # Valore dell'EMA a 50 calcolato da Twelve Data sulla candela
    ema_val = float(last_candle.get('ema', close_p))

    tz = pytz.timezone('Europe/Rome')
    formatted_time = datetime.datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

    # Evita segnali duplicati sulla stessa candela
    if last_signal_time == time_str:
        return

    # Massimo e minimo del range recente
    past_highs = [float(c['high']) for c in past_candles]
    past_lows = [float(c['low']) for c in past_candles]
    
    recent_high = max(past_highs)
    recent_low = min(past_lows)

    range_size = high_p - low_p
    if range_size == 0:
        return

    upper_wick = high_p - max(open_p, close_p)
    lower_wick = min(open_p, close_p) - low_p

    # --- CONDIZIONI LONG (SWEEP LOW + WICK RIALZISTA + TREND RIALZISTA SOPRA EMA) ---
    is_low_sweep = low_p < recent_low
    is_bullish_rejection = (lower_wick / range_size) > 0.45 and close_p > low_p
    is_above_ema = close_p > ema_val  # Filtro trend: compriamo solo se siamo sopra l'EMA

    if is_low_sweep and is_bullish_rejection and is_above_ema:
        last_signal_time = time_str
        atr = float(last_candle.get('atr', 1.20))
        sl = round(low_p - (1.5 * atr), 2)
        risk = round(close_p - sl, 2)
        tp = round(close_p + (risk * 2), 2)
        msg = (
            f"⚡ **SCALPER BOT 1M - SEGNALE BUY (Filtro EMA attivo)** ⚡\n\n"
            f"🪙 **Strumento:** {SYMBOL}\n"
            f"📊 **Tipo:** LONG (Sweep Minimi + Trend OK)\n"
            f"💵 **Prezzo Entrata:** `{close_p}`\n"
            f"🛑 **Stop Loss:** `{sl}`\n"
            f"🎯 **Take Profit:** `{tp}`\n"
            f"📈 **EMA 50:** `{ema_val}`\n"
            f"⏰ **Orario:** {formatted_time}"
        )
        send_telegram_message(msg)
        print(f"[{datetime.datetime.now()}] BUY Scalp filtrato da EMA inviato!")
        return

    # --- CONDIZIONI SHORT (SWEEP HIGH + WICK RIBASSISTA + TREND RIBASSISTA SOTTO EMA) ---
    is_high_sweep = high_p > recent_high
    is_bearish_rejection = (upper_wick / range_size) > 0.45 and close_p < high_p
    is_below_ema = close_p < ema_val  # Filtro trend: vendiamo solo se siamo sotto l'EMA

    if is_high_sweep and is_bearish_rejection and is_below_ema:
        last_signal_time = time_str
        atr = float(last_candle.get('atr', 1.20))
        sl = round(high_p + (1.5 * atr), 2)
        risk = round(sl - close_p, 2)
        tp = round(close_p - (risk * 2), 2)
        msg = (
            f"⚡ **SCALPER BOT 1M - SEGNALE SELL (Filtro EMA attivo)** ⚡\n\n"
            f"🪙 **Strumento:** {SYMBOL}\n"
            f"📊 **Tipo:** SHORT (Sweep Massimi + Trend OK)\n"
            f"💵 **Prezzo Entrata:** `{close_p}`\n"
            f"🛑 **Stop Loss:** `{sl}`\n"
            f"🎯 **Take Profit:** `{tp}`\n"
            f"📈 **EMA 50:** `{ema_val}`\n"
            f"⏰ **Orario:** {formatted_time}"
        )
        send_telegram_message(msg)
        print(f"[{datetime.datetime.now()}] SELL Scalp filtrato da EMA inviato!")
        return

# ---------------------------------------------------------
# LOOP PRINCIPALE
# ---------------------------------------------------------
def main_loop():
    print("🚀 Gold Scalper Bot (1M + EMA Filter) Avviato!")
    send_telegram_message("⚡ **Gold Scalper Bot (Liquidity Sweep + Filtro EMA) Avviato e Attivo!** 🚀")
    
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
