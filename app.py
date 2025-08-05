from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP

app = Flask(__name__)

# CONFIGURATION
WEBHOOK_PASSPHRASE = "abc123"
API_KEY = "O6o45ugAjaA9DIOpYU"
API_SECRET = "DBA3RWkisO9mYVUT0UdhMqj8QwTbbYrbyXcX"
SYMBOL = "SOLUSDT"
LEVERAGE = 60
MARGIN = 3  # $3 per trade
ENTRY_PRICE_ESTIMATE = 20  # Adjust based on market for qty calc
TP_PROFIT = 2
SL_LOSS = 1

# Connect to Bybit Testnet
session = HTTP(
    testnet=True,
    api_key=API_KEY,
    api_secret=API_SECRET
)

@app.route("/", methods=["GET"])
def home():
    return "Bybit Auto Short Bot Running..."

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("Received Webhook:", data)

    # 1. Check passphrase
    if data.get("passphrase") != WEBHOOK_PASSPHRASE:
        return jsonify({"error": "Wrong passphrase"}), 403

    # 2. Only SHORT is allowed
    side = data.get("side", "").lower()
    if side != "sell":
        return jsonify({"error": "Only SHORT (sell) allowed."}), 400

    try:
        # 3. Check open positions
        pos = session.get_positions(category="linear", symbol=SYMBOL)
        size = float(pos['result']['list'][0]['size'])
        if size > 0:
            return jsonify({"error": "Trade already open, wait until it's closed."}), 400

        # 4. Calculate quantity
        qty = round((MARGIN * LEVERAGE) / ENTRY_PRICE_ESTIMATE, 2)

        # 5. Place SHORT entry
        entry_order = session.place_order(
            category="linear",
            symbol=SYMBOL,
            side="Sell",
            order_type="Market",
            qty=qty,
            time_in_force="GoodTillCancel",
            reduce_only=False
        )
        print("Short entry placed:", entry_order)

        # 6. Get executed price
        entry_price = float(entry_order['result']['order_price'])

        # 7. Calculate TP & SL
        tp_price = round(entry_price - TP_PROFIT, 2)
        sl_price = round(entry_price + SL_LOSS, 2)

        # 8. Set TP & SL
        tp_order = session.place_order(
            category="linear",
            symbol=SYMBOL,
            side="Buy",
            order_type="Limit",
            qty=qty,
            price=tp_price,
            time_in_force="GoodTillCancel",
            reduce_only=True
        )
        sl_order = session.set_trading_stop(
            category="linear",
            symbol=SYMBOL,
            stop_loss=sl_price
        )

        return jsonify({
            "message": "Short trade executed with TP & SL",
            "entry_price": entry_price,
            "take_profit": tp_price,
            "stop_loss": sl_price
        }), 200

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
