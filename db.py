from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load .env
load_dotenv()

# Read from env
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
ALERTS_COLLECTION = os.getenv("ALERTS_COLLECTION")
TRADES_COLLECTION = os.getenv("TRADES_COLLECTION")

# Mongo connection
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

alerts_collection = db[ALERTS_COLLECTION]
trades_collection = db[TRADES_COLLECTION]

OFFTIME_ALERTS_COLLECTION = os.getenv("OFFTIME_ALERTS_COLLECTION")
OFFTIME_TRADES_COLLECTION = os.getenv("OFFTIME_TRADES_COLLECTION")

alerts_offtime_collection = db[OFFTIME_ALERTS_COLLECTION]
trades_offtime_collection = db[OFFTIME_TRADES_COLLECTION]