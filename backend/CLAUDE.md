# CLAUDE.md — Backend API Reference

Django REST Framework backend for a multi-clinic patient management platform.
All endpoints are prefixed with the base URL configured in `generic3/urls.py`.
Authentication is JWT via HTTP-only cookies (custom `CookieJWTAuthentication`).

---

## Project Layout

```
backend/generic3/
├── generic3/          # Project config (settings.py, urls.py)
├── authentication/    # JWT sessions, 2FA, password management
├── users/             # User CRUD, role profiles
├── clinics/           # Clinic management
├── modules/           # Clinic & patient module toggles
├── medications/       # Medicines, patient assignments, bundles, reports
├── activities/        # Activities, patient assignments, bundles, reports
├── notifications/     # Event notification settings + push message templates
├── fileshare/         # S3-backed file sharing between doctors and patients
└── questionnaires/    # Questionnaire framework (stub — returns empty list)
```

---

## User Roles

| Role | Description |
|---|---|
| `ADMIN` / `is_staff` | Full system access, no clinic context required |
| `CLINIC_MANAGER` | Manages one clinic; needs `?clinic_id=` on most calls |
| `DOCTOR` | Manages patients within a clinic; needs `?clinic_id=` + `?patient_id=` |
| `PATIENT` / `RESEARCH_PATIENT` | Read/create own data only |

The role is stored on `users.User.role`. Profile objects (`Doctor`, `Patient`, `ClinicManager`) are one-to-one extensions of `User`.

---

## Authentication

| Method | Path | Description |
|---|---|---|
| `POST` | `api/v1/auth/sessions/` | Login — returns JWT tokens via cookies + clinic/module data |
| `DELETE` | `api/v1/auth/sessions/` | Logout — clears JWT cookies |
| `POST` | `api/v1/auth/tokens/refresh/` | Refresh access token from cookie |
| `POST` | `api/v1/auth/2fa/` | Request 2FA code (email/OTP) |
| `POST` | `api/v1/auth/2fa/verify/` | Verify 2FA code and complete login |
| `PUT` | `api/v1/auth/password/` | Change password |
| `GET` | `api/v1/auth/users/<user_id>/qr-code/` | Get TOTP QR code for 2FA setup |

---

## Activities

Source: `activities/views.py`, `activities/urls.py`

### Core CRUD — `api/v1/activities/`

| Method | Path | Who | Behaviour |
|---|---|---|---|
| `GET` | `api/v1/activities/` | Admin | All activities in the system |
| `GET` | `api/v1/activities/?clinic_id=` | Doctor / Clinic Manager | All activities registered to that clinic |
| `GET` | `api/v1/activities/?clinic_id=&patient_id=` | Doctor | Only activities assigned to that patient by the requesting doctor |
| `POST` | `api/v1/activities/` | Admin | Create a new base `Activity` record (name + description must be unique) |
| `POST` | `api/v1/activities/` | Clinic Manager | Register an existing activity to a clinic (`ClinicActivity`) |
| `POST` | `api/v1/activities/` | Doctor | Assign a clinic activity to a patient (`PatientActivity`) |

Body for Admin POST:
```json
{ "name": "string", "description": "string" }
```

Body for Clinic Manager POST:
```json
{ "clinic_id": 1, "name": "string", "description": "string" }
```

Body for Doctor POST:
```json
{ "clinic_id": 1, "patient_id": 7, "name": "string", "description": "string" }
```

### Detail — `api/v1/activities/<id>/`

| Method | Query Params | Who | Behaviour |
|---|---|---|---|
| `GET` | _(none)_ | Admin | Base activity record |
| `GET` | `?clinic_id=` | Clinic Manager | Clinic-scoped activity |
| `GET` | `?clinic_id=&patient_id=` | Doctor / Patient | Patient assignment with `frequency`, `frequency_data`, `start_date`, `end_date` |
| `PUT` | _(none)_ | Admin | Update `name` / `description` on the base record |
| `PUT` | `?clinic_id=&patient_id=` | Doctor | `get_or_create` a `PatientActivity`; update frequency/schedule fields |
| `DELETE` | _(none)_ | Admin | Hard-delete base `Activity` |
| `DELETE` | `?clinic_id=` | Clinic Manager | Remove `ClinicActivity` (unregister from clinic) |
| `DELETE` | `?clinic_id=&patient_id=` | Doctor | Remove `PatientActivity` (unassign from patient) |

---

## Activity Bundles

### List — `api/v1/activities/bundles/`

| Method | Query Params | Who | Behaviour |
|---|---|---|---|
| `GET` | _(none)_ | Admin | All bundles across all clinics (includes `clinic_id`, `clinic_name`) |
| `GET` | `?clinic_id=` | Any | All bundles belonging to that clinic |
| `GET` | `?clinic_id=&patient_id=` | Doctor | Bundles assigned to that patient; verifies `PatientDoctor` relationship |
| `GET` | `?clinic_id=&patient_id=` | Patient | Own bundles only; identity check enforced |
| `POST` | `?clinic_id=` | Admin / Clinic Manager | Create a new `ActivitiesBundle` |

POST body:
```json
{
  "bundle_name": "Morning Routine",
  "activity_ids": [1, 2, 3]
}
```

All activities in `activity_ids` must already exist as `ClinicActivity` entries for the target clinic.

Response shape (patient bundles):
```json
[
  {
    "id": 1,
    "bundle_name": "Morning Routine",
    "doctor_id": 5,
    "doctor_name": "Dr. Jane Smith",
    "activities": [
      { "id": 1, "name": "Walk", "description": "30-min walk" }
    ]
  }
]
```

### Detail — `api/v1/activities/bundles/<id>/`

| Method | Query Params | Who | Behaviour |
|---|---|---|---|
| `GET` | _(none)_ | Admin | Bundle + clinic metadata |
| `GET` | `?clinic_id=` | Clinic Manager / Doctor | Bundle scoped to clinic (ownership check) |
| `PUT` | _(none or `?clinic_id=`)_ | Admin / Clinic Manager | Update `bundle_name` and/or replace `activity_ids` |
| `PUT` | `?clinic_id=&patient_id=` | Doctor | `get_or_create` a `PatientActivitiesBundle` (assign to patient) |
| `DELETE` | _(none)_ | Admin | Hard-delete bundle |
| `DELETE` | `?clinic_id=` | Clinic Manager | Delete clinic's bundle |
| `DELETE` | `?clinic_id=&patient_id=` | Doctor | Remove `PatientActivitiesBundle` |

---

## Activity Reports

Source: `activities/views.py` — `activity_reports()`

Path: `api/v1/activity-reports/`
Query params are used for context on both GET and POST; the POST body carries the payload.

### GET Filtering by Role

| Role | Required Query Params | Filter Applied |
|---|---|---|
| Admin | _(none)_ | All `ActivityReport` rows across the system |
| Clinic Manager | `?clinic_id=` | Reports for that clinic |
| Doctor | `?clinic_id=&patient_id=` | Reports for that patient in that clinic; `PatientDoctor` relationship verified |
| Patient / Research Patient | `?clinic_id=&patient_id=` | Own reports only; identity check (`patient.user == request.user`) |

Response shape:
```json
{
  "id": 42,
  "activity": { "id": 1, "name": "Walk", "description": "..." },
  "patient": { "user_id": 7, "name": "John Doe" },   // Admin/Clinic Manager only
  "clinic":  { "id": 3, "name": "City Clinic" },      // Admin only
  "timestamp": "2026-02-21T08:00:00Z"
}
```

### POST — Log a Completed Activity

```
POST api/v1/activity-reports/?clinic_id=3&patient_id=7
```

Body:
```json
{
  "activity_id": 1,
  "timestamp": "2026-02-21T08:00:00Z"   // optional; defaults to now
}
```

Rules:
- Patient can only create reports for themselves (identity enforced).
- The activity must be assigned to the patient via `PatientActivity` in that clinic.

---

## Medications

Source: `medications/views.py`, `medications/urls.py`

### Core CRUD — `api/v1/medications/`

Mirrors the activities pattern exactly, but the model is `Medicines` (fields: `medName`, `medForm`, `medUnitOfMeasurement`).

| Method | Path | Who | Behaviour |
|---|---|---|---|
| `GET` | `api/v1/medications/` | Admin | All `Medicines` in the system |
| `GET` | `api/v1/medications/?clinic_id=` | Doctor / Clinic Manager | Clinic catalogue (`ClinicMedicine`) |
| `GET` | `api/v1/medications/?clinic_id=&patient_id=` | Doctor | Patient prescriptions via `PatientMedicine` |
| `POST` | `api/v1/medications/` | Admin | Create new base `Medicines` record |
| `POST` | `api/v1/medications/` | Clinic Manager | Register medicine to clinic (`ClinicMedicine`) |
| `POST` | `api/v1/medications/` | Doctor | Assign medicine to patient (`PatientMedicine`) |

Body for Admin POST:
```json
{ "medication_name": "string", "medication_form": "string", "medication_unit": "string" }
```

Body for Doctor POST adds `clinic_id` and `patient_id`.

### Detail — `api/v1/medications/<id>/`

Same permission pattern as activities detail:

| Method | Params | Who | Behaviour |
|---|---|---|---|
| `GET` | _(none)_ | Admin | Base `Medicines` record |
| `GET` | `?clinic_id=` | Clinic Manager | Clinic-scoped |
| `GET` | `?clinic_id=&patient_id=` | Doctor / Patient | `PatientMedicine` with `frequency`, `dosage`, `start_date`, `end_date` |
| `PUT` | _(none)_ | Admin | Update `name`, `form`, `unit` |
| `PUT` | `?clinic_id=&patient_id=` | Doctor | `get_or_create` `PatientMedicine`; update frequency/schedule/dosage |
| `DELETE` | _(none)_ | Admin | Hard-delete `Medicines` |
| `DELETE` | `?clinic_id=` | Clinic Manager | Remove from clinic catalogue |
| `DELETE` | `?clinic_id=&patient_id=` | Doctor | Unassign from patient |

---

## Medication Bundles

Path: `api/v1/medications/bundles/` and `api/v1/medications/bundles/<id>/`

Structure and permission rules are identical to Activity Bundles.

POST body uses `medication_ids` instead of `activity_ids`:
```json
{
  "bundle_name": "Hypertension Pack",
  "medication_ids": [1000000001, 1000000002]
}
```

Note: `Medicines.id` is a `CharField` auto-incremented from `1000000000`.

Bundle model: `MedicationsBundle` (fields: `bundle_name`, `clinic`, `medicines` M2M).
Patient assignment: `PatientMedicationsBundle` (links `patient`, `bundle`, `doctor`).

---

## Medication Reports

Path: `api/v1/medication-reports/`

Same structure as Activity Reports. Patients POST when they take a medication.

### GET Filtering by Role

| Role | Required Query Params | Filter |
|---|---|---|
| Admin | _(none)_ | All `MedicationReport` rows |
| Clinic Manager | `?clinic_id=` | Reports for that clinic |
| Doctor | `?clinic_id=&patient_id=` | Reports for that patient; `PatientDoctor` verified |
| Patient / Research Patient | `?clinic_id=&patient_id=` | Own reports; identity enforced |

### POST — Log a Medication Taken

```
POST api/v1/medication-reports/?clinic_id=3&patient_id=7
```

Body:
```json
{
  "medication_id": 1000000001,
  "timestamp": "2026-02-21T08:00:00Z"   // optional
}
```

The medication must be assigned to the patient via `PatientMedicine` in that clinic.

---

## Reminder / Notification System

There are **no standalone `/remind/` endpoints** on the activities or medications routes.
Reminder scheduling is handled entirely through the notifications app.

### Set Event Notification

```
POST api/v1/notifications/set/notification/
```

Body (all fields in request body, not query params):
```json
{
  "clinic_id": 3,
  "patient_id": 7,
  "event_type": "medication",          // "medication" | "activity" | "questionnaire"
  "event_id": 1000000001,              // ID of the medication / activity / questionnaire
  "frequency": "daily",                // "once" | "daily" | "weekly" | "monthly"
  "frequency_data": {},
  "start_date_time": "2026-02-21T08:00:00Z",
  "end_date_time": "2026-02-28T08:00:00Z"
}
```

Behaviour:
- Validates that the `event_id` is assigned to the patient in the clinic (for medication/activity types).
- If a notification already exists for `(clinic, patient, event_type, event_id)`, it is updated. Otherwise a new `EventNotificationSettings` row is created.
- `frequency` and `frequency_data` default to `"once"` / `[]` if omitted.
- `start_date_time` defaults to `now()`; `end_date_time` defaults to `now() + 1 day`.
- Actual push dispatch is stubbed (`# Notification logic would go here`).

### Notification Message Templates

`notifications/utils.py` — `generate_notification_message(type, **kwargs)`:

| `type` | Title | Message |
|---|---|---|
| `medication_reminder` | "Medication Reminder" | "Time to take {medication_name}." |
| `activity_reminder` | "Activity Reminder" | "Time to perform {activity_name}." |
| `file_shared` | "{sender} has shared a file(s) with you." | Full file-name list message |

These templates are ready for integration with a push notification sender (FCM/APNS packages installed).

---

## Other Endpoints

### Users — `api/v1/users/`

| Method | Path | Description |
|---|---|---|
| `GET` | `api/v1/users/` | List users (paginated, role-filtered) |
| `POST` | `api/v1/users/` | Create user + assign role profile + clinic |
| `GET` | `api/v1/users/me/` | Current authenticated user |
| `GET/PUT/PATCH/DELETE` | `api/v1/users/<user_id>/` | User detail; DELETE removes from clinic (non-admin) or hard-deletes (admin) |

### Clinics — `api/v1/clinics/`

| Method | Path | Description |
|---|---|---|
| `GET/POST` | `api/v1/clinics/` | List all / Create clinic (with manager + module assignments) |
| `GET/PUT/DELETE` | `api/v1/clinics/<clinic_id>/` | Clinic detail; DELETE cascades all related data |

### Modules — `api/v1/modules/`

| Method | Path | Description |
|---|---|---|
| `GET/POST` | `api/v1/modules/` | Global module list / create (staff only) |
| `GET/PUT/PATCH/DELETE` | `api/v1/modules/<module_id>/` | Module detail |
| `GET/POST` | `api/v1/clinics/<clinic_id>/modules/` | Clinic module list / add |
| `GET/PATCH/DELETE` | `api/v1/clinics/<clinic_id>/modules/<module_id>/` | Toggle active / remove |
| `GET/POST` | `api/v1/clinics/<clinic_id>/patients/<patient_id>/modules/` | Patient module list / add |
| `GET/PATCH/DELETE` | `api/v1/clinics/<clinic_id>/patients/<patient_id>/modules/<module_id>/` | Toggle active / remove |

### File Share — `api/v1/fileshare/`

| Method | Path | Description |
|---|---|---|
| `GET/POST` | `api/v1/fileshare/` | List files / Upload to S3 (doctor or patient) |
| `GET` | `api/v1/fileshare/<id>/` | Retrieve file from S3 (base64-encoded) |
| `DELETE` | `api/v1/fileshare/<id>/` | Delete from S3 and DB |

---

## Data Models — Quick Reference

### Frequency Options (shared across medications, activities, notifications)

`once` | `daily` | `weekly` | `monthly`

Complex schedules are stored as freeform JSON in `frequency_data`.

### PatientActivity / PatientMedicine Fields

```
activity / medicine  → FK to Activity / Medicines
patient              → FK to Patient
doctor               → FK to Doctor
clinic               → FK to Clinic
frequency            → CharField (choices above)
frequency_data       → JSONField
start_date           → DateTimeField
end_date             → DateTimeField (default: 2100-01-01)
dosage               → CharField (medications only)
```

### Bundle Structure

```
ActivitiesBundle / MedicationsBundle
  bundle_name  → CharField
  clinic       → FK to Clinic
  activities / medicines → ManyToManyField

PatientActivitiesBundle / PatientMedicationsBundle
  patient   → FK to Patient
  bundle    → FK to bundle above
  doctor    → FK to Doctor
```

### Report Fields

```
ActivityReport / MedicationReport
  clinic     → FK to Clinic
  patient    → FK to Patient
  activity / medication → FK to Activity / Medicines
  timestamp  → DateTimeField (auto_now_add for ActivityReport)
```

---

## Global Query-Param Conventions

Most list and detail views read `clinic_id` and `patient_id` from **query parameters** (`request.GET`), not from the URL path. POST/PUT bodies carry the resource payload separately.

```
GET  api/v1/activities/?clinic_id=3&patient_id=7
POST api/v1/activity-reports/?clinic_id=3&patient_id=7
     Body: { "activity_id": 1 }
```

---

## Settings Highlights

- `AUTH_USER_MODEL = 'users.User'`
- `REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES`: `CookieJWTAuthentication`, `JWTAuthentication`
- `REST_FRAMEWORK.DEFAULT_PERMISSION_CLASSES`: `IsAuthenticated`
- Pagination: 20 per page (configurable via `?page_size=`, max 100)
- JWT access token lifetime: 60 minutes; refresh: 1 day
- CORS: `http://localhost:5173`, `http://127.0.0.1:5173` with credentials
- Database: SQLite in dev; PostgreSQL via `DATABASE_URL` env var
- File storage: AWS S3 (fileshare app)
