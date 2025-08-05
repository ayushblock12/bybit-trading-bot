from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP

app = Flask(__name__)

# Your TradingView passphrase
WEBHOOK_PASSPHRASE = "abc123"

# Mainnet API keys
API_KEY = "P95IalDQwSpUFZvUTQ51US1ovWfSRhAuYVTg"
API_SECRET = "red36cu3AaIIxEDXUO"

# Connect to Bybit Mainnet
session = HTTP(
    testnet=False,
    api_key=API_KEY,
    api_secret=API_SECRET
)

# Trade parameters
SYMBOL = "SOLUSDT"
LEVERAGE = 60
MARGIN = 3  # 3 USDT
TP_USD = 2  # Take profit: $2
SL_USD = 1  # Stop loss: $1

@app.route("/", methods=["GET"])
def home():
    return "Bybit Mainnet Bot is Running"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("Incoming Webhook:", data)

    # Check passphrase
    if data.get("passphrase") != WEBHOOK_PASSPHRASE:
        return jsonify({"error": "Wrong passphrase"}), 403

    side = data.get("side")
    if side != "sell":
        return jsonify({"error": "Only short (sell) positions are allowed"}), 400

    # Check if already in position
    try:
        pos = session.get_positions(category="linear", symbol=SYMBOL)
        size = float(pos['result']['list'][0]['size'])
        if size > 0:
            return jsonify({"message": "Position already open. Waiting for it to close."}), 200
    except Exception as e:
        return jsonify({"error": f"Position check failed: {str(e)}"}), 500

    # Get market price to calculate quantity
    try:
        price_data = session.get_tickers(category="linear", symbol=SYMBOL)
        last_price = float(price_data['result']['list'][0]['lastPrice'])
    except Exception as e:
        return jsonify({"error": f"Price fetch error: {str(e)}"}), 500

    # Calculate quantity based on margin and leverage
    trade_value = MARGIN * LEVERAGE
    qty = round(trade_value / last_price, 3)

    # Calculate SL and TP price
    sl_price = round(last_price + (SL_USD / qty), 2)
    tp_price = round(last_price - (TP_USD / qty), 2)

    try:
        # Place short order
        order = session.place_order(
            category="linear",
            symbol=SYMBOL,
            side="Sell",
            order_type="Market",
            qty=qty,
            time_in_force="GoodTillCancel",
            reduce_only=False,
            take_profit=tp_price,
            stop_loss=sl_price
        )
        return jsonify({
            "message": "Short position opened",
            "entry_price": last_price,
            "tp_price": tp_price,
            "sl_price": sl_price,
            "qty": qty,
            "order": order
        }), 200
    except Exception as e:
        return jsonify({"error": f"Order placement failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
