from fastapi import FastAPI
import cloudinary
import os
from dotenv import load_dotenv
from routes.adverts import adverts_router
from routes.users import users_router
from routes.genai import genai_router

load_dotenv()

# Configure cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET"),
)


app = FastAPI(title="RAAAEL Advertisement API", version="1.0.0")


# Home page
@app.get("/", tags=["Home"])
def read_root():
    return {"message": "Welcome to RAAAEL Advertisement API"}


# Include routers
app.include_router(adverts_router)
app.include_router(users_router, tags=["User"])
app.include_router(genai_router)
