# config.py

import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Config:
    # General
    SECRET_KEY = "your-secret-key"
    DEBUG = True
    ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
    google_key = os.getenv("google_key")

    # Database
    DB_NAME = "db.sqlite3"
    DB_USER = ""
    DB_PASSWORD = ""
    DB_HOST = ""
    DB_PORT = ""

    # Google Login
    GOOGLE_CLIENT_ID = "your-google-client-id.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET = "your-google-client-secret"

    # JWT / Auth (optional)
    JWT_SECRET_KEY = "your-jwt-secret"

# Optionally create separate classes for dev/prod
class DevelopmentConfig(Config):
    DEBUG = True
    ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

class ProductionConfig(Config):
    DEBUG = False
    ALLOWED_HOSTS = ["yourdomain.com"]
