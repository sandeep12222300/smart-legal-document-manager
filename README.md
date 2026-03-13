# Smart Legal Document Manager

A professional backend system built with **FastAPI** to help legal professionals manage documents with full version history, track precise changes, and maintain a reliable audit trail.

---

## 1. Project Overview
The **Smart Legal Document Manager** is a specialized version control system for legal documents. In legal environments, every modification is critical. This system ensures:
- **Immutable Versioning**: Every save creates a permanent, unchangeable record.
- **Change Tracking**: Deep inspection of added, removed, or modified clauses.
- **Audit Trails**: A transparent history of who edited the document and when.

---

## 2. Features
- **Document creation with automatic versioning**: Version 1 is automatically initialized upon document creation.
- **Immutable version history**: Historic versions are locked to prevent retroactive tampering.
- **Structured version comparison**: Identifies **added**, **removed**, and **modified** lines between any two versions.
- **Smart notification system**: Analyzes change significance and sends alerts for substantial edits.
- **Metadata updates without creating a new version**: Update titles and global properties without polluting history.
- **Safe deletion of versions and documents**: Guarded deletion endpoints to prevent accidental data loss.
- **REST API built with FastAPI**: High-performance, type-safe API with automatic documentation.
- **Automated tests**: Robust test suite ensuring reliability for critical legal data.

---

## 3. Technology Stack
- **Python**: Core language.
- **FastAPI**: Modern, high-performance web framework.
- **SQLAlchemy**: Database ORM.
- **SQLite (or PostgreSQL)**: Flexible database support (SQLite by default for easy setup).
- **Pydantic**: Data validation and type safety.
- **Pytest**: Industry-standard automated testing.
- **difflib**: Text comparison algorithm.

---

## 4. Project Structure
```text
app/
├── database.py          # Database connection and engine setup
├── models.py            # SQLAlchemy ORM models (Document, Version)
├── schemas.py           # Pydantic models for request/response validation
├── main.py              # Application entry point and lifespan management
├── routes/
│   └── document_routes.py # REST API endpoints
├── services/
│   ├── diff_service.py    # Logic for version comparison
│   ├── document_service.py # Business logic for document management
│   ├── version_service.py  # Logic for handling document versions
│   └── notification_service.py # Smart change notifications
└── utils/
    └── hash_utils.py       # Hashing for duplicate detection

tests/
├── conftest.py          # Test fixtures and memory-DB setup
└── test_documents.py    # API integration tests

requirements.txt         # Project dependencies
README.md                # Documentation
```

---

## 5. Installation Instructions
1. **Clone the repository**:
   ```bash
   git clone https://github.com/bandisandeep/smart-legal-doc-manager.git
   cd smart-legal-doc-manager
   ```
2. **Install dependencies using pip**:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate

   pip install -r requirements.txt
   ```
3. **Start FastAPI server using uvicorn**:
   ```bash
   uvicorn app.main:app --reload
   ```

---

## 6. Running the Server
Run the application with:
```bash
uvicorn app.main:app --reload
```
The API documentation is available at:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 7. User Guide – How to Test Features
Test the system using the built-in **Swagger UI** at `/docs`.

### Creating a Document
- **POST `/documents`**
```json
{
  "title": "Employment Contract",
  "content": "Section 1: Work hours are 9 AM to 5 PM.",
  "author": "Legal Team"
}
```

### Uploading a New Version
- **POST `/documents/{id}/versions`**
```json
{
  "content": "Section 1: Work hours are 9 AM to 6 PM.",
  "author": "HR Director"
}
```

### Listing Versions
- **GET `/documents/{id}/versions`**
Lists all versions, including timestamps, hashes, and authors.

### Comparing Two Versions
- **GET `/documents/{id}/compare?v1=1&v2=2`**
Returns a structured diff showing that "5 PM" was changed to "6 PM".

### Updating Document Title
- **PATCH `/documents/{id}/title`**
```json
{
  "title": "2024 Revised Employment Contract"
}
```

### Deleting a Version
- **DELETE `/documents/{doc_id}/versions/{version_id}`**
Removes a specific version only.

### Deleting a Document
- **DELETE `/documents/{id}?hard=true`**
Removes the entire document and all its history.

---

## 8. Comparison Logic Explanation
The system uses Python's **`difflib`** library to analyze changes between versions.

### Algorithm Behavior:
1. **Added lines**: Lines present in the new version but not the old (prefixed with `+`).
2. **Removed lines**: Lines present in the old version but deleted in the new (prefixed with `-`).
3. **Modified lines**: Detected when a removal is immediately followed by an addition, suggesting an in-place edit of a clause.

The system also calculates a **similarity score** using `SequenceMatcher` (from `difflib`). This score is used by the notification service to ignore "insignificant" edits (e.g., whitespace or minor typos) and only alert users when substantial changes are made.

---

## 9. Running Tests
The project uses `pytest` for quality assurance.
```bash
pytest
```
Tests cover:
- **Document creation**: Verifying initial setup and auto-versioning.
- **Versioning**: Ensuring increments and content integrity.
- **Comparison**: Validating the accuracy of the diff engine.
- **Metadata updates**: Confirming titles can be changed safely.

---

## 10. Future Improvements
- **Authentication**: Implementing user sign-in and role-based access.
- **Email notifications**: Connecting the mock service to a real SMTP or SendGrid provider.
- **Frontend UI**: Building a visual dashboard for legal clerks.
- **Docker deployment**: Creating a `Dockerfile` for easy cloud scaling.
- **Support for large documents**: Optimizing diff processing for extensive filings.

---

## 11. Author
**B Sandeep**
