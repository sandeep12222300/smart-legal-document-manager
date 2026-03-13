"""
models.py — SQLAlchemy ORM models for Document and DocumentVersion.

Design rules:
  • DocumentVersions are immutable once created.
  • version_number increments sequentially per document.
  • content_hash (SHA-256) prevents duplicate version content.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id: int = Column(Integer, primary_key=True, index=True)
    title: str = Column(String(512), nullable=False)
    created_by: str = Column(String(256), nullable=False)
    created_at: datetime = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    versions = relationship(
        "DocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersion.version_number",
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} title={self.title!r}>"


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: int = Column(Integer, primary_key=True, index=True)
    document_id: int = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: int = Column(Integer, nullable=False)
    content: str = Column(Text, nullable=False)
    content_hash: str = Column(String(64), nullable=False)
    created_by: str = Column(String(256), nullable=False)
    created_at: datetime = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    document = relationship("Document", back_populates="versions")


    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_doc_version"),
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentVersion doc_id={self.document_id} "
            f"v={self.version_number} hash={self.content_hash[:8]}...>"
        )
