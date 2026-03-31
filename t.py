from db import alerts_collection

for doc in alerts_collection.find():
    action = doc.get("action")

    if action in ["BUY", "EXIT_BUY"]:
        option_type = "CE"
    elif action in ["SELL", "EXIT_SELL"]:
        option_type = "PE"
    else:
        continue

    alerts_collection.update_one(
        {"_id": doc["_id"]},
        {"$set": {"option_type": option_type}}
    )