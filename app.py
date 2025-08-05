from flask import Flask, request, jsonify
from pybit.unified_trading import HTTP

app = Flask(__name__)

# Set this to match what you use in TradingView webhook
WEBHOOK_PASSPHRASE = "abc123"

# Your API credentials (testnet)
API_KEY = "O6o45ugAjaA9DIOpYU"
API_SECRET = "DBA3RWkisO9mYVUT0UdhMqj8QwTbbYrbyXcX"

# Create Bybit client
session = HTTP(
    testnet=True,
    api_key=API_KEY,
    api_secret=API_SECRET
)

@app.route("/", methods=["GET"])
def home():
    return "Bybit Bot is Running"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("Incoming Webhook:", data)

    if data.get("passphrase") != WEBHOOK_PASSPHRASE:
        return jsonify({"error": "Wrong passphrase"}), 403

    side = data.get("side")
    if side not in ["buy", "sell"]:
        return jsonify({"error": "Invalid side"}), 400

    # Risk management setup
    margin = 3  # $3 margin per trade
    leverage = 60
    qty = round((margin * leverage) / 20, 2)  # Example for SOL/USDT at ~$20

    try:
        order = session.place_order(
            category="linear",
            symbol="SOLUSDT",
            side=side.upper(),
            order_type="Market",
            qty=qty,
            time_in_force="GoodTillCancel",
            reduce_only=False
        )
        print("Order response:", order)
        return jsonify({"message": f"{side.upper()} order placed", "order": order}), 200
    except Exception as e:
        print("Order Error:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
