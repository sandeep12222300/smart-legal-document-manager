"""
hash_utils.py — Content hashing utilities.

All document version content is hashed with SHA-256 before storage.
This allows fast duplicate-content detection without full text comparison.
"""

import hashlib


def compute_sha256(content: str) -> str:
    """
    Compute the SHA-256 hex digest of a UTF-8 encoded string.

    Args:
        content: The document text to hash.

    Returns:
        A 64-character lowercase hex string.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
