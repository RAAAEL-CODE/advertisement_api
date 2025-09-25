from fastapi import Form, File, UploadFile, HTTPException, status, APIRouter, Depends
from db import adverts_collection
from bson.objectid import ObjectId
from utils import *
from typing import Annotated
import cloudinary, cloudinary.uploader
from dependencies.authn import is_authenticated
from dependencies.authz import has_roles
import os
from google.genai import types

# Create adverts router
adverts_router = APIRouter()


@adverts_router.get("/adverts", tags=["Adverts"])
def get_all_adverts(
    query="",
    limit=20,
    skip=0,
):
    # Get all adverts from database
    adverts = adverts_collection.find(
        filter={
            "$or": [
                {"title": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}},
                {"category": {"$regex": query, "$options": "i"}},
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
    if not advert:
        raise HTTPException(status_code=404, detail="Advert not found")
    # Return response
    return {"data": replace_mongo_id(advert)}


# Get similar adverts
@adverts_router.get("/adverts/{advert_id}/similar", tags=["Adverts"])
def get_similar_adverts(advert_id, limit=10, skip=0):
    # Check if advert id is valid
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid Advert ID")
    # Get adverts from database by id
    advert = adverts_collection.find_one({"_id": ObjectId(advert_id)})
    # Get similar events from database
    adverts = adverts_collection.find(
        filter={
            "_id": {"$ne": ObjectId(advert_id)},
            "$or": [
                {"title": {"$regex": advert["title"], "$options": "i"}},
                {"description": {"$regex": advert["description"], "$options": "i"}},
                {"category": {"$regex": advert["category"], "$options": "i"}},
            ],
        },
        limit=int(limit),
        skip=int(skip),
    ).to_list()
    # Return response
    return {"data": list(map(replace_mongo_id, adverts))}


# Post Advert (POST): For vendors to create a new advert.
@adverts_router.post(
    "/adverts",
    dependencies=[Depends(has_roles(["Vendor"]))],
    tags=["Vendor"],
)
def create_advert(
    title: Annotated[str, Form()],
    price: Annotated[float, Form()],
    category: Annotated[str, Form()],
    user_id: Annotated[str, Depends(is_authenticated)],
    description: Annotated[str, Form()],
    flyer: Annotated[bytes, File()] = None,
):
    if not flyer:

        # Generate AI image
        response = genai_client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=title,
            config=types.GenerateImagesConfig(
                number_of_images=1,
            ),
        )
        flyer = response.generated_images[0].image.image_bytes

    upload_result = cloudinary.uploader.upload(flyer)
    # Ensure an event with the same title does not exist
    advert_count = adverts_collection.count_documents(
        filter={"$and": [{"title": title}, {"owner": user_id}]}
    )
    if advert_count > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Event with {title} and {user_id} already exists!",
        )

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
    dependencies=[Depends(has_roles(["Vendor"]))],
)
def replace_advert(
    advert_id,
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    user_id: Annotated[str, Depends(is_authenticated)],
    price: Annotated[float, Form()],
    category: Annotated[str, Form()],
    flyer: Annotated[bytes, File()] = None,
):
    # Check if advert id is valid
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid Advert ID")
    if not flyer:

        # Generate AI image
        response = genai_client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=title,
            config=types.GenerateImagesConfig(
                number_of_images=1,
            ),
        )
        flyer = response.generated_images[0].image.image_bytes
    # upload flyer to couldinary
    upload_result = cloudinary.uploader.upload(flyer)
    # Replace event in database
    replace_result = adverts_collection.replace_one(
        filter={"_id": ObjectId(advert_id), "owner": user_id},
        replacement={
            "title": title,
            "description": description,
            "price": price,
            "category": category,
            "flyer": upload_result["secure_url"],
            "owner": user_id,
        },
    )
    if not replace_result.modified_count:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Sorry, No Advert found to replace."
        )
    return {"Message": "Advert replaced Successfully."}


# Delete Advert (DELETE):  For vendors to remove an advert.
@adverts_router.delete(
    "/adverts/{advert_id}",
    tags=["Vendor"],
    dependencies=[Depends(is_authenticated), Depends(has_roles(["Vendor"]))],
)
def delete_advert_by_id(advert_id, user_id: Annotated[str, Depends(is_authenticated)]):
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid Advert ID")
    # Delete advert from database
    delete_result = adverts_collection.delete_one(
        filter={"_id": ObjectId(advert_id), "owner": user_id}
    )
    if not delete_result.deleted_count:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Sorry, No Advert found to delete."
        )
    return {"message": "Advert deleted successfully"}


@adverts_router.get(
    "/adverts/user/me", tags=["Vendor"], dependencies=[Depends(has_roles(["Vendor"]))]
)
def get_my_adverts(user_id: Annotated[str, Depends(is_authenticated)]):
    adverts = adverts_collection.find(filter={"owner": user_id}).to_list()
    return {"data": list(map(replace_mongo_id, adverts))}
