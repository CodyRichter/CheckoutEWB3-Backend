import logging

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from src.helpers import config_collection
from src.models import FeatureFlag
from src.routers.auth_router import auth_router, manager
from src.routers.bid_router import bid_router
from src.routers.item_router import item_router

logger = logging.Logger("Main")

app = FastAPI()

app.include_router(
    item_router,
    prefix="/items",
    tags=["items"],
    responses={404: {"detail": "Not found"}},
)

app.include_router(
    auth_router,
    prefix="/auth",
    tags=["auth"],
    responses={404: {"detail": "Not found"}},
)

app.include_router(
    bid_router,
    prefix="/bids",
    tags=["bids"],
    responses={404: {"detail": "Not found"}},
)

manager.useRequest(app)

logger = logging.getLogger("api")

# Cross Origin Request Scripting (CORS) is handled here.
# origins = [
#     "http://localhost",
#     "http://localhost:3000",
#     "https://auction.ewbumass.org",
# ]

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_headers=["*"],
    allow_methods=["*"],
)


@app.on_event("startup")
def startup():
    bidding_enabled_flag = FeatureFlag(**{"flag": "enable_bidding", "value": False})
    if not config_collection.find_one({"flag": bidding_enabled_flag.flag}):
        config_collection.insert_one(bidding_enabled_flag.dict())


@app.get("/")
def healthcheck():
    return "Checkout EWB Backend is Running!"
