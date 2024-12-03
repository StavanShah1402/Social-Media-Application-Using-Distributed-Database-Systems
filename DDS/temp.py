from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from datetime import datetime
import uuid

client = MongoClient("mongodb+srv://test1234:test1234@cluster0.wsbge.mongodb.net/")
db = client["Social_media_platform"]

test_user = {
    "user_id": str(uuid.uuid4()),
    "username": "testuser",
    "email": "testuser@example.com",
    "password": generate_password_hash("testpassword"),
    "profile_picture": "https://example.com/default_profile.jpg",
    "bio": "Test User",
    "created_at": datetime.now(),
    "followers": [],
    "following": []
}

db.users.insert_one(test_user)
print("Test user created.")
