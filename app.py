from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP

app = Flask(__name__)

# === YOUR API INFO ===
API_KEY = "O6o45ugAjaA9DIOpYU"
API_SECRET = "DBA3RWkisO9mYVUT0UdhMqj8QwTbbYrbyXcX"
PASS_PHRASE = "mysecret"  # Use this to verify incoming signals

# === BOT CONFIG ===
TRADE_SYMBOL = "SOLUSDT"
TRADE_MARGIN = 3  # $3
LEVERAGE = 60
active_trade = False

# === INIT BYBIT TESTNET SESSION ===
session = HTTP(
    testnet=True,
    api_key=API_KEY,
    api_secret=API_SECRET
)

@app.route('/')
def index():
    return "Bybit Bot is Live!"

@app.route('/webhook', methods=['POST'])
def webhook():
    global active_trade

    data = request.get_json()
    if data.get("passphrase") != PASS_PHRASE:
        return jsonify({"error": "Wrong passphrase"}), 403

    if active_trade:
        return jsonify({"status": "Trade already active. Wait for TP or SL."})

    if data.get("signal") == "short":
        try:
            # Set leverage
            session.set_leverage(
                category="linear",
                symbol=TRADE_SYMBOL,
                buy_leverage=LEVERAGE,
                sell_leverage=LEVERAGE
            )

            # Place SHORT market order
            usdt_qty = round((TRADE_MARGIN * LEVERAGE) / 100, 3)  # Approx qty at 60x leverage
            entry = session.place_order(
                category="linear",
                symbol=TRADE_SYMBOL,
                side="Sell",
                order_type="Market",
                qty=usdt_qty,
                time_in_force="GoodTillCancel"
            )

            # Get filled price
            entry_price = float(entry['result']['order_price'])

            # Set TP and SL
            tp_price = round(entry_price - (2 / usdt_qty), 3)  # $2 profit
            sl_price = round(entry_price + (1 / usdt_qty), 3)  # $1 loss

            session.set_trading_stop(
                category="linear",
                symbol=TRADE_SYMBOL,
                take_profit=tp_price,
                stop_loss=sl_price,
                position_idx=2  # short
            )

            active_trade = True
            return jsonify({"status": "Short trade placed", "entry": entry_price, "tp": tp_price, "sl": sl_price})

        except Exception as e:
            return jsonify({"error": str(e)})
    else:
        return jsonify({"error": "Invalid or missing signal"}), 400

# Optional: endpoint to reset trade lock manually
@app.route('/reset', methods=['POST'])
def reset_trade_flag():
    global active_trade
    active_trade = False
    return jsonify({"status": "Trade flag reset"})

if __name__ == '__main__':
    app.run()
