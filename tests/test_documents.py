"""
test_documents.py — Integration tests for the Smart Legal Document Manager API.

All tests use the in-memory SQLite test database defined in conftest.py.
Each test has a fully isolated, rolled-back transaction.

Test Coverage:
  1. Document creation — returns 201 with correct fields
  2. Version 1 is auto-created on document creation
  3. New version accepted — increments version number
  4. Duplicate content rejected — 409 Conflict (hash guard)
  5. Compare endpoint — returns structured diff with correct fields
  6. Title PATCH — updates title, no new version created
  7. Delete single version — version is gone, document remains
  8. Hard delete — document and all versions removed
"""

import pytest

from app.services.diff_service import similarity_score


CONTENT_V1 = "Payment shall be made within 10 days of invoice."
CONTENT_V2 = "Payment shall be made within 30 days of invoice."
CONTENT_V3 = "Payment shall be made within 30 days of invoice receipt, subject to verification."


def _create_doc(client, title="Contract A", content=CONTENT_V1, author="Alice") -> dict:
    resp = client.post("/documents", json={"title": title, "content": content, "author": author})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_document_returns_201(client):
    """POSTing a new document should return 201 with the created document data."""
    resp = client.post(
        "/documents",
        json={"title": "Service Agreement", "content": CONTENT_V1, "author": "Bob"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Service Agreement"
    assert data["created_by"] == "Bob"
    assert "id" in data
    assert "created_at" in data


def test_version_1_auto_created(client):
    """After creating a document, its version history should contain exactly Version 1."""
    doc = _create_doc(client)
    resp = client.get(f"/documents/{doc['id']}/versions")
    assert resp.status_code == 200
    versions = resp.json()
    assert len(versions) == 1
    v1 = versions[0]
    assert v1["version_number"] == 1
    assert v1["content"] == CONTENT_V1
    assert v1["created_by"] == "Alice"
    assert len(v1["content_hash"]) == 64


def test_new_version_increments_version_number(client):
    """Adding a second version with different content should create Version 2."""
    doc = _create_doc(client)

    resp = client.post(
        f"/documents/{doc['id']}/versions",
        json={"content": CONTENT_V2, "author": "Carol"},
    )
    assert resp.status_code == 201
    v2 = resp.json()
    assert v2["version_number"] == 2
    assert v2["content"] == CONTENT_V2
    assert v2["created_by"] == "Carol"

    hist = client.get(f"/documents/{doc['id']}/versions").json()
    assert len(hist) == 2


def test_duplicate_content_rejected(client):
    """Submitting identical content as the current version should return 409."""
    doc = _create_doc(client)

    resp = client.post(
        f"/documents/{doc['id']}/versions",
        json={"content": CONTENT_V2, "author": "Dave"},
    )
    assert resp.status_code == 201

    resp = client.post(
        f"/documents/{doc['id']}/versions",
        json={"content": CONTENT_V2, "author": "Dave"},
    )
    assert resp.status_code == 409
    assert "identical" in resp.json()["detail"].lower()


def test_compare_returns_structured_diff(client):
    """GET /compare?v1=1&v2=2 should return structured added/removed/modified output."""
    doc = _create_doc(client)
    client.post(
        f"/documents/{doc['id']}/versions",
        json={"content": CONTENT_V2, "author": "Eve"},
    )

    resp = client.get(f"/documents/{doc['id']}/compare?v1=1&v2=2")
    assert resp.status_code == 200
    diff = resp.json()

    assert diff["document_id"] == doc["id"]
    assert diff["version_1"] == 1
    assert diff["version_2"] == 2
    assert "added" in diff
    assert "removed" in diff
    assert "modified" in diff
    assert "summary" in diff

    assert len(diff["modified"]) >= 1
    mod = diff["modified"][0]
    assert "before" in mod and "after" in mod
    assert "10 days" in mod["before"]
    assert "30 days" in mod["after"]


def test_title_patch_does_not_create_new_version(client):
    """PATCHing the title should update it without adding a new document version."""
    doc = _create_doc(client, title="Original Title")

    resp = client.patch(
        f"/documents/{doc['id']}/title",
        json={"title": "Updated Title"},
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["title"] == "Updated Title"

    versions = client.get(f"/documents/{doc['id']}/versions").json()
    assert len(versions) == 1


def test_delete_single_version(client):
    """DELETEing a non-latest version by its ID should remove it and keep the document intact."""
    doc = _create_doc(client)

    v2_resp = client.post(
        f"/documents/{doc['id']}/versions",
        json={"content": CONTENT_V2, "author": "Frank"},
    )
    assert v2_resp.status_code == 201

    versions_before = client.get(f"/documents/{doc['id']}/versions").json()
    v1 = next(v for v in versions_before if v["version_number"] == 1)

    del_resp = client.delete(f"/documents/{doc['id']}/versions/{v1['id']}")
    assert del_resp.status_code == 204

    versions_after = client.get(f"/documents/{doc['id']}/versions").json()
    assert len(versions_after) == 1
    assert versions_after[0]["version_number"] == 2


def test_delete_latest_version_rejected(client):
    """Latest version delete should be blocked to preserve append-only history."""
    doc = _create_doc(client)

    v2_resp = client.post(
        f"/documents/{doc['id']}/versions",
        json={"content": CONTENT_V2, "author": "Frank"},
    )
    v2 = v2_resp.json()

    del_resp = client.delete(f"/documents/{doc['id']}/versions/{v2['id']}")
    assert del_resp.status_code == 400
    assert "latest version" in del_resp.json()["detail"].lower()


def test_delete_only_version_rejected(client):
    """Single remaining version delete should be blocked to avoid accidental history wipe."""
    doc = _create_doc(client)
    v1 = client.get(f"/documents/{doc['id']}/versions").json()[0]

    del_resp = client.delete(f"/documents/{doc['id']}/versions/{v1['id']}")
    assert del_resp.status_code == 400
    assert "only remaining version" in del_resp.json()["detail"].lower()


def test_similarity_score_ignores_whitespace_only_changes():
    """Whitespace-only edits should be treated as trivial for notification significance."""
    old_text = "Section 1: Payment terms.\nClause A applies."
    new_text = "  Section 1:  Payment terms. \n\nClause A applies.   "

    assert similarity_score(old_text, new_text) == pytest.approx(1.0)


def test_hard_delete_removes_document_and_versions(client):
    """DELETE /documents/{id}?hard=true should remove the document and all its versions."""
    doc = _create_doc(client)
    client.post(
        f"/documents/{doc['id']}/versions",
        json={"content": CONTENT_V2, "author": "Grace"},
    )

    resp = client.delete(f"/documents/{doc['id']}")
    assert resp.status_code == 400

    resp = client.delete(f"/documents/{doc['id']}?hard=true")
    assert resp.status_code == 204

    resp_versions = client.get(f"/documents/{doc['id']}/versions")
    assert resp_versions.status_code == 404

