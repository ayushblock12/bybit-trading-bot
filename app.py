from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP
import time

app = Flask(__name__)

WEBHOOK_PASSPHRASE = "abc123"

API_KEY = "P95IalDQwSpUFZvUTQ51US1ovWfSRhAuYVTg"
API_SECRET = "red36cu3AaIIxEDXUO"

session = HTTP(
    testnet=False,  # MAINNET
    api_key=API_KEY,
    api_secret=API_SECRET
)

SYMBOL = "SOLUSDT"
LEVERAGE = 60
MARGIN = 3
ENTRY_PRICE = None


def position_is_open():
    try:
        response = session.get_positions(category="linear", symbol=SYMBOL)
        pos = response["result"]["list"][0]
        return float(pos["size"]) > 0
    except Exception as e:
        print("Position check failed:", e)
        return False


@app.route("/")
def home():
    return "✅ Bybit Bot is Running on Railway"


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("Webhook Data:", data)

    if data.get("passphrase") != WEBHOOK_PASSPHRASE:
        return jsonify({"error": "Invalid passphrase"}), 403

    if data.get("side").lower() != "sell":
        return jsonify({"error": "Only short trades allowed"}), 400

    if position_is_open():
        return jsonify({"message": "Position already open. Waiting for TP or SL."}), 200

    try:
        # Assume SOLUSDT is ~$20
        entry_price = session.get_ticker(category="linear", symbol=SYMBOL)["result"]["list"][0]["lastPrice"]
        entry_price = float(entry_price)

        qty = round((MARGIN * LEVERAGE) / entry_price, 3)
        tp_price = round(entry_price * 0.967, 3)  # ~2 USDT gain
        sl_price = round(entry_price * 1.0167, 3)  # ~1 USDT loss

        # Open short position
        order = session.place_order(
            category="linear",
            symbol=SYMBOL,
            side="Sell",
            order_type="Market",
            qty=qty,
            time_in_force="GoodTillCancel",
            reduce_only=False
        )

        time.sleep(1)  # Delay to ensure position opens

        # Set TP/SL
        session.set_trading_stop(
            category="linear",
            symbol=SYMBOL,
            take_profit=tp_price,
            stop_loss=sl_price
        )

        return jsonify({
            "message": "✅ Short position placed",
            "entry_price": entry_price,
            "tp": tp_price,
            "sl": sl_price
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run()
