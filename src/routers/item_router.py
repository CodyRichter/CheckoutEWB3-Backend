import io
import logging
from typing import List, Union
from src.database import session_dep

from fastapi import APIRouter, Depends, UploadFile, Form, File
import blurhash


from src.exceptions import (
    item_name_conflict_exception,
    item_not_found_exception,
    item_update_bid_conflict_exception,
)
from src.helpers import s3_client
from src.models import (
    BidInternal,
    ItemInternal,
    ItemExport,
    ItemInternal,
    ItemList,
    UserInternal,
    UserInternal,
)
from src.routers.auth_router import is_admin
from src.settings import settings
from PIL import Image
from PIL.ImageOps import exif_transpose

item_router = APIRouter()
logger = logging.Logger("Items")


def update_item_image(item_name: str, image_file: str):

    # Downscale Image
    raw_image = Image.open(image_file)
    file_extension = raw_image.format
    image = exif_transpose(raw_image)
    image.thumbnail((512, 512), Image.ANTIALIAS)

    compressed_image_file = io.BytesIO()
    image.save(compressed_image_file, format=file_extension)
    compressed_image_file.seek(0)

    # Blurhash Image Thumbnail
    image_placeholder = blurhash.encode(compressed_image_file, 4, 3)
    compressed_image_file.seek(0)

    # Upload Image to S3
    s3_client.upload_fileobj(
        compressed_image_file,
        settings.AWS_IMAGE_BUCKET_NAME,
        f"{item_name}.{file_extension}",
        ExtraArgs={"ContentType": "image/jpeg"},
    )

    # Generate Image URL
    image_url = f"https://{settings.AWS_IMAGE_BUCKET_NAME}.s3.us-east-1.amazonaws.com/{item_name}.{file_extension}"
    return image_url, image_placeholder


@item_router.get("/items", response_model=ItemList)
def get_all_items(session=Depends(session_dep)):
    db_items = session.query(ItemInternal).order_by(ItemInternal.name).all()
    return ItemList(items=db_items)


@item_router.get("/item", response_model=ItemExport)
def get_item_by_name(item_name: str, session=Depends(session_dep)):
    db_item = session.query(ItemInternal).filter(ItemInternal.name == item_name).first()
    if not db_item:
        raise item_not_found_exception

    return db_item


@item_router.post("/item")
def add_auction_item(
    name: str = Form(...),
    description: str = Form(...),
    bid: float = Form(...),
    tags: List[str] = Form(...),
    image: UploadFile = File(...),
    user: UserInternal = Depends(is_admin),
    session=Depends(session_dep),
):

    if session.query(ItemInternal).filter_by(name=name).first():
        raise item_name_conflict_exception

    image_url, image_placeholder = update_item_image(name, image.file)

    item_to_add = ItemInternal(
        name=name,
        description=description,
        original_bid=bid,
        tags=tags,
        image=image_url,
        image_placeholder=image_placeholder,
    )

    session.add(item_to_add)
    session.commit()

    logger.info(f"Item [{name}] created by admin [{user.first_name} {user.last_name}]")
    return {"detail": "Successfully added item to database"}


@item_router.put("/item")
def update_auction_item(
    name: str = Form(...),
    description: str = Form(...),
    bid: float = Form(...),
    tags: List[str] = Form(...),
    image: Union[UploadFile, None] = None,
    user: UserInternal = Depends(is_admin),
    session=Depends(session_dep),
):
    existing_item: ItemInternal = (
        session.query(ItemInternal).filter_by(name=name).first()
    )
    if not existing_item:
        raise item_not_found_exception

    # If the item has a winning bid, the original bid cannot be changed
    if existing_item.winning_bid and bid != existing_item.original_bid:
        raise item_update_bid_conflict_exception

    if image:
        image_url, image_placeholder = update_item_image(name, image.file)
        existing_item.image = image_url
        existing_item.image_placeholder = image_placeholder

    existing_item.description = description
    existing_item.original_bid = bid
    existing_item.tags = tags

    session.commit()

    logger.info(f"Item [{name}] updated by admin [{user.first_name} {user.last_name}]")

    return {"detail": "Successfully updated item"}


@item_router.delete("/item")
def remove_auction_item(
    item_name: str, user: UserInternal = Depends(is_admin), session=Depends(session_dep)
):

    item = session.query(ItemInternal).filter_by(name=item_name).first()
    if not item:
        raise item_not_found_exception

    item_bids = session.query(BidInternal).filter_by(item_name=item_name).all()
    for bid in item_bids:
        session.delete(bid)

    session.delete(item)
    session.commit()

    s3_client.delete_object(
        Bucket=settings.AWS_IMAGE_BUCKET_NAME, Key=f"{item_name}.jpg"
    )

    logger.info(
        f"Item [{item_name}] deleted by admin [{user.first_name} {user.last_name}]"
    )

    return {"detail": "Successfully deleted item"}
