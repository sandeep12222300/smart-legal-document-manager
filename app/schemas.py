"""
schemas.py — Pydantic v2 request/response schemas.

All API inputs and outputs are strictly typed.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


                                                                               

class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=512, description="Document title")
    content: str = Field(..., min_length=1, description="Initial document text (becomes Version 1)")
    author: str = Field(..., min_length=1, max_length=256, description="Name of the author creating the document")


class TitleUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=512, description="New document title")


class DocumentResponse(BaseModel):
    id: int
    title: str
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}




class VersionCreate(BaseModel):
    content: str = Field(..., min_length=1, description="New version text content")
    author: str = Field(..., min_length=1, max_length=256, description="Author name for this version")


class VersionResponse(BaseModel):
    id: int
    document_id: int
    version_number: int
    content: str
    content_hash: str
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


                                                                               

class ModifiedLine(BaseModel):
    before: str = Field(..., description="Original line (from version v1)")
    after: str = Field(..., description="Changed line (from version v2)")


class DiffResponse(BaseModel):
    document_id: int
    version_1: int
    version_2: int
    added: list[str] = Field(default_factory=list, description="Lines present only in v2")
    removed: list[str] = Field(default_factory=list, description="Lines present only in v1")
    modified: list[ModifiedLine] = Field(default_factory=list, description="Lines that changed between versions")
    summary: str = Field(..., description="Human-readable summary of changes")
