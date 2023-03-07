import logging
from datetime import datetime
import uuid
from src.database import get_session

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
    is_bidding_enabled,
    set_bidding_enabled,
)
from src.models import (
    ItemInternal,
    SetBiddingMode,
    UserInternal,
    BidCreate,
    BidInternal,
    BidStatusExport,
    BidDeltaResponse,
)
from src.routers.auth_router import is_admin, is_user
from src.settings import settings

bid_router = APIRouter()
logger = logging.Logger("Bids")


@bid_router.get("/enabled")
def get_bidding_status():
    return {"bidding_enabled": is_bidding_enabled()}


@bid_router.post("/enabled")
def set_bidding_status(
    bidding_mode: SetBiddingMode, user: UserInternal = Depends(is_admin)
):
    enabled = bidding_mode.enabled
    set_bidding_enabled(enabled)
    logger.info(
        f"Bidding [{'Enabled' if enabled else 'Disabled'}] by admin [{user.first_name} {user.last_name}]"
    )
    return {"detail": f"Bidding is now [{'Enabled' if enabled else 'Disabled'}]"}


@bid_router.get("/delta", response_model=BidDeltaResponse)
def get_bid_delta():
    return BidDeltaResponse(delta=settings.minimum_bid_increment)


@bid_router.get("/user", response_model=BidStatusExport)
def get_winning_bids(
    user: UserInternal = Depends(is_user), session=Depends(get_session)
):
    """Gets the list of all items in which the current user has bid on."""
    winning_bid_items = []
    losing_bid_items = []

    all_item_ids = (
        session.query(BidInternal)
        .distinct(BidInternal.item_name)
        .filter(BidInternal.email == user.email)
        .all()
    )

    user_items = (
        session.query(ItemInternal)
        .filter(ItemInternal.name.in_([item.item_name for item in all_item_ids]))
        .all()
    )

    for item in user_items:
        if item.winning_bid and item.winning_bid.email == user.email:
            winning_bid_items.append(item)
        else:
            losing_bid_items.append(item)
    return BidStatusExport(winning_bids=winning_bid_items, losing_bids=losing_bid_items)


@bid_router.post("/bid")
def place_bid(
    bid_create: BidCreate,
    user: UserInternal = Depends(is_user),
    session=Depends(get_session),
):

    if not is_bidding_enabled():
        raise bidding_disabled_exception

    bid_item = (
        session.query(ItemInternal)
        .filter(ItemInternal.name == bid_create.item_name)
        .first()
    )

    if not bid_item:
        raise item_not_found_exception

    current_winning_bid_exists = bid_item.winning_bid_id is not None

    if (
        not current_winning_bid_exists
    ):  # If this is first bid, don't enforce delta and make equality < instead of <=
        if bid_create.bid < bid_item.original_bid:
            raise bid_below_starting_exception

    else:  # If not the first bid, additional bidding restrictions
        if bid_create.bid <= bid_item.winning_bid.bid:
            raise bid_below_current_exception

        if (
            bid_create.bid - bid_item.winning_bid.bid < settings.minimum_bid_increment
        ):  # Enforce minimum bid delta
            raise bid_increment_too_small_exception

    tz = timezone("EST")
    current_time = datetime.now(tz)

    bid_for_db = BidInternal(
        item_name=bid_create.item_name,
        item=bid_item,
        bid=bid_create.bid,
        email=user.email,
        time_placed=str(current_time),
    )

    bid_item.winning_bid_id = bid_for_db.id

    session.add(bid_item)
    session.add(bid_for_db)
    session.commit()

    logger.info(
        f"Bid placed on [{bid_item.name}] for [${bid_create.bid}] by [{user.first_name} {user.last_name}, {user.email}]"
    )
    return {"detail": "Your bid has been successfully placed!"}
