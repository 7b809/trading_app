capital = 100000

current_position = None
entry_price = None
quantity = 0

def process_signal(data):
    global current_position, entry_price, quantity, capital

    action = data["action"]
    price = float(data["price"])

    trade_log = None

    if action == "EXIT_BUY" and current_position == "BUY":
        pnl = (price - entry_price) * quantity
        capital += pnl
        trade_log = {"type":"EXIT_BUY","entry_price":entry_price,"exit_price":price,"quantity":quantity,"pnl":pnl,"capital":capital}
        current_position = None

    elif action == "EXIT_SELL" and current_position == "SELL":
        pnl = (entry_price - price) * quantity
        capital += pnl
        trade_log = {"type":"EXIT_SELL","entry_price":entry_price,"exit_price":price,"quantity":quantity,"pnl":pnl,"capital":capital}
        current_position = None

    elif action == "BUY":
        quantity = capital // price
        entry_price = price
        current_position = "BUY"
        trade_log = {"type":"BUY","entry_price":price,"quantity":quantity,"capital":capital}

    elif action == "SELL":
        quantity = capital // price
        entry_price = price
        current_position = "SELL"
        trade_log = {"type":"SELL","entry_price":price,"quantity":quantity,"capital":capital}

    return trade_log
