import logging

from fastapi import FastAPI, Depends
from starlette.middleware.cors import CORSMiddleware

from src.database import create_db, session_dep
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

    create_db()

    with session_dep() as session:
        bidding_enabled_flag = FeatureFlag(**{"flag": "enable_bidding", "value": False})

        flag_exists = (
            session.query(FeatureFlag)
            .filter(FeatureFlag.flag == bidding_enabled_flag.flag)
            .first()
        )

        if not flag_exists:
            session.add(bidding_enabled_flag)
            session.commit()


@app.get("/")
def healthcheck():
    return "Checkout EWB Backend is Running!"
