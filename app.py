from flask import Flask, request
import bybit
import threading

app = Flask(__name__)

# ⛔ YOUR BYBIT TESTNET API KEYS (already provided)
API_KEY = 'P95IalDQwSpUFZvUTQ51US1ovWfSRhAuYVTg'
API_SECRET = 'red36cu3AaIIxEDXUO'

# ✅ Use Bybit testnet
client = bybit.bybit(test=True, api_key=API_KEY, api_secret=API_SECRET)

# 🧠 Trading settings
SYMBOL = "SOLUSDT"
LEVERAGE = 60
MARGIN = 3  # USDT
TP_USDT = 2
SL_USDT = 1

position_open = False

@app.route('/webhook', methods=['POST'])
def webhook():
    global position_open
    data = request.json

    if position_open:
        return "Position already open", 200

    if data.get("action") == "short":
        threading.Thread(target=place_short_trade).start()
        return "Short signal received", 200

    return "Invalid signal", 400

def place_short_trade():
    global position_open
    try:
        # Cancel all open orders before starting
        client.LinearOrder.LinearOrder_cancelAll(symbol=SYMBOL).result()

        # Set leverage
        client.LinearPositions.LinearPositions_saveLeverage(
            symbol=SYMBOL, buy_leverage=LEVERAGE, sell_leverage=LEVERAGE).result()

        # Get current market price
        ticker = client.Market.Market_symbolInfo(symbol=SYMBOL).result()
        mark_price = float(ticker[0]['result'][0]['last_price'])

        # Calculate quantity to short
        qty = round((MARGIN * LEVERAGE) / mark_price, 3)

        # Open short position
        client.LinearOrder.LinearOrder_new(
            symbol=SYMBOL,
            side="Sell",
            order_type="Market",
            qty=qty,
            time_in_force="GoodTillCancel",
            reduce_only=False
        ).result()

        position_open = True

        # Calculate TP and SL prices
        tp_price = round(mark_price - (TP_USDT / qty), 3)
        sl_price = round(mark_price + (SL_USDT / qty), 3)

        # Set Take Profit order
        client.LinearOrder.LinearOrder_new(
            symbol=SYMBOL,
            side="Buy",
            order_type="Limit",
            qty=qty,
            price=tp_price,
            time_in_force="GoodTillCancel",
            reduce_only=True
        ).result()

        # Set Stop Loss
        client.LinearOrder.LinearOrder_new_stop(
            symbol=SYMBOL,
            side="Buy",
            order_type="Market",
            qty=qty,
            stop_loss=sl_price,
            base_price=mark_price,
            time_in_force="GoodTillCancel",
            reduce_only=True
        ).result()

    except Exception as e:
        print("❌ Error placing trade:", str(e))
        position_open = False

@app.route('/')
def home():
    return "✅ Bybit bot is running 24/7"

if __name__ == '__main__':
    app.run()
