"""
Shared utility functions used across route modules.
"""
from datetime import datetime
from bson import ObjectId


def serialize_doc(doc):
    """Convert MongoDB document to JSON-serializable format"""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    if isinstance(doc, dict):
        serialized = {}
        for key, value in doc.items():
            if key == "_id":
                continue
            elif isinstance(value, ObjectId):
                serialized[key] = str(value)
            elif isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, dict):
                serialized[key] = serialize_doc(value)
            elif isinstance(value, list):
                serialized[key] = [serialize_doc(item) if isinstance(item, dict) else item for item in value]
            else:
                serialized[key] = value

        if "ticket_id" in serialized:
            serialized["id"] = serialized["ticket_id"]
        if "user_id" in serialized and "id" not in serialized:
            serialized["id"] = serialized["user_id"]

        return serialized
    return doc
