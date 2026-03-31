from flask import Flask, request, jsonify, render_template
from db import alerts_collection, trades_collection
from trade_engine import process_signal

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    # store alert
    alerts_collection.insert_one(data)

    # process trade
    trade = process_signal(data)

    if trade:
        trade["symbol"] = data.get("symbol")
        trade["datetime"] = data.get("datetime")
        trades_collection.insert_one(trade)

    return jsonify({"status": "success"})


# 🔹 UPDATED (symbol + limit support)
@app.route("/alerts", methods=["GET"])
def get_alerts():
    symbol = request.args.get("symbol")
    limit = int(request.args.get("limit", 50))  # ✅ NEW (default 50)

    query = {}
    if symbol:
        query["symbol"] = symbol

    alerts = list(
        alerts_collection.find(query, {"_id": 0})
        .sort("datetime", -1)
        .limit(limit)  # ✅ using dynamic limit
    )

    return jsonify(alerts)


# 🔹 UPDATED (symbol + limit support)
@app.route("/trades", methods=["GET"])
def get_trades():
    symbol = request.args.get("symbol")
    limit = int(request.args.get("limit", 50))  # ✅ NEW (default 50)

    query = {}
    if symbol:
        query["symbol"] = symbol

    trades = list(
        trades_collection.find(query, {"_id": 0})
        .sort("datetime", -1)
        .limit(limit)  # ✅ using dynamic limit
    )

    return jsonify(trades)


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


if __name__ == "__main__":
    app.run(debug=True)