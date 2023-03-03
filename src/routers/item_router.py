import io
import logging
from typing import List, Union

from fastapi import APIRouter, Depends, UploadFile, Form, File
import blurhash


from src.exceptions import (
    item_name_conflict_exception,
    item_not_found_exception,
    item_update_bid_conflict_exception,
)
from src.helpers import item_collection, bid_collection, s3_client
from src.models import AuctionItem, AuctionItemList, User
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


@item_router.get("/items", response_model=AuctionItemList)
def get_all_items():
    db_items = item_collection.find({}, {"_id": 0}).sort("name")
    items = [AuctionItem(**db_item) for db_item in db_items]
    return AuctionItemList(items=items)


@item_router.get("/item", response_model=AuctionItem)
def get_item_by_name(item_name: str):
    db_query = item_collection.find_one({"name": item_name}, {"_id": 0})
    if not db_query:
        raise item_not_found_exception

    return AuctionItem(**db_query)


@item_router.post("/item")
def add_auction_item(
    name: str = Form(...),
    description: str = Form(...),
    bid: float = Form(...),
    tags: List[str] = Form(...),
    image: UploadFile = File(...),
    user: User = Depends(is_admin),
):

    if item_collection.find_one({"name": name}):
        raise item_name_conflict_exception

    item_to_add = {
        "_id": name,
        "name": name,
        "description": description,
        "original_bid": bid,
        "bid": bid,
        "tags": tags,
        "bids_placed": False,
    }

    image_url, image_placeholder = update_item_image(name, image.file)
    item_to_add["image"] = image_url
    item_to_add["image_placeholder"] = image_placeholder

    item_collection.insert_one(item_to_add)

    logger.info(f"Item [{name}] created by admin [{user.first_name} {user.last_name}]")
    return {"detail": "Successfully added item to database"}


@item_router.put("/item")
def update_auction_item(
    name: str = Form(...),
    description: str = Form(...),
    bid: float = Form(...),
    tags: List[str] = Form(...),
    image: Union[UploadFile, None] = None,
    user: User = Depends(is_admin),
):
    existing_item = item_collection.find_one({"name": name})
    if not existing_item:
        raise item_not_found_exception

    new_item = {
        "description": description,
        "bid": bid,
        "tags": tags,
    }

    if new_item["bid"] != existing_item["bid"] and existing_item["bids_placed"]:
        raise item_update_bid_conflict_exception

    if image:
        image_url, image_placeholder = update_item_image(name, image.file)
        new_item["image"] = image_url
        new_item["image_placeholder"] = image_placeholder

    item_collection.update_one(
        {"name": existing_item["name"]},
        {
            "$set": new_item,
        },
    )

    logger.info(f"Item [{name}] updated by admin [{user.first_name} {user.last_name}]")

    return {"detail": "Successfully updated item"}


@item_router.delete("/item")
def remove_auction_item(item_name: str, user: User = Depends(is_admin)):
    if item_collection.find_one({"name": item_name}):
        item_collection.delete_one({"name": item_name})
        bid_collection.delete_many({"item_name": item_name})

        # Delete Image from S3
        s3_client.delete_object(
            Bucket=settings.AWS_IMAGE_BUCKET_NAME, Key=f"{item_name}.jpg"
        )

        logger.info(
            f"Item [{item_name}] deleted by admin [{user.first_name} {user.last_name}]"
        )
        return {"detail": "Successfully deleted item"}

    raise item_not_found_exception
