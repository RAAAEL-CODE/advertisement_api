from enum import Enum
from fastapi import APIRouter, Form, HTTPException, status
from typing import Annotated
from pydantic import EmailStr
from db import users_collection
import bcrypt
import jwt
import os
from datetime import timezone, datetime, timedelta
from models import UserRole

# Create users router
users_router = APIRouter()


# Define endpoints
@users_router.post("/users/register")
def register_user(
    username: Annotated[str, Form()],
    email: Annotated[EmailStr, Form()],
    password: Annotated[str, Form(min_length=8)],
    role: Annotated[UserRole, Form()] = UserRole.GUEST,  # default role is guest
):
    # Ensure user does not exist (using this instead of find one, which brings the data from the dtbs)
    user_count = users_collection.count_documents(filter={"email": email})
    if user_count > 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "User already exists!")
    # Hash user password
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    users_collection.insert_one(
        {
            "username": username,
            "email": email,
            "password": hashed_password.decode("utf-8"),
            "role": role,
        }
    )
    # Save user into database
    # Return response
    return {"message": "User registered successfully"}


@users_router.post("/users/login")
def login_user(email: Annotated[EmailStr, Form()], password: Annotated[str, Form()]):
    # Ensure user exist
    user_in_db = users_collection.find_one({"email": email})
    if not user_in_db:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found!")
    # Compare their password
    hashed_password_in_db = user_in_db["password"]
    correct_password = bcrypt.checkpw(password.encode(), hashed_password_in_db.encode())
    if not correct_password:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    # Generate for them an access token
    encoded_jwt = jwt.encode(
        {
            "id": str(user_in_db["_id"]),
            "exp": datetime.now(tz=timezone.utc) + timedelta(hours=24),
        },
        os.getenv("JWT_SECRET_KEY"),
        "HS256",
    )
    # Return response
    return {"message": "Welcome to RAAAEL Ads", "access token": encoded_jwt}
