from pydantic import BaseSettings


class Settings(BaseSettings):
    auth_secret: str = "DEVELOPMENT_AUTH_SECRET"
    minimum_bid_increment: float = 2  # Dollars
    AWS_ACCESS_KEY: str
    AWS_SECRET_KEY: str
    AWS_IMAGE_BUCKET_NAME: str = "ewb-auction-images"
    DB_URL: str = "checkoutewb-database"


settings = Settings()
