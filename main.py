import os
from typing import List
import logging

from fastapi import FastAPI, HTTPException
from pydantic.main import BaseModel
from pymongo import MongoClient

from datetime import datetime
from pytz import timezone
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()
client = MongoClient(os.getenv('MONGO_DB_URL'))
# client = MongoClient('checkoutewb-database', 27017)
database = client["auction_db"]
item_collection = database["items"]
bid_collection = database["bids"]
config_collection = database["config"]
logger = logging.getLogger('api')

bidding_enabled = False

# Cross Origin Request Scripting (CORS) is handled here.
origins = [
    "http://localhost",
    "http://localhost:3000",
    "https://auction.ewbumass.org",
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
    additional_images: str = ''
    bid: float
    bid_name: str
    original_bid: float = -1


class AuctionItemList(BaseModel):
    items: List[AuctionItem]


class UserBid(BaseModel):
    first_name: str
    last_name: str
    email: str
    item_name: str
    bid: float


# class BidRequest(BaseModel):
#     first_name: str
#     last_name: str
#     email: str


class FeatureFlag(BaseModel):
    flag: str
    value: bool


@app.on_event('startup')
def startup():
    bidding_enabled_flag = FeatureFlag(**{'flag': 'enable_bidding', 'value': 'true'})
    if not config_collection.find_one({'flag': bidding_enabled_flag.flag}):
        config_collection.insert_one(bidding_enabled_flag.dict())

    global bidding_enabled
    bidding_enabled = config_collection.find_one({'flag': bidding_enabled_flag.flag})['value']


@app.get('/enabled')
def get_bidding_status():
    return "Bidding is Now " + 'Enabled' if bidding_enabled else 'Disabled'


@app.post('/enabled')
def set_bidding_status(enabled: bool, key: str):
    if key != os.getenv('ADMIN_KEY'):
        raise HTTPException(status_code=401, detail='You are not authorized to make this interaction.')
    config_collection.replace_one({'flag': 'enable_bidding'}, {'flag': 'enable_bidding', 'value': enabled})
    global bidding_enabled
    bidding_enabled = enabled
    return "Bidding is Now " + ('Enabled' if enabled else 'Disabled')


@app.get('/items')
def get_all_items():
    return list(item_collection.find({}, {'_id': 0}).sort("name"))


@app.get('/item')
def get_item_by_name(item_name: str):
    db_query = item_collection.find_one({'name': item_name}, {'_id': 0})
    if not db_query:
        return "Can't find item with specified name"

    return db_query


@app.post('/item')
def add_auction_item(auction_item: AuctionItem, key: str):
    if key != os.getenv('ADMIN_KEY'):
        raise HTTPException(status_code=401, detail='You are not authorized to make this interaction.')

    if item_collection.find_one({'name': auction_item.name}):
        return "Item with name already exists"

    item_to_add = auction_item.dict()
    item_to_add['original_bid'] = auction_item.bid
    item_collection.insert_one(item_to_add)
    return 'Successfully added item to database'


@app.post('/items')
def add_auction_items(auction_items: AuctionItemList, key: str):
    if key != os.getenv('ADMIN_KEY'):
        raise HTTPException(status_code=401, detail='You are not authorized to make this interaction.')

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
def remove_auction_item(item_name: str, key: str):
    if key != os.getenv('ADMIN_KEY'):
        raise HTTPException(status_code=401, detail='You are not authorized to make this interaction.')

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


@app.get('/bids/user')
def get_latest_bids(first_name: str, last_name: str):
    all_bids = list(bid_collection.find({'first_name': first_name, 'last_name': last_name},
                                        {'item_name': 1, 'bid': 1, '_id': 0}))

    highest = list(item_collection.find({'bid_name': first_name + ' ' + last_name}, {'name': 1, 'bid': 1, 'bid_name': 1, '_id': 0}))
    bid_names = [bid_item['name'] for bid_item in highest]
    not_highest = []
    for bid in all_bids:
        if bid['item_name'] not in bid_names:
            not_highest.append({
                'name': bid['item_name'],
                'bid': bid['bid']
            })

    return {
        'total': len(highest) + len(not_highest),
        'notHighestItems': not_highest,
        'highestItems': highest
    }


@app.post('/bid')
def place_bid(bid: UserBid):

    if not bidding_enabled:
        return {'status': 'failure', 'detail': 'Bidding is not currently enabled.'}

    if not item_collection.find_one({'name': bid.item_name}):
        return {'status': 'failure', 'detail': 'Item with name does not exist'}

    item = AuctionItem(**item_collection.find_one({'name': bid.item_name}))

    if item.original_bid != item.bid and item.bid_name != 'No bids placed.':  # If not the first bid, additional bidding restrictions
        if bid.bid <= item.bid:
            return {'status': 'failure', 'detail': 'Unable to place bid. The bid amount must be higher than the current price.'}

        if bid.bid - item.bid < 2:  # Enforce minimum bid delta
            return {'status': 'failure', 'detail': 'Unable to place bid. The minimum bid increment is $2.'}
    else:  # If this is first bid, don't enforce delta and make equality < instead of <=
        if bid.bid < item.bid:
            return {'status': 'failure', 'detail': 'Unable to place bid. The bid amount must be not be below the starting bid.'}

    tz = timezone('EST')
    current_time = datetime.now(tz)

    bid_for_db = bid.dict()

    bid_for_db['time_placed'] = str(current_time)

    bid_collection.insert_one(bid_for_db)
    item_collection.update_one({
        'name': item.name}, {
        '$set': {
            'bid': bid.bid,
            'bid_name': bid.first_name + ' ' + bid.last_name
        }
    })

    return {'status': 'success', 'detail': 'Your bid has been placed!'}