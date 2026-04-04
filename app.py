from flask import Flask, request, jsonify, render_template
from db import alerts_collection, trades_collection
from trade_engine import process_signal
import logging

# 🔹 NEW IMPORTS (for time logic)
from datetime import datetime, time
import pytz
from db import alerts_offtime_collection, trades_offtime_collection

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

# 🔹 IST timezone
IST = pytz.timezone("Asia/Kolkata")


# =========================
# 🔹 NEW: PARSE NEW ALERT FORMAT
# =========================
def parse_new_alert(raw_msg):
    mapping = {
        "pe_exit_ce_entry": ["EXIT_SELL", "BUY"],
        "ce_exit_pe_entry": ["EXIT_BUY", "SELL"]
    }
    return mapping.get(str(raw_msg).lower())


# =========================
# 🔹 Time window checker (UNCHANGED)
# =========================
def is_within_time_window(dt_str):
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        dt = IST.localize(dt)

        start = time(13, 30)
        end = time(14, 40)

        return start <= dt.time() <= end
    except Exception:
        return False


# =========================
# 🔥 MODIFIED WEBHOOK (ROUTE BASED + NEW FORMAT SUPPORT)
# =========================
@app.route("/webhook/<route_id>", methods=["POST"])
def webhook(route_id):
    data = request.json

    raw_message = data.get("message")  # 🔹 NEW
    symbol = data.get("symbol")
    price = float(data.get("price", 0))

    # 🔹 CURRENT IST TIME (REQUEST TIME)
    now_ist = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

    # =========================
    # 🔹 NEW ALERT PARSING
    # =========================
    parsed_actions = parse_new_alert(raw_message)

    trade = None

    # =========================
    # 🔹 PROCESS TRADE FIRST (MODIFIED ONLY IF NEW FORMAT)
    # =========================
    if parsed_actions:
        for action in parsed_actions:
            temp_data = {
                "symbol": symbol,
                "action": action,
                "price": price
            }
            trade = process_signal(temp_data)

            if trade:
                trade["symbol"] = symbol
                trade["datetime"] = now_ist
                trade["route"] = route_id

                # 🔹 ADD option_type (SAME LOGIC)
                if "CE" in trade["type"]:
                    temp_data["option_type"] = "CE"
                elif "PE" in trade["type"]:
                    temp_data["option_type"] = "PE"

                # 🔹 TIME CHECK (UNCHANGED LOGIC)
                in_time = is_within_time_window(now_ist)

                if in_time:
                    trades_collection.insert_one(trade)
                else:
                    trades_offtime_collection.insert_one(trade)

    else:
        # =========================
        # 🔹 FALLBACK TO OLD LOGIC (UNCHANGED)
        # =========================
        trade = process_signal(data)

        if trade:
            if "CE" in trade["type"]:
                data["option_type"] = "CE"
            elif "PE" in trade["type"]:
                data["option_type"] = "PE"

        if not data.get("option_type"):
            if data.get("action") in ["BUY", "EXIT_BUY"]:
                data["option_type"] = "CE"
            elif data.get("action") in ["SELL", "EXIT_SELL"]:
                data["option_type"] = "PE"

        in_time = is_within_time_window(data.get("datetime", ""))

        if trade:
            trade["symbol"] = data.get("symbol")
            trade["datetime"] = data.get("datetime")
            trade["route"] = route_id

            if in_time:
                trades_collection.insert_one(trade)
            else:
                trades_offtime_collection.insert_one(trade)

    # =========================
    # 🔹 STORE ALERT (ENHANCED BUT SAFE)
    # =========================
    alert_doc = data.copy()

    alert_doc["message"] = raw_message
    alert_doc["route"] = route_id
    alert_doc["datetime"] = now_ist  # 🔹 ALWAYS REQUEST TIME

    in_time_alert = is_within_time_window(now_ist)

    if in_time_alert:
        alerts_collection.insert_one(alert_doc)
    else:
        alerts_offtime_collection.insert_one(alert_doc)

    return jsonify({"status": "success"})


# =========================
# 🔹 ALERTS API (UNCHANGED)
# =========================
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


# =========================
# 🔹 TRADES API (UNCHANGED)
# =========================
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


# =========================
# 🔹 SYMBOLS API (UNCHANGED)
# =========================
@app.route("/symbols", methods=["GET"])
def get_symbols():
    symbols = alerts_collection.distinct("symbol")
    return jsonify(symbols)


# =========================
# 🔹 DASHBOARD (UNCHANGED)
# =========================
@app.route("/")
def dashboard():
    if test_log:
        log("[DASHBOARD] UI Requested")

    return render_template("dashboard.html")


if __name__ == "__main__":
    if test_log:
        log("🚀 Flask App Started")

    app.run(debug=True)