from fastapi import Form, File, UploadFile, HTTPException, status, APIRouter, Depends
from db import adverts_collection
from bson.objectid import ObjectId
from utils import replace_mongo_id
from typing import Annotated
import cloudinary, cloudinary.uploader
from dependencies.authn import is_authenticated
from dependencies.authz import has_roles

# Create adverts router
adverts_router = APIRouter()


@adverts_router.get("/adverts", tags=["Adverts"])
def get_all_adverts(title="", description="", limit=20, skip=0):
    # Get all adverts from database
    adverts = adverts_collection.find(
        filter={
            "$or": [
                {"title": {"$regex": title, "$options": "i"}},
                {"description": {"$regex": description, "$options": "i"}},
            ]
        },
        limit=int(limit),
        skip=int(skip),
    ).to_list()
    # Return response
    return {"data": list(map(replace_mongo_id, adverts))}


# Get Advert Details (GET): For vendors to view a specific advert’s details.
@adverts_router.get("/adverts/{advert_id}", tags=["Adverts"])
def get_adverts_by_id(advert_id):
    # Check if advert id is valid
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid Advert ID")
    # Get adverts from database by id
    advert = adverts_collection.find_one({"_id": ObjectId(advert_id)})
    # Return response
    return {"data": replace_mongo_id(advert)}


# Post Advert (POST): For vendors to create a new advert.
@adverts_router.post(
    "/adverts", dependencies=[Depends(has_roles(["vendor"]))], tags=["Vendor"]
)
def create_advert(
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    price: Annotated[float, Form()],
    category: Annotated[str, Form()],
    flyer: Annotated[UploadFile, File()],
    user_id: Annotated[str, Depends(is_authenticated)],
):
    # Ensure an event with the same title does not exist
    advert_count = adverts_collection.count_documents(
        filter={"$and": [{"title": title}, {"owner": user_id}]}
    )
    if advert_count > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Event with {title} and {user_id} already exists!",
        )
    upload_result = cloudinary.uploader.upload(flyer.file)

    adverts_collection.insert_one(
        {
            "title": title,
            "price": price,
            "description": description,
            "category": category,
            "flyer": upload_result["secure_url"],
            "owner": user_id,
        }
    )
    return {"Message": "Advert added successfully."}


# Update Advert (PUT): For vendors to edit an advert
@adverts_router.put(
    "/adverts/{advert_id}",
    tags=["Vendor"],
    dependencies=[Depends(has_roles(["vendor"]))],
)
def replace_advert(
    advert_id,
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    price: Annotated[float, Form()],
    category: Annotated[str, Form()],
    flyer: Annotated[UploadFile, File()],
):
    # Check if advert id is valid
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid Advert ID")

    # upload flyer to couldinary
    upload_result = cloudinary.uploader.upload(flyer.file)
    # Replace event in database
    adverts_collection.replace_one(
        filter={"_id": ObjectId(advert_id)},
        replacement={
            "title": title,
            "description": description,
            "price": price,
            "category": category,
            "flyer": upload_result["secure_url"],
        },
    )
    return {"Message": "Advert replaced Successfully."}


# Delete Advert (DELETE):  For vendors to remove an advert.
@adverts_router.delete(
    "/adverts/{advert_id}",
    tags=["Vendor"],
    dependencies=[Depends(has_roles(["vendor"]))],
)
def delete_advert_by_id(advert_id):
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid Advert ID")
    # Delete advert from database
    delete_result = adverts_collection.delete_one(filter={"_id": ObjectId(advert_id)})
    if not delete_result.deleted_count:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Sorry, No Advert found to delete."
        )
    return {"message": "Advert deleted successfully"}
