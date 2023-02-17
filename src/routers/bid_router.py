import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from pytz import timezone

from src.exceptions import (
    bid_below_current_exception,
    bid_below_starting_exception,
    bid_increment_too_small_exception,
    bidding_disabled_exception,
    item_not_found_exception,
)
from src.helpers import (
    bid_collection,
    is_bidding_enabled,
    item_collection,
    set_bidding_enabled,
)
from src.models import (
    AuctionItem,
    AuctionItemInternal,
    SetBiddingMode,
    User,
    UserBidCreate,
    UserBidInternal,
    UserBidStatus,
)
from src.routers.auth_router import is_admin, is_user
from src.settings import settings

bid_router = APIRouter()
logger = logging.Logger("Bids")


@bid_router.get("/enabled")
def get_bidding_status():
    return {"bidding_enabled": is_bidding_enabled()}


@bid_router.post("/enabled")
def set_bidding_status(bidding_mode: SetBiddingMode, user: User = Depends(is_admin)):
    enabled = bidding_mode.enabled
    set_bidding_enabled(enabled)
    logger.info(
        f"Bidding [{'Enabled' if enabled else 'Disabled'}] by admin [{user.first_name} {user.last_name}]"
    )
    return {"detail": f"Bidding is now [{'Enabled' if enabled else 'Disabled'}]"}


@bid_router.get("/user", response_model=UserBidStatus)
def get_winning_bids(user: User = Depends(is_user)):
    """Gets the list of all items in which the current user is winning the bid."""

    winning_bid_items = item_collection.find(
        {"bid_email": user.email}, {"_id": 0}
    ).sort("name")
    winning_items = [AuctionItem(**db_item) for db_item in winning_bid_items]
    winning_item_names = [db_item["name"] for db_item in winning_bid_items]

    user_bid_item_names = bid_collection.distinct("item_name", {"email": user.email})
    losing_item_names = [i for i in user_bid_item_names if i not in winning_item_names]

    logger.warning(user_bid_item_names)

    losing_bid_items = item_collection.find(
        {"name": {"$in": losing_item_names}}, {"_id": 0}
    ).sort("name")
    losing_items = [AuctionItem(**db_item) for db_item in losing_bid_items]
    return UserBidStatus(winning_bids=winning_items, losing_bids=losing_items)


@bid_router.post("/bid")
def place_bid(bid: UserBidCreate, user: User = Depends(is_user)):

    if not is_bidding_enabled():
        raise bidding_disabled_exception

    if not item_collection.find_one({"name": bid.item_name}):
        raise item_not_found_exception

    item = AuctionItemInternal(**item_collection.find_one({"name": bid.item_name}))

    try:  # If bid collection not made yet, we must catch TypeError
        no_bids_yet = len(bid_collection.find_one({"item_name": bid.item_name})) <= 0
    except TypeError:
        no_bids_yet = True

    if (
        no_bids_yet
    ):  # If this is first bid, don't enforce delta and make equality < instead of <=
        if bid.bid < item.bid:
            raise bid_below_starting_exception

    else:  # If not the first bid, additional bidding restrictions
        if bid.bid <= item.bid:
            raise bid_below_current_exception

        if (
            bid.bid - item.bid < settings.minimum_bid_increment
        ):  # Enforce minimum bid delta
            raise bid_increment_too_small_exception

    tz = timezone("EST")
    current_time = datetime.now(tz)

    bid_for_db = UserBidInternal(
        item_name=bid.item_name,
        bid=bid.bid,
        email=user.email,
        time_placed=str(current_time),
    )

    bid_collection.insert_one(bid_for_db.dict())
    item_collection.update_one(
        {"name": item.name},
        {"$set": {"bid": bid.bid, "bid_email": user.email}},
    )

    logger.info(
        f"Bid placed on [{item.name}] for [${bid.bid}] by [{user.first_name} {user.last_name}, {user.email}]"
    )
    return {"detail": "Your bid has been successfully placed!"}
