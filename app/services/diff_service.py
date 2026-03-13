"""
diff_service.py — Document version comparison using difflib.

Produces a structured, human-readable diff categorised into:
  • added   — lines that exist only in the newer version
  • removed — lines that exist only in the older version
  • modified — line pairs that represent an in-place change

Algorithm
---------
We use difflib.ndiff which annotates each line with:
  '  ' — unchanged
  '- ' — present in old, absent in new
  '+ ' — present in new, absent in old
  '? ' — hint line (ignored)

To detect "modified" pairs we look for a (remove, add) consecutive pattern
in the diff output — this strongly implies the same logical line was edited.
"""

import difflib
import re
from app.schemas import DiffResponse, ModifiedLine


def compare_versions(
    v1_content: str,
    v2_content: str,
    document_id: int,
    version_1: int,
    version_2: int,
) -> DiffResponse:
    """
    Compare two document version texts and return a structured DiffResponse.

    Args:
        v1_content: Full text of the older version.
        v2_content: Full text of the newer version.
        document_id: ID of the parent document (for response metadata).
        version_1: Version number of v1_content.
        version_2: Version number of v2_content.

    Returns:
        DiffResponse with added, removed, modified collections and a summary.
    """
    v1_lines = v1_content.splitlines(keepends=False)
    v2_lines = v2_content.splitlines(keepends=False)

    diff = list(difflib.ndiff(v1_lines, v2_lines))

    added: list[str] = []
    removed: list[str] = []
    modified: list[ModifiedLine] = []

    i = 0
    while i < len(diff):
        line = diff[i]

        if line.startswith("? "):

            i += 1
            continue

        if line.startswith("- "):
            removed_text = line[2:]

                        
                    
            j = i + 1
            while j < len(diff) and diff[j].startswith("? "):
                j += 1

            if j < len(diff) and diff[j].startswith("+ "):
                added_text = diff[j][2:]
                modified.append(ModifiedLine(before=removed_text, after=added_text))
                i = j + 1
            else:
                removed.append(removed_text)
                i += 1

        elif line.startswith("+ "):
            added.append(line[2:])
            i += 1

        else:
            i += 1

    parts: list[str] = []
    if modified:
        parts.append(f"{len(modified)} line(s) modified")
    if added:
        parts.append(f"{len(added)} line(s) added")
    if removed:
        parts.append(f"{len(removed)} line(s) removed")

    summary = (
        f"Comparing version {version_1} → {version_2}: "
        + (", ".join(parts) if parts else "No changes detected")
        + "."
    )

    return DiffResponse(
        document_id=document_id,
        version_1=version_1,
        version_2=version_2,
        added=added,
        removed=removed,
        modified=modified,
        summary=summary,
    )


def _normalize_for_similarity(text: str) -> str:
    """Normalize text so whitespace-only edits are treated as trivial."""
    return re.sub(r"\s+", "", text)


def similarity_score(text_a: str, text_b: str) -> float:
    """
    Return a similarity ratio in [0.0, 1.0] between two strings.

    Whitespace is normalized away so spacing/newline-only edits do not
    trigger significance notifications.
    """
    normalized_a = _normalize_for_similarity(text_a)
    normalized_b = _normalize_for_similarity(text_b)
    return difflib.SequenceMatcher(None, normalized_a, normalized_b).ratio()
