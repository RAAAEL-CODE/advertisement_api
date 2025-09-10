from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to Mongo Atlas Cluster
mongo_client = MongoClient(os.getenv("DATABASE_URI"))

# Assess database
advertisement_manager_db = mongo_client["advertisement_manager_db"]

# Pick a collection to operate on
adverts_collection = advertisement_manager_db["adverts"]
