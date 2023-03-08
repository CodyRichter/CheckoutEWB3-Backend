import logging
from datetime import timedelta

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from fastapi.requests import Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_login import LoginManager
from fastapi_login.exceptions import InvalidCredentialsException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED
from sqlalchemy.exc import IntegrityError

from src.models import UserInternal, UserCreate, UserExport
from src.settings import settings
from src.database import get_session, session_dep

manager = LoginManager(settings.auth_secret, token_url="/auth/token")

auth_router = APIRouter()

logger = logging.Logger("Authentication")


def hash_password(plaintext: str):
    return manager.pwd_context.hash(plaintext)


def verify_password(plaintext: str, hashed: str):
    return manager.pwd_context.verify(plaintext, hashed)


@manager.user_loader()
def load_user(email: str):
    try:
        session = get_session()
        user = session.query(UserInternal).filter(UserInternal.email == email).first()
    finally:
        session.close()
    return user


def is_user(request: Request):
    raw_user_data = request.state.user
    if request.state.user:
        user = UserInternal.parse_obj(raw_user_data)
        return user

    raise HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="You must be logged in to access this resource.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def is_admin(user: UserInternal = Depends(is_user)):
    if not user.admin:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="You must be an administrator to access this resource.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@auth_router.post("/token")
def login(data: OAuth2PasswordRequestForm = Depends()):
    email = data.username
    user = load_user(email)
    if not user:
        logger.info(f"User [{email}] has unsuccessfully attempted a login.")
        raise InvalidCredentialsException
    elif not verify_password(data.password, user.hashed_password):
        raise InvalidCredentialsException

    access_token = manager.create_access_token(
        data=dict(sub=email), expires=timedelta(days=7)
    )
    logger.info(
        f"User [{user.first_name}, {user.last_name}, {user.email}] has logged in successfully."
    )
    return {"access_token": access_token, "token_type": "bearer"}


@auth_router.post("/register", status_code=201)
def register(user_create: UserCreate, session=Depends(session_dep)):
    user: UserInternal = UserInternal(
        first_name=user_create.first_name,
        last_name=user_create.last_name,
        email=user_create.email,
        hashed_password=hash_password(user_create.password),
        enabled=True,
        admin=False,
    )

    try:
        session.add(user)
        session.commit()
        logger.info(
            f"User [{user.first_name}, {user.last_name}, {user.email}] has registered a new account."
        )
    except IntegrityError:
        logger.info(
            f"User [{user.email}] has failed to register a new account due to email conflict."
        )
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="User with that email address is already registered.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"detail": "New user account successfully created!"}


@auth_router.get("/profile")
def profile(user: UserInternal = Depends(is_user)):
    return UserExport(**user.dict())
