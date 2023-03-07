from pydantic import BaseSettings


class Settings(BaseSettings):
    auth_secret: str = "DEVELOPMENT_AUTH_SECRET"
    minimum_bid_increment: float = 2  # Dollars
    AWS_ACCESS_KEY: str
    AWS_SECRET_KEY: str
    AWS_IMAGE_BUCKET_NAME: str = "ewb-auction-images"
    AUTHENTICATION_POSTGRES_USER: str = "postgres"
    AUTHENTICATION_POSTGRES_PASSWORD: str = "password"
    AUTHENTICATION_POSTGRES_HOST: str = "checkoutewb-database"
    AUTHENTICATION_POSTGRES_PORT: str = "5432"
    AUTHENTICATION_POSTGRES_DB: str = "auction_db"


settings = Settings()
