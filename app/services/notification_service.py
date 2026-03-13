"""
notification_service.py — Asynchronous change notification system.

Triggered by version_service after a new version is saved.
Only fires when the similarity between old and new content drops below 0.98
(i.e. the change is significant enough to warrant attention).

In production, replace the console log with an email/SMS/webhook call.
"""

import logging
from datetime import datetime, timezone

from app.services.diff_service import similarity_score

logger = logging.getLogger(__name__)

                                                                                
                                                                          
TRIVIAL_SIMILARITY_THRESHOLD: float = 0.98


def notify_significant_change(
    document_id: int,
    document_title: str,
    version_number: int,
    author: str,
    old_content: str,
    new_content: str,
) -> None:
    """
    Evaluate whether a version change is significant and, if so, trigger a
    notification.  This function is designed to be scheduled as a
    FastAPI BackgroundTask — it does NOT block the HTTP response.

    Any notification-side failure is logged and swallowed so it cannot
    affect already-committed document/version writes.
    """
    try:
        score = similarity_score(old_content, new_content)
        timestamp = datetime.now(timezone.utc).isoformat()

        if score >= TRIVIAL_SIMILARITY_THRESHOLD:
            logger.info(
                "[Notification] SKIPPED — trivial change detected "
                "(similarity=%.4f) for document '%s' (id=%d) version %d.",
                score, document_title, document_id, version_number,
            )
            return

        logger.warning(
            "[Notification] SIGNIFICANT CHANGE on document '%s' (id=%d)\n"
            "  ▸ New version : %d\n"
            "  ▸ Edited by   : %s\n"
            "  ▸ Similarity  : %.4f (threshold=%.2f)\n"
            "  ▸ Timestamp   : %s",
            document_title, document_id,
            version_number,
            author,
            score, TRIVIAL_SIMILARITY_THRESHOLD,
            timestamp,
        )

        _send_email_placeholder(
            document_id=document_id,
            document_title=document_title,
            version_number=version_number,
            author=author,
            similarity=score,
            timestamp=timestamp,
        )
    except Exception:
        logger.exception(
            "[Notification] FAILED for document '%s' (id=%d) version %d.",
            document_title,
            document_id,
            version_number,
        )


def _send_email_placeholder(
    document_id: int,
    document_title: str,
    version_number: int,
    author: str,
    similarity: float,
    timestamp: str,
) -> None:
    """
    Placeholder for an actual email/webhook delivery.

    Replace this function body with an SMTP call, SendGrid API request,
    Slack webhook, etc. in production.
    """
    email_body = (
        f"\n{'═' * 60}\n"
        f"  📧  LEGAL DOCUMENT CHANGE ALERT\n"
        f"{'═' * 60}\n"
        f"  Document : {document_title} (ID: {document_id})\n"
        f"  Version  : {version_number}\n"
        f"  Author   : {author}\n"
        f"  Time     : {timestamp}\n"
        f"  Similarity to previous version: {similarity:.1%}\n"
        f"\n"
        f"  ACTION REQUIRED: Please review the updated document.\n"
        f"  Navigate to /documents/{document_id}/compare?v1={version_number - 1}&v2={version_number}\n"
        f"{'═' * 60}"
    )
                                                                                           
    print(email_body)
