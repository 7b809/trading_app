from flask import Flask, request, jsonify, render_template
from db import alerts_collection, trades_collection
from trade_engine import process_signal

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    alerts_collection.insert_one(data)

    trade = process_signal(data)
    if trade:
        trade["symbol"] = data.get("symbol")
        trade["datetime"] = data.get("datetime")
        trades_collection.insert_one(trade)

    return jsonify({"status": "success"})

@app.route("/alerts", methods=["GET"])
def get_alerts():
    alerts = list(alerts_collection.find({}, {"_id": 0}).sort("datetime", -1).limit(50))
    return jsonify(alerts)

@app.route("/trades", methods=["GET"])
def get_trades():
    trades = list(trades_collection.find({}, {"_id": 0}).sort("datetime", -1).limit(50))
    return jsonify(trades)

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

if __name__ == "__main__":
    app.run(debug=True)
