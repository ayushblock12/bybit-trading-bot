from flask import Flask, request
from pybit.unified_trading import HTTP
import threading

app = Flask(__name__)

# Bybit testnet credentials
api_key = "P95IalDQwSpUFZvUTQ51US1ovWfSRhAuYVTg"
api_secret = "red36cu3AaIIxEDXUO"

session = HTTP(
    testnet=True,
    api_key=api_key,
    api_secret=api_secret
)

# Config
symbol = "SOLUSDT"
leverage = 60
margin = 3
in_position = False

@app.route("/", methods=["GET"])
def index():
    return "Bybit bot is running."

@app.route("/webhook", methods=["POST"])
def webhook():
    global in_position

    data = request.get_json()

    if data is None or "passphrase" not in data or data["passphrase"] != "your_secret_pass":
        return {"error": "Invalid passphrase"}, 401

    if in_position:
        return {"status": "Already in a trade"}

    threading.Thread(target=open_trade).start()
    return {"status": "Short trade signal received"}

def open_trade():
    global in_position

    try:
        in_position = True

        # Get current price
        price = float(session.get_orderbook(symbol=symbol)["result"]["b"][0][0])

        # Calculate quantity
        qty = round((margin * leverage) / price, 2)

        # Place market short order
        session.place_order(
            category="linear",
            symbol=symbol,
            side="Sell",
            order_type="Market",
            qty=qty,
            time_in_force="GoodTillCancel",
            reduce_only=False
        )

        entry_price = price
        sl_price = round(entry_price + (1 / qty), 3)
        tp_price = round(entry_price - (2 / qty), 3)

        # Set stop loss & take profit
        session.set_trading_stop(
            category="linear",
            symbol=symbol,
            stop_loss=str(sl_price),
            take_profit=str(tp_price)
        )

        print("Short position opened")

    except Exception as e:
        print("Error placing order:", e)

    finally:
        # Monitor the position and wait for TP/SL
        while True:
            pos = session.get_positions(category="linear", symbol=symbol)["result"]["list"][0]
            if float(pos["size"]) == 0:
                in_position = False
                print("Position closed.")
                break

if __name__ == "__main__":
    app.run(debug=True)
