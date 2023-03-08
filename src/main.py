import logging

from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from src.database import create_db, get_session, session_dep
from src.models import FeatureFlag
from src.routers.auth_router import auth_router, manager
from src.routers.bid_router import bid_router
from src.routers.item_router import item_router
import sqlalchemy

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
def startup(session=Depends(session_dep)):

    create_db()

    session = get_session()
    try:
        bidding_enabled_flag = FeatureFlag(**{"flag": "enable_bidding", "value": False})

        flag_exists = (
            session.query(FeatureFlag)
            .filter(FeatureFlag.flag == bidding_enabled_flag.flag)
            .first()
        )

        if not flag_exists:
            session.add(bidding_enabled_flag)
            session.commit()
    finally:
        session.close()


@app.get("/")
def healthcheck():
    return "Checkout EWB Backend is Running!"


@app.exception_handler(sqlalchemy.exc.OperationalError)
async def validation_exception_handler(request, err):
    logger.error(f"Database connection error on {request.url}: {err}")

    return JSONResponse(
        status_code=503,
        content={
            "detail": "Server is currently unable to handle the request. Please try again later. Error code: 503-DBTMC"
        },
    )
