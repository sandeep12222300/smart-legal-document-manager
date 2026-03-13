"""
version_service.py — Business logic for DocumentVersion management.

Key invariants enforced here:
  1. Content-hash deduplication — identical content is rejected.
  2. Sequential version numbering — always max(existing) + 1.
  3. Full transaction safety — partial writes are rolled back on error.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models import Document, DocumentVersion
from app.schemas import VersionCreate, DiffResponse
from app.utils.hash_utils import compute_sha256
from app.services.diff_service import compare_versions
from app.services.document_service import get_document_or_404




def create_version(
    db: Session, document_id: int, payload: VersionCreate
) -> tuple[DocumentVersion, DocumentVersion | None]:
    """
    Add a new version to a document.

    Returns:
        (new_version, previous_version) — previous_version is None only when
        document has no prior versions (shouldn't happen after creation, but
        handled defensively).

    Raises:
        404 if document does not exist.
        409 if the content hash matches the latest version (duplicate).
    """
    doc: Document = get_document_or_404(db, document_id)

    new_hash = compute_sha256(payload.content)


    latest_version: DocumentVersion | None = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_number.desc())
        .first()
    )

                                                                               
    if latest_version and latest_version.content_hash == new_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The submitted content is identical to the current version "
                f"(version {latest_version.version_number}). "
                "No new version was created."
            ),
        )

    next_version_number = (latest_version.version_number + 1) if latest_version else 1

    try:
        new_version = DocumentVersion(
            document_id=document_id,
            version_number=next_version_number,
            content=payload.content,
            content_hash=new_hash,
            created_by=payload.author,
        )
        db.add(new_version)
        db.commit()
        db.refresh(new_version)
        return new_version, latest_version
    except Exception:
        db.rollback()
        raise


                                                                               

def get_versions(db: Session, document_id: int) -> list[DocumentVersion]:
    """Return all versions for a document in ascending order."""
    get_document_or_404(db, document_id)
    return (
        db.query(DocumentVersion)
        .filter(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_number.asc())
        .all()
    )


def get_version_or_404(
    db: Session, document_id: int, version_number: int
) -> DocumentVersion:
    """Fetch a specific version by DOCUMENT ID + VERSION NUMBER, or raise 404."""
    version = (
        db.query(DocumentVersion)
        .filter(
            DocumentVersion.document_id == document_id,
            DocumentVersion.version_number == version_number,
        )
        .first()
    )
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version_number} not found for document id={document_id}.",
        )
    return version


def get_version_by_id_or_404(
    db: Session, document_id: int, version_id: int
) -> DocumentVersion:
    """Fetch a specific version by its PRIMARY KEY id, or raise 404."""
    version = (
        db.query(DocumentVersion)
        .filter(
            DocumentVersion.id == version_id,
            DocumentVersion.document_id == document_id,
        )
        .first()
    )
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version id={version_id} not found for document id={document_id}.",
        )
    return version


                                                                               

def compare(
    db: Session, document_id: int, v1_num: int, v2_num: int
) -> DiffResponse:
    """
    Compare two versions of a document and return a structured diff.

    Args:
        db:           Database session.
        document_id:  Parent document ID.
        v1_num:       Version number of the older/base version.
        v2_num:       Version number of the newer version.

    Returns:
        DiffResponse with added/removed/modified breakdown and a summary.
    """
    if v1_num == v2_num:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="v1 and v2 must be different version numbers.",
        )

    ver1 = get_version_or_404(db, document_id, v1_num)
    ver2 = get_version_or_404(db, document_id, v2_num)

    return compare_versions(
        v1_content=ver1.content,
        v2_content=ver2.content,
        document_id=document_id,
        version_1=v1_num,
        version_2=v2_num,
    )


                                                                               

def delete_version(db: Session, document_id: int, version_id: int) -> None:
    """
    Delete a single document version by its primary key ID.

    Note: This does NOT renumber remaining versions to preserve audit integrity.
    """
    version = get_version_by_id_or_404(db, document_id, version_id)
    try:
        db.delete(version)
        db.commit()
    except Exception:
        db.rollback()
        raise
