"""
document_service.py — Business logic for Document CRUD operations.

All database mutations are wrapped in transactions so that partial writes
cannot occur.  If anything fails mid-operation the session is rolled back
by SQLAlchemy's context or the caller's exception handler.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import Document, DocumentVersion
from app.schemas import DocumentCreate
from app.utils.hash_utils import compute_sha256




def create_document(db: Session, payload: DocumentCreate) -> Document:
    """
    Create a new Document and its first version (Version 1) atomically.

    Steps:
      1. Create the Document row.
      2. Hash the initial content.
      3. Create DocumentVersion with version_number=1.
      4. Commit the transaction.

    If any step fails the entire transaction is rolled back.
    """
    try:
        doc = Document(title=payload.title, created_by=payload.author)
        db.add(doc)
        db.flush()                                         

        content_hash = compute_sha256(payload.content)
        version = DocumentVersion(
            document_id=doc.id,
            version_number=1,
            content=payload.content,
            content_hash=content_hash,
            created_by=payload.author,
        )
        db.add(version)
        db.commit()
        db.refresh(doc)
        return doc
    except Exception:
        db.rollback()
        raise


                                                                               

def get_document_or_404(db: Session, document_id: int) -> Document:
    """Fetch a document by ID or raise 404."""
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id={document_id} not found.",
        )
    return doc


def list_documents(db: Session) -> list[Document]:
    """Return all documents ordered by creation date."""
    return db.query(Document).order_by(Document.created_at.desc()).all()


                                                                               

def update_title(db: Session, document_id: int, new_title: str) -> Document:
    """
    Update a document's title WITHOUT creating a new version.

    This is a metadata-only change and does not affect version history.
    """
    doc = get_document_or_404(db, document_id)
    try:
        doc.title = new_title
        db.commit()
        db.refresh(doc)
        return doc
    except Exception:
        db.rollback()
        raise


                                                                               

def delete_document(db: Session, document_id: int) -> None:
    """
    Hard-delete a document and ALL its versions.

    The cascade="all, delete-orphan" relationship on Document.versions
    ensures all DocumentVersion rows are removed in the same transaction.
    """
    doc = get_document_or_404(db, document_id)
    try:
        db.delete(doc)
        db.commit()
    except Exception:
        db.rollback()
        raise
