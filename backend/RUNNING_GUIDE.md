# Running Guide — Generic3 Backend

Django REST Framework backend for a multi-clinic patient management platform.

---

## Prerequisites

- Python 3.9+ (project ships with a `venv` using Python 3.9)
- SQLite (default, no extra setup) or PostgreSQL (via `DATABASE_URL` env var)

---

## How to Run

### 1. Activate the virtual environment

```bash
# From the backend/ directory
source venv/bin/activate
```

### 2. Install dependencies (first time only)

```bash
pip install -r generic3/requirements.txt
```

### 3. Apply database migrations (first time or after model changes)

```bash
cd generic3
python manage.py migrate
```

### 4. Start the development server

```bash
# From backend/generic3/
python manage.py runserver
```

The server starts at **http://127.0.0.1:8000**

To run on a different port (e.g. 8001):

```bash
python manage.py runserver 0.0.0.0:8001
```

### 5. (Optional) Expose via ngrok for external access

```bash
# In a separate terminal
ngrok http 8001
```

Set the generated ngrok URL in your `.env` file as `NGROK_URL` so CORS accepts it.

---

## Environment Variables

Copy `.env.example` to `.env` in the `backend/` directory and fill in the values.

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | insecure dev key | Django secret key |
| `DEBUG` | `True` | Enable debug mode |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,0.0.0.0` | Comma-separated allowed hosts |
| `DATABASE_URL` | _(unset — uses SQLite)_ | PostgreSQL connection string |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated allowed frontend origins |
| `CSRF_TRUSTED_ORIGINS` | _(empty)_ | Trusted origins for CSRF |
| `NGROK_URL` | _(empty)_ | ngrok URL to add to CORS allowed origins |
| `FCM_API_KEY` | _(empty)_ | Firebase Cloud Messaging key (push notifications) |
| `APNS_CERTIFICATE_PATH` | _(empty)_ | Apple push notification certificate |

---

## Base URL

```
http://127.0.0.1:8000/api/v1/
```

All API endpoints are prefixed with `/api/v1/`.

---

## Authentication

The API uses **JWT tokens stored in HTTP-only cookies**.

- Login via `POST /api/v1/auth/sessions/` — sets `access` and `refresh` JWT cookies automatically.
- All subsequent requests use those cookies (no manual token header needed).
- Tokens can also be passed via `Authorization: Bearer <token>` header as a fallback.

**Token lifetimes:**
- Access token: 60 minutes
- Refresh token: 1 day (auto-rotated)

---

## User Roles

| Role | Description |
|---|---|
| `ADMIN` / `is_staff` | Full system access; no clinic context required |
| `CLINIC_MANAGER` | Manages one clinic; most calls need `?clinic_id=` |
| `DOCTOR` | Manages patients in a clinic; needs `?clinic_id=` + `?patient_id=` |
| `PATIENT` / `RESEARCH_PATIENT` | Can only read/create their own data |

---

## All Endpoints

### Authentication — `/api/v1/auth/`

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/auth/sessions/` | Login — sets JWT cookies + returns clinic/module info | No |
| `DELETE` | `/api/v1/auth/sessions/` | Logout — clears JWT cookies | Yes |
| `POST` | `/api/v1/auth/tokens/refresh/` | Refresh access token from cookie | No |
| `POST` | `/api/v1/auth/2fa/` | Request a 2FA code (email/OTP) | No |
| `POST` | `/api/v1/auth/2fa/verify/` | Verify 2FA code and complete login | No |
| `PUT` | `/api/v1/auth/password/` | Change current user's password | Yes |
| `GET` | `/api/v1/auth/users/<user_id>/qr-code/` | Get TOTP QR code for 2FA setup | Yes |

**Login request body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

---

### Users — `/api/v1/users/`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/users/` | List users (paginated, role-filtered) |
| `POST` | `/api/v1/users/` | Create a new user and assign role + clinic |
| `GET` | `/api/v1/users/me/` | Get the currently authenticated user |
| `GET` | `/api/v1/users/<user_id>/` | Get a user by ID |
| `PUT` | `/api/v1/users/<user_id>/` | Update a user |
| `PATCH` | `/api/v1/users/<user_id>/` | Partially update a user |
| `DELETE` | `/api/v1/users/<user_id>/` | Remove user from clinic (non-admin) or hard-delete (admin) |

---

### Clinics — `/api/v1/clinics/`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/clinics/` | List all clinics |
| `POST` | `/api/v1/clinics/` | Create a clinic (with manager + module assignments) |
| `GET` | `/api/v1/clinics/<clinic_id>/` | Get clinic detail |
| `PUT` | `/api/v1/clinics/<clinic_id>/` | Update a clinic |
| `DELETE` | `/api/v1/clinics/<clinic_id>/` | Delete clinic (cascades all related data) |

---

### Modules — `/api/v1/modules/`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/modules/` | List all global modules (staff only) |
| `POST` | `/api/v1/modules/` | Create a module (staff only) |
| `GET/PUT/PATCH/DELETE` | `/api/v1/modules/<module_id>/` | Module detail |
| `GET` | `/api/v1/clinics/<clinic_id>/modules/` | List modules assigned to a clinic |
| `POST` | `/api/v1/clinics/<clinic_id>/modules/` | Add a module to a clinic |
| `GET/PATCH/DELETE` | `/api/v1/clinics/<clinic_id>/modules/<module_id>/` | Toggle active / remove clinic module |
| `GET` | `/api/v1/clinics/<clinic_id>/patients/<patient_id>/modules/` | List patient's modules |
| `POST` | `/api/v1/clinics/<clinic_id>/patients/<patient_id>/modules/` | Add a module for a patient |
| `GET/PATCH/DELETE` | `/api/v1/clinics/<clinic_id>/patients/<patient_id>/modules/<module_id>/` | Toggle active / remove patient module |

---

### Medications — `/api/v1/medications/`

Context is determined by query parameters, not URL structure.

| Method | Endpoint | Query Params | Who | Description |
|---|---|---|---|---|
| `GET` | `/api/v1/medications/` | _(none)_ | Admin | All medicines in the system |
| `GET` | `/api/v1/medications/` | `?clinic_id=` | Clinic Manager / Doctor | Clinic medicine catalogue |
| `GET` | `/api/v1/medications/` | `?clinic_id=&patient_id=` | Doctor | Patient prescriptions |
| `POST` | `/api/v1/medications/` | _(none)_ | Admin | Create a new base medicine record |
| `POST` | `/api/v1/medications/` | _(body has clinic_id)_ | Clinic Manager | Register medicine to clinic |
| `POST` | `/api/v1/medications/` | _(body has clinic+patient)_ | Doctor | Prescribe medicine to patient |
| `GET` | `/api/v1/medications/<id>/` | `?clinic_id=&patient_id=` | Doctor / Patient | Patient prescription detail |
| `PUT` | `/api/v1/medications/<id>/` | `?clinic_id=&patient_id=` | Doctor | Update prescription |
| `DELETE` | `/api/v1/medications/<id>/` | _(none)_ | Admin | Hard-delete medicine |
| `DELETE` | `/api/v1/medications/<id>/` | `?clinic_id=` | Clinic Manager | Remove from clinic catalogue |
| `DELETE` | `/api/v1/medications/<id>/` | `?clinic_id=&patient_id=` | Doctor | Unassign from patient |

**Medication Bundles:**

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/medications/bundles/` | List bundles (scope by query params) |
| `POST` | `/api/v1/medications/bundles/` | Create a bundle |
| `GET/PUT/DELETE` | `/api/v1/medications/bundles/<id>/` | Bundle detail |

Bundle POST body:
```json
{
  "bundle_name": "Hypertension Pack",
  "medication_ids": [1000000001, 1000000002]
}
```

**Medication Reports:**

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/medication-reports/` | List medication reports (scope by query params) |
| `POST` | `/api/v1/medication-reports/?clinic_id=3&patient_id=7` | Log a medication taken |

Report POST body:
```json
{
  "medication_id": 1000000001,
  "timestamp": "2026-02-21T08:00:00Z"
}
```

---

### Activities — `/api/v1/activities/`

Same pattern as medications — context is set via query parameters.

| Method | Endpoint | Query Params | Who | Description |
|---|---|---|---|---|
| `GET` | `/api/v1/activities/` | _(none)_ | Admin | All activities in the system |
| `GET` | `/api/v1/activities/` | `?clinic_id=` | Clinic Manager / Doctor | Clinic activity list |
| `GET` | `/api/v1/activities/` | `?clinic_id=&patient_id=` | Doctor | Patient assigned activities |
| `POST` | `/api/v1/activities/` | _(none)_ | Admin | Create a new activity |
| `POST` | `/api/v1/activities/` | _(body has clinic_id)_ | Clinic Manager | Register activity to clinic |
| `POST` | `/api/v1/activities/` | _(body has clinic+patient)_ | Doctor | Assign activity to patient |
| `GET` | `/api/v1/activities/<id>/` | `?clinic_id=&patient_id=` | Doctor / Patient | Patient activity detail |
| `PUT` | `/api/v1/activities/<id>/` | `?clinic_id=&patient_id=` | Doctor | Update patient assignment |
| `DELETE` | `/api/v1/activities/<id>/` | _(none)_ | Admin | Hard-delete activity |
| `DELETE` | `/api/v1/activities/<id>/` | `?clinic_id=` | Clinic Manager | Unregister from clinic |
| `DELETE` | `/api/v1/activities/<id>/` | `?clinic_id=&patient_id=` | Doctor | Unassign from patient |

**Activity Bundles:**

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/activities/bundles/` | List bundles (scope by query params) |
| `POST` | `/api/v1/activities/bundles/` | Create a bundle |
| `GET/PUT/DELETE` | `/api/v1/activities/bundles/<id>/` | Bundle detail |

Bundle POST body:
```json
{
  "bundle_name": "Morning Routine",
  "activity_ids": [1, 2, 3]
}
```

**Activity Reports:**

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/activity-reports/` | List activity reports (scope by query params) |
| `POST` | `/api/v1/activity-reports/?clinic_id=3&patient_id=7` | Log a completed activity |

Report POST body:
```json
{
  "activity_id": 1,
  "timestamp": "2026-02-21T08:00:00Z"
}
```

---

### Notifications — `/api/v1/notifications/`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/notifications/set/notification/` | Create or update a reminder for a medication / activity / questionnaire |

Request body:
```json
{
  "clinic_id": 3,
  "patient_id": 7,
  "event_type": "medication",
  "event_id": 1000000001,
  "frequency": "daily",
  "frequency_data": {},
  "start_date_time": "2026-02-21T08:00:00Z",
  "end_date_time": "2026-02-28T08:00:00Z"
}
```

`event_type` options: `medication` | `activity` | `questionnaire`
`frequency` options: `once` | `daily` | `weekly` | `monthly`

---

### File Share — `/api/v1/fileshare/`

Files are stored in AWS S3. Configure S3 credentials in `.env`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/fileshare/` | List shared files |
| `POST` | `/api/v1/fileshare/` | Upload a file to S3 |
| `GET` | `/api/v1/fileshare/<id>/` | Download file from S3 (returns base64-encoded) |
| `DELETE` | `/api/v1/fileshare/<id>/` | Delete file from S3 and database |

---

## Pagination

List endpoints are paginated at **20 results per page**.

```
GET /api/v1/users/?page=2
GET /api/v1/users/?page=2&page_size=50   # max 100
```

---

## Common HTTP Status Codes

| Code | Meaning |
|---|---|
| `200` | OK |
| `201` | Created |
| `204` | Deleted (no content) |
| `400` | Bad request / missing fields |
| `401` | Unauthenticated |
| `403` | Forbidden (wrong role or clinic) |
| `404` | Resource not found |

Error responses follow this shape:
```json
{
  "detail": "Error message describing what went wrong."
}
```

---

## Admin Panel

The Django admin is available at:

```
http://127.0.0.1:8000/admin/
```

2FA (TOTP) is enforced for admin login. Use the QR-code endpoint to set it up.
