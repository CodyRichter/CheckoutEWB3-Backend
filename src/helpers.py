import os

from pymongo import MongoClient

if os.getenv("MONGO_DB_URL"):
    client = MongoClient(os.getenv("MONGO_DB_URL"))
else:
    client = MongoClient("checkoutewb-database", 27017)

database = client["auction_db"]
item_collection = database["items"]
bid_collection = database["bids"]
config_collection = database["config"]
user_collection = database["users"]


def set_bidding_enabled(result: bool) -> None:
    config_collection.replace_one(
        {"flag": "enable_bidding"}, {"flag": "enable_bidding", "value": result}
    )


def is_bidding_enabled() -> bool:
    db_result = config_collection.find_one({"flag": "enable_bidding"}, {"_id": 0})
    return db_result and db_result["value"]
