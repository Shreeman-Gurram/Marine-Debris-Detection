"""
backend/app/database/mongodb.py
================================
SONARIS Backend — MongoDB Atlas Connection + Persistence

Uses environment variable MONGODB_URI (loaded from .env if present).
Database: sonaris
Collection: analyses

Design principles:
  - Connection is created lazily on first use.
  - If MONGODB_URI is not configured, raises MongoUnavailableError clearly.
  - If Atlas is unreachable, raises MongoUnavailableError with the root cause.
  - The inference pipeline is NOT blocked by DB failures — the caller decides.
  - No credentials are ever hardcoded.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Load .env if it exists (no error if absent)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; rely on actual env vars

logger = logging.getLogger("sonaris.database")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DB_NAME         = "sonaris"
COLLECTION_NAME = "analyses"
_CONNECT_TIMEOUT_MS = 5000   # 5s timeout for Atlas connection check
_SERVER_TIMEOUT_MS  = 5000


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------
class MongoUnavailableError(RuntimeError):
    """Raised when MongoDB is not configured or cannot be reached."""


# ---------------------------------------------------------------------------
# Lazy singleton client
# ---------------------------------------------------------------------------
_client = None   # pymongo.MongoClient or None


def _get_client():
    """Return a cached MongoClient, creating it on first call."""
    global _client

    if _client is not None:
        return _client

    uri = os.environ.get("MONGODB_URI", "").strip()
    if not uri:
        raise MongoUnavailableError(
            "MONGODB_URI environment variable is not set. "
            "Create a .env file with MONGODB_URI=<your Atlas connection string> "
            "or set it in your environment before starting the server."
        )

    try:
        import pymongo
    except ImportError as exc:
        raise MongoUnavailableError(
            "pymongo is not installed. Run: pip install pymongo"
        ) from exc

    try:
        client = pymongo.MongoClient(
            uri,
            connectTimeoutMS=_CONNECT_TIMEOUT_MS,
            serverSelectionTimeoutMS=_SERVER_TIMEOUT_MS,
        )
        # Force an actual connection attempt to detect unreachable clusters early
        client.admin.command("ping")
        logger.info("MongoDB Atlas connected. Database: %s", DB_NAME)
        _client = client
        return _client
    except Exception as exc:
        raise MongoUnavailableError(
            f"MongoDB connection failed: {exc}. "
            "Check that MONGODB_URI is correct and the cluster is accessible."
        ) from exc


def get_database():
    """Return the 'sonaris' database handle."""
    return _get_client()[DB_NAME]


def get_analyses_collection():
    """Return the 'analyses' collection handle."""
    return get_database()[COLLECTION_NAME]


# ---------------------------------------------------------------------------
# Document operations
# ---------------------------------------------------------------------------

def insert_analysis(document: Dict[str, Any]) -> str:
    """
    Insert one analysis result document into the analyses collection.

    Automatically adds a UTC 'created_at' timestamp if not already present.

    Args:
        document: Dict containing the full analysis result.

    Returns:
        The inserted document's ObjectId as a string.

    Raises:
        MongoUnavailableError: If MongoDB is not configured or unreachable.
        RuntimeError: If the insert itself fails for any other reason.
    """
    doc = dict(document)
    if "created_at" not in doc:
        doc["created_at"] = datetime.now(timezone.utc).isoformat()

    try:
        collection = get_analyses_collection()
        result = collection.insert_one(doc)
        inserted_id = str(result.inserted_id)
        logger.info(
            "Analysis document inserted. id=%s  collection=%s.%s",
            inserted_id, DB_NAME, COLLECTION_NAME,
        )
        return inserted_id
    except MongoUnavailableError:
        raise
    except Exception as exc:
        raise RuntimeError(
            f"MongoDB insert_one failed: {exc}"
        ) from exc
