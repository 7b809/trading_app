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
# 🔥 ROUTE → SYMBOL MAPPING
# =========================
WEBHOOK_CONFIG = {
    "1": "nifty",
    "2": "gift_nifty",
    "3": "bitcoin"
}


# =========================
# 🔹 PARSE NEW ALERT FORMAT
# =========================
def parse_new_alert(raw_msg):
    mapping = {
        "pe_exit_ce_entry": ["EXIT_SELL", "BUY"],
        "ce_exit_pe_entry": ["EXIT_BUY", "SELL"]
    }
    return mapping.get(str(raw_msg).lower())


# =========================
# 🔹 TIME WINDOW (UNCHANGED)
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
# 🔥 ROBUST WEBHOOK
# =========================
@app.route("/webhook/<route_id>", methods=["POST"])
def webhook(route_id):

    try:
        # =========================
        # 🔹 SAFE INPUT PARSING (JSON + TEXT)
        # =========================
        if request.is_json:
            data = request.get_json()
        else:
            raw_text = request.get_data(as_text=True)

            data = {
                "message": raw_text.strip(),
                "symbol": None,
                "price": 0
            }

        raw_message = data.get("message")

        # =========================
        # 🔹 SYMBOL MAPPING
        # =========================
        mapped_symbol = WEBHOOK_CONFIG.get(str(route_id))
        symbol = mapped_symbol if mapped_symbol else data.get("symbol")

        price = float(data.get("price", 0) or 0)

        # 🔹 CURRENT IST TIME
        now_ist = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

        parsed_actions = parse_new_alert(raw_message)

        trade = None

        # =========================
        # 🔹 PROCESS TRADE
        # =========================
        if parsed_actions:
            for action in parsed_actions:
                temp_data = {
                    "symbol": symbol,
                    "action": action,
                    "price": price
                }

                try:
                    trade = process_signal(temp_data)
                except Exception as e:
                    log(f"[TRADE ERROR] {e}")
                    trade = None

                if trade:
                    trade["symbol"] = symbol
                    trade["datetime"] = now_ist
                    trade["route"] = route_id

                    if "CE" in trade["type"]:
                        temp_data["option_type"] = "CE"
                    elif "PE" in trade["type"]:
                        temp_data["option_type"] = "PE"

                    in_time = is_within_time_window(now_ist)

                    try:
                        if in_time:
                            trades_collection.insert_one(trade)
                        else:
                            trades_offtime_collection.insert_one(trade)
                    except Exception as e:
                        log(f"[DB TRADE ERROR] {e}")

        else:
            # =========================
            # 🔹 FALLBACK OLD LOGIC
            # =========================
            data["symbol"] = symbol

            try:
                trade = process_signal(data)
            except Exception as e:
                log(f"[TRADE ERROR] {e}")
                trade = None

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
                trade["symbol"] = symbol
                trade["datetime"] = data.get("datetime")
                trade["route"] = route_id

                try:
                    if in_time:
                        trades_collection.insert_one(trade)
                    else:
                        trades_offtime_collection.insert_one(trade)
                except Exception as e:
                    log(f"[DB TRADE ERROR] {e}")

        # =========================
        # 🔹 ALWAYS SAVE ALERT (FAIL-SAFE)
        # =========================
        alert_doc = data.copy()

        alert_doc["message"] = raw_message
        alert_doc["route"] = route_id
        alert_doc["symbol"] = symbol
        alert_doc["datetime"] = now_ist

        in_time_alert = is_within_time_window(now_ist)

        try:
            if in_time_alert:
                alerts_collection.insert_one(alert_doc)
            else:
                alerts_offtime_collection.insert_one(alert_doc)
        except Exception as e:
            log(f"[DB ALERT ERROR] {e}")

        return jsonify({"status": "success"})

    except Exception as e:
        # 🔥 FINAL SAFETY NET
        log(f"[WEBHOOK CRASH] {e}")

        # Try saving raw request at least
        try:
            raw_text = request.get_data(as_text=True)

            fallback_doc = {
                "message": raw_text,
                "route": route_id,
                "datetime": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
                "error": str(e)
            }

            alerts_collection.insert_one(fallback_doc)
        except Exception:
            pass

        return jsonify({"status": "error", "msg": str(e)}), 200


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

    alerts = list(
        alerts_collection.find(query, {"_id": 0})
        .sort("datetime", -1)
        .limit(limit)
    )

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

    trades = list(
        trades_collection.find(query, {"_id": 0})
        .sort("datetime", -1)
        .limit(limit)
    )

    return jsonify(trades)


@app.route("/symbols", methods=["GET"])
def get_symbols():
    symbols = alerts_collection.distinct("symbol")
    return jsonify(symbols)


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


if __name__ == "__main__":
    app.run(debug=True)