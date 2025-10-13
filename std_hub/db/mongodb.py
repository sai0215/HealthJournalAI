from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os
import logging

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, skip
 
logger = logging.getLogger(__name__)

# MongoDB Atlas connection string
# Replace with your MongoDB Atlas connection string
# Format: mongodb+srv://<username>:<password>@<cluster>.mongodb.net/<database>?retryWrites=true&w=majority
# Or set the MONGODB_URI environment variable in a .env file

# Option 1: Read from environment variable (recommended for security)
mongo_uri = os.environ.get("MONGODB_URI")

# Option 2: If no environment variable, use the connection string below
# Uncomment and replace with your actual MongoDB Atlas credentials
if not mongo_uri:
    # mongo_uri = "mongodb+srv://<username>:<password>@<cluster>.mongodb.net/<database>?retryWrites=true&w=majority"
    mongo_uri = None  # Set to None to run without database, or add your Atlas connection string above
 
if mongo_uri:
    try:
        # Attempt to connect to MongoDB (Atlas or local)
        # Reduced timeout for faster failure detection
        db_client = MongoClient(
            mongo_uri, 
            serverSelectionTimeoutMS=3000,  # 3-second timeout for faster failure
            connectTimeoutMS=3000,
            socketTimeoutMS=3000
        )
       
        # Ping the server to check if MongoDB is running
        db_client.admin.command('ping')
        logger.info("MongoDB Atlas is connected and running successfully.")
    except (ConnectionFailure, Exception) as e:
        logger.warning(f"MongoDB is not running or cannot be reached: {e}. Continuing without database.")
        db_client = None
else:
    logger.warning("MongoDB URI is not set in the configuration. Continuing without database.")
    db_client = None