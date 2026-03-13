# Smart Legal Document Manager

A **production-ready backend API** that gives lawyers a lightweight version control system for legal documents — with immutable versioning, content-diff comparison, and an async change-notification system.

Built with **Python · FastAPI · SQLAlchemy · SQLite** (swappable to PostgreSQL).

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Installation](#installation)
3. [Running the Server](#running-the-server)
4. [API Reference & Example Requests](#api-reference--example-requests)
5. [How Versioning Works](#how-versioning-works)
6. [How Diff Comparison Works](#how-diff-comparison-works)
7. [Async Notification System](#async-notification-system)
8. [Project Structure](#project-structure)
9. [Running Tests](#running-tests)

---

## Project Overview

| Feature | Description |
|---|---|
| **Document Management** | Create, read, update title, and delete legal documents |
| **Immutable Versioning** | Every edit creates a new version; old content is never overwritten |
| **Duplicate Guard** | SHA-256 content hashing prevents identical versions |
| **Diff Comparison** | Line-level diff between any two versions (added / removed / modified) |
| **Smart Notifications** | Background alerts only triggered for significant changes (similarity < 98%) |
| **Audit Trail** | Every version records author name and timestamp |
| **Safe Deletion** | `?hard=true` query guard prevents accidental data loss |

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourname/smart-legal-document-manager.git
cd smart-legal-document-manager

# 2. Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

### PostgreSQL (optional, production)

The app uses **SQLite** by default (`legal_docs.db` in the project root).
To use PostgreSQL, set the environment variable:

```bash
$env:DATABASE_URL = "postgresql+psycopg2://user:password@localhost/legal_docs"
```

---

## Running the Server

```bash
uvicorn app.main:app --reload
```

The server starts at **http://127.0.0.1:8000**.

| URL | Description |
|---|---|
| `http://127.0.0.1:8000/docs` | Interactive Swagger UI |
| `http://127.0.0.1:8000/redoc` | ReDoc documentation |
| `http://127.0.0.1:8000/` | Health check |

---

## API Reference & Example Requests

### 1 — Create a Document

```bash
curl -X POST http://127.0.0.1:8000/documents \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Service Agreement",
    "content": "Payment shall be made within 10 days of invoice.",
    "author": "Alice"
  }'
```

**Response (201)**
```json
{
  "id": 1,
  "title": "Service Agreement",
  "created_by": "Alice",
  "created_at": "2026-03-13T17:00:00+00:00"
}
```

---

### 2 — Upload a New Version

```bash
curl -X POST http://127.0.0.1:8000/documents/1/versions \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Payment shall be made within 30 days of invoice.",
    "author": "Bob"
  }'
```

**Response (201)**
```json
{
  "id": 2,
  "document_id": 1,
  "version_number": 2,
  "content": "Payment shall be made within 30 days of invoice.",
  "content_hash": "a1b2c3...",
  "created_by": "Bob",
  "created_at": "2026-03-13T17:05:00+00:00"
}
```

> If content is identical to the latest version, the API returns **409 Conflict**.

---

### 3 — Get Version History

```bash
curl http://127.0.0.1:8000/documents/1/versions
```

Returns an array of all versions in ascending order.

---

### 4 — Compare Two Versions

```bash
curl "http://127.0.0.1:8000/documents/1/compare?v1=1&v2=2"
```

**Response (200)**
```json
{
  "document_id": 1,
  "version_1": 1,
  "version_2": 2,
  "added": [],
  "removed": [],
  "modified": [
    {
      "before": "Payment shall be made within 10 days of invoice.",
      "after":  "Payment shall be made within 30 days of invoice."
    }
  ],
  "summary": "Comparing version 1 → 2: 1 line(s) modified."
}
```

---

### 5 — Update Document Title

```bash
curl -X PATCH http://127.0.0.1:8000/documents/1/title \
  -H "Content-Type: application/json" \
  -d '{"title": "Amended Service Agreement"}'
```

Updates only the title. **No new version is created.**

---

### 6 — Delete a Single Version

```bash
curl -X DELETE http://127.0.0.1:8000/documents/1/versions/2
```

Removes version with `id=2`. Other versions are unaffected.

---

### 7 — Delete Entire Document

```bash
curl -X DELETE "http://127.0.0.1:8000/documents/1?hard=true"
```

The `?hard=true` flag is **required** as a safety guard.
Removes the document and all its versions permanently.

---

## How Versioning Works

```
Document Created
      │
      ▼
  Version 1  ──── SHA-256 hash stored ────┐
      │                                   │
      │  (user uploads new content)       │
      ▼                                   │
  Hash new content ─── matches? ─── YES → 409 Reject
      │ NO
      ▼
  version_number = max(existing) + 1
      │
      ▼
  Version N  saved (immutable) ←─ NEVER overwritten
```

**Key rules:**
- Versions are **append-only** — content is never modified after creation.
- Each version stores `content_hash` (SHA-256) to enable O(1) duplicate detection.
- Version numbers start at 1 and always increment by 1.
- Deleting a version does **not** renumber others (audit integrity).

---

## How Diff Comparison Works

The comparison engine uses Python's built-in `difflib.ndiff()` algorithm.

`ndiff` annotates every line with a prefix:
- `"  "` — line unchanged
- `"- "` — line removed (only in v1)
- `"+ "` — line added (only in v2)
- `"? "` — inline hint (ignored)

**Modified line detection:**
If a removed line (`"- "`) is immediately followed by an added line (`"+ "`), the engine classifies this as a **modification** rather than a separate removal + addition. This produces human-readable output like:

```json
{
  "before": "Payment within 10 days",
  "after":  "Payment within 30 days"
}
```

This approach is far more useful to lawyers than a raw unified diff patch.

---

## Async Notification System

When a new version is saved, the API fires a **FastAPI BackgroundTask** that:

1. Computes a **SequenceMatcher similarity score** between old and new content.
2. If `similarity >= 0.98` → change is trivial → **no notification sent**.
3. If `similarity < 0.98` → change is significant → notification triggered.

```
New version uploaded
        │
        │  (HTTP response returned immediately — user does NOT wait)
        │
        ▼ (background task)
  similarity = SequenceMatcher(old, new).ratio()
        │
        ├─ >= 0.98 → SKIP (trivial change logged)
        │
        └─ < 0.98  → ALERT logged + email placeholder printed
```

In production, replace `_send_email_placeholder()` in `notification_service.py`
with your SMTP / SendGrid / Slack webhook call.

---

## Project Structure

```
smart-legal-document-manager/
│
├── app/
│   ├── main.py                  # FastAPI app, startup, middleware
│   ├── database.py              # SQLAlchemy engine + session + Base
│   ├── models.py                # ORM models: Document, DocumentVersion
│   ├── schemas.py               # Pydantic v2 request/response schemas
│   │
│   ├── routes/
│   │   └── document_routes.py   # All REST endpoints
│   │
│   ├── services/
│   │   ├── document_service.py  # Document CRUD logic
│   │   ├── version_service.py   # Version management + deduplication
│   │   ├── diff_service.py      # difflib-based comparison engine
│   │   └── notification_service.py  # Async change notification
│   │
│   └── utils/
│       └── hash_utils.py        # SHA-256 content hashing
│
├── tests/
│   ├── conftest.py              # In-memory SQLite test fixtures
│   └── test_documents.py        # 8 integration test cases
│
├── requirements.txt
└── README.md
```

---

## Running Tests

```bash
pytest tests/ -v
```

Expected output:

```
tests/test_documents.py::test_create_document_returns_201          PASSED
tests/test_documents.py::test_version_1_auto_created               PASSED
tests/test_documents.py::test_new_version_increments_version_number PASSED
tests/test_documents.py::test_duplicate_content_rejected            PASSED
tests/test_documents.py::test_compare_returns_structured_diff       PASSED
tests/test_documents.py::test_title_patch_does_not_create_new_version PASSED
tests/test_documents.py::test_delete_single_version                 PASSED
tests/test_documents.py::test_hard_delete_removes_document_and_versions PASSED

8 passed in X.XXs
```

Run with coverage:

```bash
pytest tests/ -v --tb=short
```
