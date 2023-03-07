from typing import List, Optional

from pydantic.main import BaseModel
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import (
    Column as SAColumn,
    ARRAY as SAArray,
    String as SAString,
)
from sqlalchemy.orm import RelationshipProperty as SARelationshipProperty

# ----- ----- ----- ----- -----
# Tables
# ----- ----- ----- ----- -----


class BidInternal(SQLModel, table=True):
    __tablename__ = "bids"

    id: str = Field(default=None, primary_key=True)
    bid: float = Field(default=None)
    email: str = Field(default=None, index=True)
    time_placed: str = Field(default=None)

    item_name: str = Field(default=None)
    item: "ItemInternal" = Relationship(
        back_populates="winning_bid", sa_relationship_kwargs={"uselist": False}
    )


class ItemInternal(SQLModel, table=True):
    __tablename__ = "items"

    name: str = Field(default=None, primary_key=True)
    description: str = Field(default=None)
    original_bid: float = Field(default=None)
    tags: List[str] = Field(default=None, sa_column=SAColumn("tags", SAArray(SAString)))
    image: str = Field(default=None)
    image_placeholder: Optional[str] = Field(default=None)

    winning_bid_id: Optional[str] = Field(default=None, foreign_key="bids.id")
    winning_bid: Optional[BidInternal] = Relationship(
        back_populates="item", sa_relationship_kwargs={"uselist": False}
    )


class UserInternal(SQLModel, table=True):
    __tablename__ = "users"

    email: str = Field(default=None, index=True, primary_key=True)
    first_name: str = Field(default=None, index=True)
    last_name: str = Field(default=None, index=True)
    hashed_password: str = Field(default=None)
    enabled: bool = Field(default=True)
    admin: bool = Field(default=False)


class FeatureFlag(SQLModel, table=True):
    __tablename__ = "feature_flags"

    flag: str = Field(default=None, primary_key=True)
    value: bool = Field(default=False)


# ----- ----- ----- ----- -----
# Bid Models
# ----- ----- ----- ----- -----


class BidExport(SQLModel, table=False):
    bid: float


class BidCreate(SQLModel, table=False):
    item_name: str
    bid: float


# ----- ----- ----- ----- -----
# Item Models
# ----- ----- ----- ----- -----


class ItemCreate(SQLModel, table=False):
    name: str
    description: str
    original_bid: float
    tags: List[str]
    image: str
    image_placeholder: Optional[str] = ""


class ItemExport(SQLModel, table=False):
    name: str = Field(default=None, primary_key=True, index=True)
    description: str
    original_bid: float
    tags: List[str]
    image: str
    image_placeholder: str
    winning_bid: Optional[BidExport] = None


# ----- ----- ----- ----- -----
# User Models
# ----- ----- ----- ----- -----


class UserCreate(SQLModel, table=False):
    first_name: str
    last_name: str
    email: str
    password: str


class UserExport(SQLModel, table=False):
    first_name: str
    last_name: str
    email: str
    admin: bool


# ----- ----- ----- ----- -----
# General API Response Models
# ----- ----- ----- ----- -----


class ItemList(SQLModel, table=False):
    items: List[ItemExport]


class BidStatusExport(SQLModel, table=False):
    winning_bids: List["ItemExport"]
    losing_bids: List["ItemExport"]


class BidDeltaResponse(SQLModel, table=False):
    delta: float


class SetBiddingMode(SQLModel, table=False):
    enabled: bool


class ProfileResponse(SQLModel, table=False):
    profile: UserExport
