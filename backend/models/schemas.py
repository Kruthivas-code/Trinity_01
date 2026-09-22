"""
Pydantic request/response models for the Trinity docs-platform API.
"""
from pydantic import BaseModel, Field
from typing import Optional


# ==================== Auth ====================

class SessionCreate(BaseModel):
    session_id: str = Field(..., min_length=10, max_length=500)

    model_config = {"json_schema_extra": {"examples": [{"session_id": "abc123def456ghi789jkl012mno345pqr"}]}}


class APIKeyCreate(BaseModel):
    name: str
    description: Optional[str] = ""

    model_config = {"json_schema_extra": {"examples": [{"name": "CI/CD Pipeline Key", "description": "Used by GitHub Actions for automated ticket creation"}]}}
