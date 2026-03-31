from flask import Flask, request, jsonify, render_template
from db import alerts_collection, trades_collection
from trade_engine import process_signal
import logging

app = Flask(__name__)

# 🔹 Logging toggle
test_log = False

# 🔹 Logger setup (non-intrusive)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

def log(msg):
    if test_log:
        logging.info(msg)


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    # =========================
    # 🔹 PROCESS TRADE FIRST
    # =========================
    trade = process_signal(data)

    # =========================
    # 🔹 ADD option_type (CE/PE)
    # =========================
    if trade:
        if "CE" in trade["type"]:
            data["option_type"] = "CE"
        elif "PE" in trade["type"]:
            data["option_type"] = "PE"

    # 🔹 FALLBACK (VERY IMPORTANT)
    if not data.get("option_type"):
        if data.get("action") in ["BUY", "EXIT_BUY"]:
            data["option_type"] = "CE"
        elif data.get("action") in ["SELL", "EXIT_SELL"]:
            data["option_type"] = "PE"

    # =========================
    # 🔹 STORE ALERT (ENRICHED)
    # =========================
    alerts_collection.insert_one(data)

    # 🔹 LOG (alerts)
    if test_log:
        symbol = data.get("symbol")
        query = {"symbol": symbol} if symbol else {}
        total_alerts = alerts_collection.count_documents(query)
        log(f"[WEBHOOK] Alerts Count | Symbol: {symbol or 'ALL'} | Total: {total_alerts}")

    # =========================
    # 🔹 STORE TRADE
    # =========================
    if trade:
        trade["symbol"] = data.get("symbol")
        trade["datetime"] = data.get("datetime")
        trades_collection.insert_one(trade)

        # 🔹 LOG (trades)
        if test_log:
            symbol = trade.get("symbol")
            query = {"symbol": symbol} if symbol else {}
            total_trades = trades_collection.count_documents(query)
            log(f"[WEBHOOK] Trades Count | Symbol: {symbol or 'ALL'} | Total: {total_trades}")

    return jsonify({"status": "success"})


# 🔹 UPDATED (symbol + limit support)
@app.route("/alerts", methods=["GET"])
def get_alerts():
    symbol = request.args.get("symbol")
    limit = int(request.args.get("limit", 50))

    query = {}
    if symbol:
        query["symbol"] = symbol

    if test_log:
        total_alerts = alerts_collection.count_documents(query)
        log(f"[ALERTS API] Requested | Symbol: {symbol or 'ALL'} | Total Found: {total_alerts} | Limit: {limit}")

    alerts = list(
        alerts_collection.find(query, {"_id": 0})
        .sort("datetime", -1)
        .limit(limit)
    )

    if test_log:
        log(f"[ALERTS API] Returned Count: {len(alerts)}")

    return jsonify(alerts)


# 🔹 UPDATED (symbol + limit support)
@app.route("/trades", methods=["GET"])
def get_trades():
    symbol = request.args.get("symbol")
    limit = int(request.args.get("limit", 50))

    query = {}
    if symbol:
        query["symbol"] = symbol

    if test_log:
        total_trades = trades_collection.count_documents(query)
        log(f"[TRADES API] Requested | Symbol: {symbol or 'ALL'} | Total Found: {total_trades} | Limit: {limit}")

    trades = list(
        trades_collection.find(query, {"_id": 0})
        .sort("datetime", -1)
        .limit(limit)
    )

    if test_log:
        log(f"[TRADES API] Returned Count: {len(trades)}")

    return jsonify(trades)


@app.route("/symbols", methods=["GET"])
def get_symbols():
    symbols = alerts_collection.distinct("symbol")
    return jsonify(symbols)


@app.route("/")
def dashboard():
    if test_log:
        log("[DASHBOARD] UI Requested")

    return render_template("dashboard.html")


if __name__ == "__main__":
    if test_log:
        log("🚀 Flask App Started")

    app.run(debug=True)