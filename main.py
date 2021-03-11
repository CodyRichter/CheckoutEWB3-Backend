from typing import List

from fastapi import FastAPI
from pydantic.main import BaseModel
from pymongo import MongoClient

from datetime import datetime
from pytz import timezone
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()
client = MongoClient('checkoutewb-database', 27017)
database = client["auction_db"]
item_collection = database["items"]  # Create collection for images in database
bid_collection = database["bids"]  # Create collection for images in database


# Cross Origin Request Scripting (CORS) is handled here.
origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuctionItem(BaseModel):
    name: str
    description: str
    tags: List[str]
    image: str
    bid: float
    bid_name: str


class AuctionItemList(BaseModel):
    items: List[AuctionItem]


class UserBid(BaseModel):
    first_name: str
    last_name: str
    email: str
    item_name: str
    bid: float


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get('/items')
def get_all_items():
    return list(item_collection.find({}, {'_id': 0}))


@app.get('/item')
def get_item_by_name(item_name: str):
    db_query = item_collection.find_one({'name': item_name}, {'_id': 0})
    if not db_query:
        return "Can't find item with specified name"

    return db_query


@app.post('/item')
def add_auction_item(auction_item: AuctionItem):
    if item_collection.find_one({'name': auction_item.name}):
        return "Item with name already exists"

    item_to_add = auction_item.dict()
    item_to_add['original_bid'] = auction_item.bid
    item_collection.insert_one(item_to_add)
    return 'Successfully added item to database'


@app.post('/items')
def add_auction_item(auction_items: AuctionItemList):
    count = 0
    for auction_item in list(auction_items.items):
        if item_collection.find_one({'name': auction_item.name}):
            continue

        count += 1
        item_to_add = auction_item.dict()
        item_to_add['original_bid'] = auction_item.bid
        item_collection.insert_one(item_to_add)
        return 'Successfully added ' + str(count) + 'item(s) to database'


@app.delete('/item')
def remove_auction_item(item_name: str):
    if item_collection.find_one({'name': item_name}):
        item_collection.delete_one({'name': item_name})
        return 'Successfully deleted item'

    return 'Could not find item with name ' + item_name + ' to delete.'


@app.get('/bids')
def get_latest_bids():
    latest_bids = list(item_collection.find({}, {'name': 1, 'bid': 1, 'bid_name': 1, '_id': 0}))
    bids = {}
    for bid in latest_bids:
        bids[bid['name']] = {
            'bid': bid['bid'],
            'bid_name':  bid['bid_name']
        }

    return bids


@app.post('/bid')
def place_bid(bid: UserBid):
    if not item_collection.find_one({'name': bid.item_name}):
        return {'status': 'failure', 'detail': 'Item with name does not exist'}

    item = AuctionItem(**item_collection.find_one({'name': bid.item_name}))

    if bid.bid <= item.bid:
        return {'status': 'failure', 'detail': 'Unable to place bid. The bid amount must be higher than the current price.'}

    tz = timezone('EST')
    current_time = datetime.now(tz)

    bid_for_db = bid.dict()

    bid_for_db['time_placed'] = str(current_time)

    bid_collection.insert_one(bid_for_db)
    item.bid = bid.bid
    item.bid_name = bid.first_name + ' ' + bid.last_name
    item_collection.replace_one({'name': item.name}, item.dict())

    return {'status': 'success', 'detail': 'Your bid has been placed!'}