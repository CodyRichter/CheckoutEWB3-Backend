import logging

from fastapi import APIRouter, Depends

from src.exceptions import item_name_conflict_exception, item_not_found_exception
from src.helpers import item_collection
from src.models import AuctionItem, AuctionItemList, User
from src.routers.auth_router import is_admin

item_router = APIRouter()
logger = logging.Logger("Items")


@item_router.get("/items", response_model=AuctionItemList)
def get_all_items():
    db_items = item_collection.find({}, {"_id": 0}).sort("name")
    items = [AuctionItem(**db_item) for db_item in db_items]
    return AuctionItemList(items=items)


@item_router.get("/item", response_model=AuctionItem)
def get_item_by_name(item_name: str):
    db_query = item_collection.find_one({"name": item_name}, {"_id": 0})
    if not db_query:
        raise item_not_found_exception

    return AuctionItem(**db_query)


@item_router.post("/item")
def add_auction_item(auction_item: AuctionItem, user: User = Depends(is_admin)):

    if item_collection.find_one({"name": auction_item.name}):
        raise item_name_conflict_exception

    item_to_add = auction_item.dict()
    item_to_add["original_bid"] = auction_item.bid
    item_to_add["_id"] = auction_item.name
    item_collection.insert_one(item_to_add)

    logger.info(
        f"Item [{auction_item.name}] created by admin [{user.first_name} {user.last_name}]"
    )
    return {"detail": "Successfully added item to database"}


@item_router.post("/items")
def add_auction_items(auction_items: AuctionItemList, user: User = Depends(is_admin)):
    count = 0
    for auction_item in list(auction_items.items):
        if item_collection.find_one({"name": auction_item.name}):
            logger.warn(
                f"Attempted create of [{auction_item.name}] by admin [{user.first_name} {user.last_name}] failed due to item name conflict"
            )
            continue

        count += 1
        item_to_add = auction_item.dict()
        item_to_add["original_bid"] = auction_item.bid
        item_to_add["_id"] = auction_item.name
        item_collection.insert_one(item_to_add)

    logger.info(
        f"Item(s) [{','.join([ai.name for ai in auction_items.items])}] created by admin [{user.first_name} {user.last_name}]"
    )
    return {"detail": f"Successfully added {str(count)} item(s) to database"}


@item_router.delete("/item")
def remove_auction_item(item_name: str, user: User = Depends(is_admin)):
    if item_collection.find_one({"name": item_name}):
        item_collection.delete_one({"name": item_name})
        logger.info(
            f"Item [{item_name}] deleted by admin [{user.first_name} {user.last_name}]"
        )
        return {"detail": "Successfully deleted item"}

    raise item_not_found_exception
