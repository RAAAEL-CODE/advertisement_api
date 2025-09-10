from fastapi import FastAPI, Form, File, UploadFile, HTTPException, status
from db import adverts_collection
from pydantic import BaseModel
from bson.objectid import ObjectId
from utils import replace_mongo_id
from typing import Annotated
import cloudinary, cloudinary.uploader

# Configure cloudinary
cloudinary.config(
    cloud_name="dyf9h2cb0",
    api_key="526419166373937",
    api_secret="5MXfLxNArpPFrLy1M5RFxdzkypg",
)


class AdvertModel(BaseModel):
    title: str
    description: str
    price: float
    category: str

app = FastAPI()


# Home page
@app.get("/")
def read_root():
    return {"message": "Welcome to RAAAEL Advertisement API"}


# Post Advert (POST): For vendors to create a new advert.
@app.post("/adverts")
def create_advert(
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    price: Annotated[float, Form()],
    category: Annotated[str, Form()],
    flyer: Annotated[UploadFile, File()] = None,
):
    upload_result = cloudinary.uploader.upload(flyer.file)

    adverts_collection.insert_one(
        {
            "title": title,
            "price": price,
            "description": description,
            "category": category,
            "flyer": upload_result["secure_url"],
        }
    )
    return {"Message": "Advert added successfully."}


@app.get("/adverts")
def get_all_adverts(title="", description="", limit=7, skip=0):
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
@app.get("/adverts/{advert_id}")
def get_adverts_by_id(advert_id):
    # Check if advert id is valid
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid Advert ID")
    # Get adverts from database by id
    advert = adverts_collection.find_one({"_id": ObjectId(advert_id)})
    if not advert:
        raise HTTPException(status_code=404, detail="Advert Not Found")
    # Return response
    return {"data": replace_mongo_id(advert)}


# Update Advert (PUT): For vendors to edit an advert
@app.put("/adverts/{advert_id}")
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
@app.delete("/adverts/{advert_id}")
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
