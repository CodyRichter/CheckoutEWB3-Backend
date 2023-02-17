from pydantic import BaseSettings


class Settings(BaseSettings):
    auth_secret: str = "DEVELOPMENT_AUTH_SECRET"
    minimum_bid_increment: float = 2  # Dollars


settings = Settings()
