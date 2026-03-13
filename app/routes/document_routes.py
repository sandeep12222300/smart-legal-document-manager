"""
document_routes.py — All REST API endpoints for the Smart Legal Document Manager.

Endpoint summary:
  POST   /documents                              — Create document + Version 1
  POST   /documents/{id}/versions               — Upload a new version
  GET    /documents/{id}/versions               — List all versions
  GET    /documents/{id}/compare?v1=1&v2=2      — Compare two versions
  PATCH  /documents/{id}/title                  — Update title (no new version)
  DELETE /documents/{id}/versions/{version_id}  — Delete a single version
  DELETE /documents/{id}?hard=true              — Delete entire document
"""

from fastapi import APIRouter, Depends, BackgroundTasks, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    DocumentCreate,
    DocumentResponse,
    TitleUpdate,
    VersionCreate,
    VersionResponse,
    DiffResponse,
)
from app.services import document_service, version_service
from app.services.notification_service import notify_significant_change

router = APIRouter(prefix="/documents", tags=["Documents"])


                                                                                

@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new legal document",
    description=(
        "Creates a document record and automatically publishes **Version 1** "
        "from the supplied content. The content hash is stored to prevent "
        "duplicate versions in the future."
    ),
)
def create_document(
    payload: DocumentCreate,
    db: Session = Depends(get_db),
) -> DocumentResponse:
    doc = document_service.create_document(db, payload)
    return doc


@router.get(
    "",
    response_model=list[DocumentResponse],
    summary="List all documents",
)
def list_documents(db: Session = Depends(get_db)) -> list[DocumentResponse]:
    return document_service.list_documents(db)


@router.patch(
    "/{document_id}/title",
    response_model=DocumentResponse,
    summary="Update document title",
    description=(
        "Updates only the document title. "
        "This is a **metadata-only** operation and does NOT create a new version."
    ),
)
def update_title(
    document_id: int,
    payload: TitleUpdate,
    db: Session = Depends(get_db),
) -> DocumentResponse:
    return document_service.update_title(db, document_id, payload.title)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
    description=(
        "Requires `?hard=true` to confirm intentional deletion. "
        "Removes the document **and all its versions** permanently."
    ),
)
def delete_document(
    document_id: int,
    hard: bool = Query(
        False, description="Must be `true` to confirm deletion of document and all its versions."
    ),
    db: Session = Depends(get_db),
) -> None:
    if not hard:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Safety guard: add `?hard=true` to confirm permanent deletion.",
        )
    document_service.delete_document(db, document_id)


                                                                                

@router.post(
    "/{document_id}/versions",
    response_model=VersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new document version",
    description=(
        "Adds a new immutable version to the document. "
        "Rejected with **409 Conflict** if the content is identical to the "
        "current version (duplicate-hash guard). "
        "A **background notification** is dispatched if the change is significant "
        "(similarity < 98%)."
    ),
)
def create_version(
    document_id: int,
    payload: VersionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> VersionResponse:
    new_version, previous_version = version_service.create_version(db, document_id, payload)

  
    if previous_version is not None:
        doc = document_service.get_document_or_404(db, document_id)
        background_tasks.add_task(
            notify_significant_change,
            document_id=document_id,
            document_title=doc.title,
            version_number=new_version.version_number,
            author=new_version.created_by,
            old_content=previous_version.content,
            new_content=new_version.content,
        )

    return new_version


@router.get(
    "/{document_id}/versions",
    response_model=list[VersionResponse],
    summary="List version history",
    description="Returns all versions of a document in ascending version order.",
)
def list_versions(
    document_id: int,
    db: Session = Depends(get_db),
) -> list[VersionResponse]:
    return version_service.get_versions(db, document_id)


@router.get(
    "/{document_id}/compare",
    response_model=DiffResponse,
    summary="Compare two versions",
    description=(
        "Returns a structured diff between version **v1** and **v2**, showing "
        "added lines, removed lines, and modified line pairs. "
        "Output is designed to be readable by non-technical users."
    ),
)
def compare_versions(
    document_id: int,
    v1: int = Query(..., description="Version number of the base (older) version"),
    v2: int = Query(..., description="Version number of the target (newer) version"),
    db: Session = Depends(get_db),
) -> DiffResponse:
    return version_service.compare(db, document_id, v1, v2)


@router.delete(
    "/{document_id}/versions/{version_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a specific version",
    description=(
        "Removes a single version by its **primary key ID** (not version number). "
        "The remaining versions retain their original version numbers."
    ),
)
def delete_version(
    document_id: int,
    version_id: int,
    db: Session = Depends(get_db),
) -> None:
    version_service.delete_version(db, document_id, version_id)
