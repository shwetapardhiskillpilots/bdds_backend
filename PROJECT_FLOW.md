# Project Flow & Change Log

This document tracks the application flow, architecture, and structural changes for the **BDDS FastAPI Mirror**.

## 🏗️ Architecture Overview

The project is built using **FastAPI** with **SQLAlchemy** for database interactions. It serves as a mirror for a Django-based system, maintaining compatible API paths and data structures.

### Directory Structure
- `main.py`: Application entry point, router inclusion, and middleware configuration.
- `routers/`: Directory containing endpoint definitions, grouped by functional area.
- `models.py`: SQLAlchemy database models.
- `schemas.py`: Pydantic models for request/response validation.
- `database.py`: Database connection and engine configuration.
- `auth.py`: Authentication logic and dependency injection.

---

## 🌊 Application Flow

1.  **Entry Point (`main.py`)**:
    - Initializes the `FastAPI` application.
    - Configures CORS middleware.
    - Mounts the `/media` static file directory.
    - Includes routers from the `routers/` package.
    - Warmed up the DB connection pool on startup for performance.

2.  **Routing (`routers/`)**:
    - Request paths are routed to specific modules:
        - `/auth`: Authentication and user login.
        - `/master`: Master data management.
        - `/form`: Dynamic form processing.
        - `/media`: Media file handling.
        - `/dashboard`: Dashboard metrics and visualizations.
        - `/admin`: Administrative functions.

3.  **Data Layer**:
    - **Schemas**: Request data is validated against Pydantic models in `schemas.py`.
    - **Models**: Business logic interacts with the database via SQLAlchemy models in `models.py`.
    - **Database**: The `database.py` module manages the connection to the underlying DB.

---

## 📝 Change Log

### [2026-02-28] - Location Management APIs
- Added `updlocation` and `dlocation` endpoints to the master router.
- Supports updating location names and deleting location records.
- Prefixed with `/api_proxy/` to match frontend expectations.

### [2026-02-28] - Cloudflare Tunneling Enabled
- Installed `cloudflared` and configured a Quick Tunnel to expose the local server.
- Public URL: `https://circle-jan-manager-m-electric.trycloudflare.com`

### [2026-02-28] - SP Authority API & Credentials
- Implemented a new router `sp_authority.py` for managing special authority credentials.
- Added endpoints: `GET /sp-authority/` (list) and `POST /sp-authority/` (create).
- Added corresponding validation and response schemas in `schemas.py`.

### [2026-02-28] - Stability & Consistency Fixes
- Fixed `DataError` in `formapi` by correctly passing `user_id` as an integer rather than an object.
- Renamed all authentication dependencies to `current_user: AuthUser` for clarity and consistency across `form.py`, `master.py`, and `auth.py`.
- Resolved `NameError` in `form.py` by ensuring all required models are imported.

### [2026-02-28] - Profile Update Added & Fixed
- Updated the `/profile/` endpoint in `auth.py` to support data updates via POST.
- Fixed a `500 Internal Server Error` (InvalidRequestError) by ensuring the user instance is attached to the current session before refreshing (critical for token-cached users).
- Now correctly updates both `AuthUser` and its associated `Nlogines_creations` record.

### [2026-02-28] - User Profile Endpoint
- Added `/profile/` endpoint in `auth.py` to get current user details.
- Includes basic auth info and extended metadata from `Nlogines_creations`.

### [2026-02-28] - Pagination Added (Base Preserving)
- Implemented optional pagination on the `/listonly` endpoint in `form.py` *without* changing the function signature.
- Added support for `offset` and `limit` (max 25) extracted directly from the request.
- Preserves "base code" behavior: if no `limit` is provided, all records are returned.
- Compatible with both query parameters (GET) and JSON body (POST).

### [2026-02-28] - Initial Setup
- Created `PROJECT_FLOW.md` to track project architecture and changes.
- Documented the current application flow and component structure.

---

## 🚀 Upcoming Tasks
- [ ] Maintain consistent documentation for all new endpoints.
- [ ] Track major refactors or database schema changes here.
