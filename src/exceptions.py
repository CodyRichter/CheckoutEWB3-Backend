from fastapi import HTTPException
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from src.settings import settings

bidding_disabled_exception = HTTPException(
    status_code=HTTP_403_FORBIDDEN,
    detail="Bidding is currently disabled.",
)

item_not_found_exception = HTTPException(
    status_code=HTTP_404_NOT_FOUND,
    detail="Unable to find auction item with provided name.",
)

item_name_conflict_exception = HTTPException(
    status_code=HTTP_409_CONFLICT,
    detail="Auction item with given name already exists.",
)

item_update_bid_conflict_exception = HTTPException(
    status_code=HTTP_409_CONFLICT,
    detail="Unable to update auction item. You may not change the bid amount if bids have already been placed.",
)

bid_increment_too_small_exception = HTTPException(
    status_code=HTTP_400_BAD_REQUEST,
    detail=f"Unable to place bid. The minimum bid increment is ${settings.minimum_bid_increment}.",
)

bid_below_current_exception = HTTPException(
    status_code=HTTP_400_BAD_REQUEST,
    detail="Unable to place bid. Your bid amount must be above the current bid.",
)

bid_below_starting_exception = HTTPException(
    status_code=HTTP_400_BAD_REQUEST,
    detail="Unable to place bid. The bid amount must be above the starting bid.",
)
