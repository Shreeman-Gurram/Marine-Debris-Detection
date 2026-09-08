"""
backend/test_mongodb.py
========================
SONARIS — MongoDB connection and document verification script.

Run AFTER configuring MONGODB_URI in .env and running POST /api/analyze.

Usage:
    python backend/test_mongodb.py [analysis_id]

    If analysis_id is provided, fetches that specific document.
    Otherwise, fetches the most recent document.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

uri = os.environ.get("MONGODB_URI", "").strip()
if not uri:
    print("ERROR: MONGODB_URI is not set.")
    print("  Edit .env: MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>/")
    sys.exit(1)

try:
    import pymongo
except ImportError:
    print("ERROR: pymongo not installed. Run: pip install pymongo")
    sys.exit(1)

print(f"Connecting to MongoDB...")
try:
    client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    print("Connected OK.")
except Exception as exc:
    print(f"ERROR: Could not connect: {exc}")
    sys.exit(1)

db         = client["sonaris"]
collection = db["analyses"]

analysis_id_arg = sys.argv[1] if len(sys.argv) > 1 else None

if analysis_id_arg:
    from bson import ObjectId
    doc = collection.find_one({"_id": ObjectId(analysis_id_arg)})
    if doc is None:
        print(f"ERROR: No document found with _id={analysis_id_arg}")
        sys.exit(1)
    print(f"\nDocument for analysis_id={analysis_id_arg}:")
else:
    doc = collection.find_one(sort=[("created_at", pymongo.DESCENDING)])
    if doc is None:
        print("No documents found in sonaris.analyses collection.")
        sys.exit(0)
    print("\nMost recent document in sonaris.analyses:")

# Serialize ObjectId for printing
doc["_id"] = str(doc["_id"])
print(json.dumps(doc, indent=2, default=str))
print(f"\nTotal documents in collection: {collection.count_documents({})}")
