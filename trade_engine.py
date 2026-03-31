positions = {}  # 🔹 NEW (store per symbol)

def process_signal(data):
    symbol = data["symbol"]
    action = data["action"]
    price = float(data["price"])

    # 🔹 create state per symbol (instead of global variables)
    if symbol not in positions:
        positions[symbol] = {
            "capital": 100000,
            "position": None,
            "entry_price": None,
            "quantity": 0
        }

    state = positions[symbol]
    trade_log = None

    # EXIT BUY
    if action == "EXIT_BUY" and state["position"] == "BUY":
        pnl = (price - state["entry_price"]) * state["quantity"]
        state["capital"] += pnl

        trade_log = {
            "type": "EXIT_BUY",
            "entry_price": state["entry_price"],
            "exit_price": price,
            "quantity": state["quantity"],
            "pnl": pnl,
            "capital": state["capital"]
        }

        state["position"] = None

    # EXIT SELL
    elif action == "EXIT_SELL" and state["position"] == "SELL":
        pnl = (state["entry_price"] - price) * state["quantity"]
        state["capital"] += pnl

        trade_log = {
            "type": "EXIT_SELL",
            "entry_price": state["entry_price"],
            "exit_price": price,
            "quantity": state["quantity"],
            "pnl": pnl,
            "capital": state["capital"]
        }

        state["position"] = None

    # BUY
    elif action == "BUY":
        state["quantity"] = state["capital"] // price
        state["entry_price"] = price
        state["position"] = "BUY"

        trade_log = {
            "type": "BUY",
            "entry_price": price,
            "quantity": state["quantity"],
            "capital": state["capital"]
        }

    # SELL
    elif action == "SELL":
        state["quantity"] = state["capital"] // price
        state["entry_price"] = price
        state["position"] = "SELL"

        trade_log = {
            "type": "SELL",
            "entry_price": price,
            "quantity": state["quantity"],
            "capital": state["capital"]
        }

    return trade_log