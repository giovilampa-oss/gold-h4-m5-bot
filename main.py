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
    return "Gold Scalper Bot PRO (5M Advanced) is running live!"

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
active_trades = []          # Monitoraggio trade attivi

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

def is_trading_hours(rome_dt):
    """Filtro Orario: Opera dalle 08:00 alle 22:00 (Ora Italiana)"""
    return 8 <= rome_dt.hour < 22

# --------------------------------------------------
# THREAD: MONITORAGGIO WIN / LOSS / BREAK-EVEN
# --------------------------------------------------
def monitor_active_trades():
    global active_trades
    while True:
        try:
            if active_trades:
                candles = get_market_data()
                if candles and len(candles) > 0:
                    current_price = float(candles[-1]['close'])
                    trades_to_remove = []
                    
                    for trade in active_trades:
                        # Controllo LONG
                        if trade['type'] == 'LONG':
                            # Requisito Break-Even (R : R = 1 : 1)
                            if not trade['be_notified'] and current_price >= (trade['entry'] + trade['risk']):
                                send_telegram_message(
                                    f"🛡️ **AGGIORNAMENTO TRADE LONG ({SYMBOL})**\n\n"
                                    f"Il prezzo ha raggiunto +1R (`{current_price}`)!\n"
                                    f"💡 **Consiglio:** Sposta lo Stop Loss a B/E (Break-Even) a `{trade['entry']}` per azzerare il rischio!"
                                )
                                trade['be_notified'] = True

                            # Take Profit
                            if current_price >= trade['tp']:
                                send_telegram_message(
                                    f"🎉 **TAKE PROFIT COLPITO! (WIN)** 🎉\n\n"
                                    f"🌐 **Strumento:** {SYMBOL}\n"
                                    f"📊 **Tipo:** LONG\n"
                                    f"🎯 **Profit Target:** `{trade['tp']}`\n"
                                    f"🚀 **Esito:** Operazione chiusa in PROFITTO!"
                                )
                                trades_to_remove.append(trade)

                            # Stop Loss
                            elif current_price <= trade['sl']:
                                send_telegram_message(
                                    f"🛑 **STOP LOSS COLPITO (LOSS)** 🛑\n\n"
                                    f"🌐 **Strumento:** {SYMBOL}\n"
                                    f"📊 **Tipo:** LONG\n"
                                    f"🛑 **Prezzo Uscita:** `{trade['sl']}`"
                                )
                                trades_to_remove.append(trade)

                        # Controllo SHORT
                        elif trade['type'] == 'SHORT':
                            # Requisito Break-Even
                            if not trade['be_notified'] and current_price <= (trade['entry'] - trade['risk']):
                                send_telegram_message(
                                    f"🛡️ **AGGIORNAMENTO TRADE SHORT ({SYMBOL})**\n\n"
                                    f"Il prezzo ha raggiunto +1R (`{current_price}`)!\n"
                                    f"💡 **Consiglio:** Sposta lo Stop Loss a B/E (Break-Even) a `{trade['entry']}` per azzerare il rischio!"
                                )
                                trade['be_notified'] = True

                            # Take Profit
                            if current_price <= trade['tp']:
                                send_telegram_message(
                                    f"🎉 **TAKE PROFIT COLPITO! (WIN)** 🎉\n\n"
                                    f"🌐 **Strumento:** {SYMBOL}\n"
                                    f"📊 **Tipo:** SHORT\n"
                                    f"🎯 **Profit Target:** `{trade['tp']}`\n"
                                    f"🚀 **Esito:** Operazione chiusa in PROFITTO!"
                                )
                                trades_to_remove.append(trade)

                            # Stop Loss
                            elif current_price >= trade['sl']:
                                send_telegram_message(
                                    f"🛑 **STOP LOSS COLPITO (LOSS)** 🛑\n\n"
                                    f"🌐 **Strumento:** {SYMBOL}\n"
                                    f"📊 **Tipo:** SHORT\n"
                                    f"🛑 **Prezzo Uscita:** `{trade['sl']}`"
                                )
                                trades_to_remove.append(trade)

                    for t in trades_to_remove:
                        if t in active_trades:
                            active_trades.remove(t)

        except Exception as e:
            print(f"Errore nel monitoraggio trade: {e}")

        time.sleep(15)  # Controlla ogni 15 secondi

# --------------------------------------------------
# LOGICA DI TRADING: LIQUIDITY SWEEP & EMA FILTER
# --------------------------------------------------
def analyze_scalp():
    global last_signal_time, active_trades

    candles = get_market_data()
    if not candles or len(candles) < LOOKBACK + 2:
        return

    # Ultima candela chiusa (index -2)
    last_candle = candles[-2]
    prev_candles = candles[-(LOOKBACK + 2):-2]

    time_str = last_candle['datetime']
    if last_signal_time == time_str:
        return

    # Converti orario in fuso orario di Roma (Europe/Rome)
    try:
        dt_utc = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.utc)
        rome_tz = pytz.timezone("Europe/Rome")
        rome_dt = dt_utc.astimezone(rome_tz)
        formatted_time = rome_dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        rome_dt = datetime.datetime.now(pytz.timezone("Europe/Rome"))
        formatted_time = time_str

    # Filtro Orario Attivo
    if not is_trading_hours(rome_dt):
        return

    high_p = float(last_candle['high'])
    low_p = float(last_candle['low'])
    close_p = float(last_candle['close'])
    open_p = float(last_candle['open'])

    ema_200 = float(last_candle.get('ema', close_p))
    atr = float(last_candle.get('atr', 1.20))

    recent_high = max(float(c['high']) for c in prev_candles)
    recent_low = min(float(c['low']) for c in prev_candles)

    range_size = abs(high_p - low_p)
    if range_size == 0:
        return

    lower_wick = min(open_p, close_p) - low_p
    upper_wick = high_p - max(open_p, close_p)

    # --- CONDIZIONI LONG ---
    is_low_sweep = low_p < recent_low
    is_bullish_rejection = (lower_wick / range_size) > 0.45 and close_p > low_p

    if is_low_sweep and is_bullish_rejection and close_p > ema_200:
        last_signal_time = time_str
        
        sl = round(low_p - (1.5 * atr), 2)
        risk = round(close_p - sl, 2)
        tp = round(close_p + (risk * 2), 2)

        active_trades.append({
            'type': 'LONG',
            'entry': close_p,
            'sl': sl,
            'tp': tp,
            'risk': risk,
            'be_notified': False
        })

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
        print(f"[{datetime.datetime.now()}] BUY Scalp inviato e messo in monitoraggio!")
        return

    # --- CONDIZIONI SHORT ---
    is_high_sweep = high_p > recent_high
    is_bearish_rejection = (upper_wick / range_size) > 0.45 and close_p < high_p

    if is_high_sweep and is_bearish_rejection and close_p < ema_200:
        last_signal_time = time_str
        
        sl = round(high_p + (1.5 * atr), 2)
        risk = round(sl - close_p, 2)
        tp = round(close_p - (risk * 2), 2)

        active_trades.append({
            'type': 'SHORT',
            'entry': close_p,
            'sl': sl,
            'tp': tp,
            'risk': risk,
            'be_notified': False
        })

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
        print(f"[{datetime.datetime.now()}] SELL Scalp inviato e messo in monitoraggio!")
        return

# --------------------------------------------------
# MAIN LOOP
# --------------------------------------------------
if __name__ == '__main__':
    # Avvia Flask in un thread separato
    t_flask = Thread(target=run_flask)
    t_flask.daemon = True
    t_flask.start()

    # Avvia il Monitor dei Trade Attivi in un thread separato
    t_monitor = Thread(target=monitor_active_trades)
    t_monitor.daemon = True
    t_monitor.start()

    send_telegram_message("⚡ Gold Scalper Bot PRO (5M Sweep + EMA + BE & Win Tracker) Avviato! 🚀")

    while True:
        try:
            analyze_scalp()
        except Exception as e:
            print(f"Errore durante l'esecuzione: {e}")
        time.sleep(CHECK_INTERVAL)
