import boto3
from src.models import FeatureFlag
from src.database import session_dep
from src.settings import settings

s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY,
    aws_secret_access_key=settings.AWS_SECRET_KEY,
)


def set_bidding_enabled(result: bool) -> None:
    with session_dep() as session:
        db_result = (
            session.query(FeatureFlag)
            .filter(FeatureFlag.flag == "enable_bidding")
            .first()
        )
        if db_result:
            db_result.value = result
            session.commit()
        else:
            raise Exception("Bidding feature flag not found")


def is_bidding_enabled() -> bool:
    with session_dep() as session:
        db_result = (
            session.query(FeatureFlag)
            .filter(FeatureFlag.flag == "enable_bidding")
            .first()
        )
        return db_result and db_result.value
