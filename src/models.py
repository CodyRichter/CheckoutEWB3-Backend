from typing import List, Optional

from pydantic.main import BaseModel


class AuctionItem(BaseModel):
    name: str
    description: str
    bid: float
    tags: List[str]
    image: str
    image_placeholder: Optional[str] = ""
    bids_placed: bool = False


class AuctionItemInternal(AuctionItem):
    original_bid: float = -1
    bid_email: str = ""


class AuctionItemList(BaseModel):
    items: List[AuctionItem]


class UserBidStatus(BaseModel):
    winning_bids: List[AuctionItem]
    losing_bids: List[AuctionItem]


class UserBidCreate(BaseModel):
    item_name: str
    bid: float


class UserBidInternal(UserBidCreate):
    email: str
    time_placed: str


class FeatureFlag(BaseModel):
    flag: str
    value: bool


class BidDeltaResponse(BaseModel):
    delta: float


class SetBiddingMode(BaseModel):
    enabled: bool


class User(BaseModel):
    first_name: str
    last_name: str
    email: str
    hashed_password: str
    enabled: bool
    admin: bool


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str


class UserExport(BaseModel):
    first_name: str
    last_name: str
    email: str
    admin: bool


class ProfileResponse(BaseModel):
    profile: UserExport
