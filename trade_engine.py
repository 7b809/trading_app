positions = {}  # 🔹 NEW (store per symbol)

def process_signal(data):
    symbol = data["symbol"]
    action = data["action"]
    price = float(data["price"])

    # 🔹 create state per symbol (instead of global variables)
    if symbol not in positions:
        positions[symbol] = {
            "capital": 100000,
            "position": None,   # 🔹 CE / PE (updated)
            "entry_price": None,
            "quantity": 0
        }

    state = positions[symbol]
    trade_log = None

    # =========================
    # 🔹 EXIT BUY → CE EXIT
    # =========================
    if action == "EXIT_BUY" and state["position"] == "CE":
        pnl = (price - state["entry_price"]) * state["quantity"]
        state["capital"] += pnl

        trade_log = {
            "type": "CE_EXIT",
            "entry_price": state["entry_price"],
            "exit_price": price,
            "quantity": state["quantity"],
            "pnl": pnl,
            "capital": state["capital"]
        }

        state["position"] = None

    # =========================
    # 🔹 EXIT SELL → PE EXIT
    # =========================
    elif action == "EXIT_SELL" and state["position"] == "PE":
        pnl = (state["entry_price"] - price) * state["quantity"]
        state["capital"] += pnl

        trade_log = {
            "type": "PE_EXIT",
            "entry_price": state["entry_price"],
            "exit_price": price,
            "quantity": state["quantity"],
            "pnl": pnl,
            "capital": state["capital"]
        }

        state["position"] = None

    # =========================
    # 🔹 BUY → CE ENTRY
    # =========================
    elif action == "BUY":
        # 🔹 SAFETY: if PE already open, wait for EXIT_SELL
        if state["position"] == "PE":
            return None

        state["quantity"] = state["capital"] // price
        state["entry_price"] = price
        state["position"] = "CE"

        trade_log = {
            "type": "CE_ENTRY",
            "entry_price": price,
            "quantity": state["quantity"],
            "capital": state["capital"]
        }

    # =========================
    # 🔹 SELL → PE ENTRY
    # =========================
    elif action == "SELL":
        # 🔹 SAFETY: if CE already open, wait for EXIT_BUY
        if state["position"] == "CE":
            return None

        state["quantity"] = state["capital"] // price
        state["entry_price"] = price
        state["position"] = "PE"

        trade_log = {
            "type": "PE_ENTRY",
            "entry_price": price,
            "quantity": state["quantity"],
            "capital": state["capital"]
        }

    return trade_log