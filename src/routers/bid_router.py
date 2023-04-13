import logging
from datetime import datetime
import uuid
from src.database import session_dep

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
    WinningBidExport,
    WinningBidsResponse,
)
from src.routers.auth_router import is_admin, is_user
from src.settings import settings

bid_router = APIRouter()
logger = logging.Logger("Bids")


@bid_router.get("/enabled")
def get_bidding_status(session=Depends(session_dep)):
    return {"bidding_enabled": is_bidding_enabled(session)}


@bid_router.post("/enabled")
def set_bidding_status(
    bidding_mode: SetBiddingMode,
    user: UserInternal = Depends(is_admin),
    session=Depends(session_dep),
):
    enabled = bidding_mode.enabled
    set_bidding_enabled(enabled, session)
    logger.info(
        f"Bidding [{'Enabled' if enabled else 'Disabled'}] by admin [{user.first_name} {user.last_name}]"
    )
    return {"detail": f"Bidding is now [{'Enabled' if enabled else 'Disabled'}]"}


@bid_router.get("/delta", response_model=BidDeltaResponse)
def get_bid_delta():
    return BidDeltaResponse(delta=settings.minimum_bid_increment)


@bid_router.get("/user", response_model=BidStatusExport)
def get_winning_bids(
    user: UserInternal = Depends(is_user), session=Depends(session_dep)
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
    session=Depends(session_dep),
):

    if not is_bidding_enabled(session):
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
        id=str(uuid.uuid4()),
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


@bid_router.get("/winner", response_model=WinningBidsResponse)
def get_winning_bids(
    user: UserInternal = Depends(is_admin),
    session=Depends(session_dep),
):
    # TODO: Return winning bids for all users

    # Get winning bids
    winning_bids_query = (
        session.query(BidInternal, UserInternal)
        .filter(BidInternal.id.in_(session.query(ItemInternal.winning_bid_id)))
        .filter(BidInternal.email == UserInternal.email)
        .all()
    )

    winning_bids = []

    for row in winning_bids_query:
        winning_bids.append(
            WinningBidExport(
                item_name=row.BidInternal.item_name,
                winning_bid=row.BidInternal.bid,
                email=row.BidInternal.email,
                first_name=row.UserInternal.first_name,
                last_name=row.UserInternal.last_name,
            )
        )

    return WinningBidsResponse(winning_bids=winning_bids)
