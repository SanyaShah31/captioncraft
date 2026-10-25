"""
Database module for CaptionCraft AI.
Manages persistent MongoDB connection, collections, and index initialization
for user authentication and password reset tokens.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple
from dotenv import load_dotenv, find_dotenv
import pymongo
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, PyMongoError

# Ensure project root and backend are on sys.path and .env is loaded
_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent

for _p in [str(_PROJECT_ROOT), str(_BACKEND_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

_root_env = _PROJECT_ROOT / ".env"
if _root_env.exists():
    load_dotenv(dotenv_path=_root_env)
else:
    load_dotenv(find_dotenv(usecwd=True))

DEFAULT_MONGODB_URI = "mongodb://localhost:27017"
DEFAULT_MONGODB_DATABASE = "captioncraft_db"

_client: Optional[pymongo.MongoClient] = None


class DatabaseConnectionError(Exception):
    """Raised when MongoDB connection cannot be established."""
    pass


def get_mongodb_config() -> Tuple[str, str]:
    """
    Reads MongoDB connection settings from environment variables.
    Does not hardcode credentials.
    """
    uri = os.getenv("MONGODB_URI", "").strip() or DEFAULT_MONGODB_URI
    db_name = os.getenv("MONGODB_DATABASE", "").strip() or DEFAULT_MONGODB_DATABASE
    return uri, db_name


def get_mongo_client(uri: Optional[str] = None, timeout_ms: int = 3000) -> pymongo.MongoClient:
    """
    Returns a managed MongoClient singleton instance.
    Pings the server with a short timeout to confirm connectivity.
    Never exposes credentials or URI in error messages.
    """
    global _client
    target_uri = uri or get_mongodb_config()[0]

    if _client is not None:
        try:
            _client.admin.command("ping")
            return _client
        except Exception:
            _client = None

    try:
        client = pymongo.MongoClient(
            target_uri,
            serverSelectionTimeoutMS=timeout_ms,
            connectTimeoutMS=timeout_ms
        )
        # Verify connection
        client.admin.command("ping")
        _client = client
        return _client
    except (ServerSelectionTimeoutError, ConnectionFailure, PyMongoError) as e:
        raise DatabaseConnectionError(
            "Unable to connect to the database. Please verify that your MongoDB service is running and accessible."
        ) from e


def init_db(db: pymongo.database.Database) -> None:
    """
    Ensures required unique indices exist on users and password_resets collections.
    """
    try:
        # Unique index on normalized email for users collection
        db["users"].create_index("email", unique=True, background=True)
        # Unique index on token_hash for password resets
        db["password_resets"].create_index("token_hash", unique=True, background=True)
        # TTL index on expires_at for automatic cleanup of expired tokens
        db["password_resets"].create_index("expires_at", expireAfterSeconds=0, background=True)
        # Indexes for user-specific and feature-specific history
        db["history"].create_index([("user_id", 1), ("feature_type", 1), ("created_at", -1)], background=True)
        db["history"].create_index([("user_id", 1), ("created_at", -1)], background=True)
        db["history"].create_index("id", unique=True, background=True)
        # Indexes for persistent user sessions
        db["user_sessions"].create_index("token_hash", unique=True, background=True)
        db["user_sessions"].create_index("expires_at", expireAfterSeconds=0, background=True)
        db["user_sessions"].create_index("user_id", background=True)
    except Exception as e:
        # Log or re-raise as DatabaseConnectionError
        raise DatabaseConnectionError("Failed to initialize database indexes.") from e


def get_db(uri: Optional[str] = None, db_name: Optional[str] = None) -> pymongo.database.Database:
    """
    Retrieves the configured MongoDB database and initializes required indexes.
    """
    env_uri, env_db = get_mongodb_config()
    target_uri = uri or env_uri
    target_db_name = db_name or env_db

    client = get_mongo_client(target_uri)
    db = client[target_db_name]
    init_db(db)
    return db


def check_db_connection() -> Tuple[bool, Optional[str]]:
    """
    Quick non-throwing health check for MongoDB connectivity.
    Returns: (is_healthy, error_message_or_none)
    """
    try:
        get_db()
        return True, None
    except DatabaseConnectionError as e:
        return False, str(e)
    except Exception:
        return False, "Unable to establish connection to MongoDB."
