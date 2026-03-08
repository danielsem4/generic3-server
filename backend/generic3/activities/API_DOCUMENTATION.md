# Activities Module API Documentation

## Table of Contents
1. [Activities Endpoints](#activities-endpoints)
2. [Activity Bundles Endpoints](#activity-bundles-endpoints)
3. [Activity Reports Endpoints](#activity-reports-endpoints)

---

## Activities Endpoints

### 1. List/Create Activities
**Endpoint:** `GET/POST /api/v1/activities/`

#### GET - List Activities
Lists activities based on user role and context.

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `clinic_id` | Optional | Filter activities by clinic |
| `patient_id` | Optional | Filter activities by patient (requires clinic_id) |

**User Roles & Behavior:**
- **Admin** (no params): Returns all activities in the system
- **Clinic Manager** (`clinic_id`): Returns all activities available in the clinic
- **Doctor** (`clinic_id`): Returns all activities available in the clinic
- **Doctor** (`clinic_id` + `patient_id`): Returns activities assigned to specific patient
- **Patient** (`clinic_id` + `patient_id`): Returns their own assigned activities

**Response:**
```json
[
  {
    "id": 1,
    "name": "Morning Walk",
    "description": "30 minute walk in the morning"
  }
]
```

**Status Codes:**
- `200 OK`: Success
- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Clinic or patient not found

---

#### POST - Create Activity
Creates a new activity or assigns an activity based on user role.

**Request Body:**
```json
{
  "name": "Morning Walk",
  "description": "30 minute walk in the morning",
  "clinic_id": 1,          // Required for Clinic Manager/Doctor
  "patient_id": 5          // Required for Doctor
}
```

**User Roles & Behavior:**
- **Admin**: Creates a new base activity
- **Clinic Manager**: Adds existing activity to their clinic
- **Doctor**: Assigns existing activity to a patient

**Response:**
```json
{
  "id": 1,
  "name": "Morning Walk",
  "description": "30 minute walk in the morning"
}
```

**Status Codes:**
- `201 Created`: Activity created/assigned successfully
- `400 Bad Request`: Missing required fields
- `404 Not Found`: Activity, clinic, or patient not found

---

### 2. Activity Details
**Endpoint:** `GET/PUT/DELETE /api/v1/activities/{id}/`

#### GET - Get Activity Details
Retrieves activity details based on user role and context.

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `clinic_id` | Conditional | Required for Clinic Manager/Doctor/Patient |
| `patient_id` | Conditional | Required for Doctor/Patient |

**User Roles & Behavior:**
- **Admin** (no params): Returns base activity details
- **Clinic Manager** (`clinic_id`): Returns clinic activity details
- **Doctor/Patient** (`clinic_id` + `patient_id`): Returns patient activity details with schedule

**Response (Patient Activity):**
```json
{
  "id": 1,
  "name": "Morning Walk",
  "description": "30 minute walk",
  "doctor": 3,
  "frequency": "weekly",
  "frequency_data": {
    "dates": [],
    "days": ["monday", "wednesday", "friday"],
    "time": ["08:00", "12:00"]
  },
  "start_date": "2026-01-15 08:00:00",
  "end_date": "2026-02-15 08:00:00"
}
```

**Status Codes:**
- `200 OK`: Success
- `400 Bad Request`: Missing required parameters
- `404 Not Found`: Activity not found

---

#### PUT - Update Activity
Updates activity details or assigns activity to patient.

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `clinic_id` | Conditional | Required for Doctor |
| `patient_id` | Conditional | Required for Doctor |

**Request Body (Admin - Update Activity):**
```json
{
  "name": "Updated Activity Name",
  "description": "Updated description"
}
```

**Request Body (Doctor - Assign/Update Patient Activity):**
```json
{
  "frequency": "weekly",
  "frequency_data": {
    "dates": [],
    "days": ["monday", "wednesday", "friday"],
    "time": ["08:00", "12:00"]
  },
  "start_date": "2026-01-15 08:00:00",
  "end_date": "2026-02-15 08:00:00"
}
```

**User Roles & Behavior:**
- **Admin** (no params): Updates base activity name/description
- **Doctor** (`clinic_id` + `patient_id`): Assigns activity to patient or updates schedule

**Response (Doctor Assignment):**
```json
{
  "detail": "Activity assigned to patient",
  "activity_id": 1,
  "activity_name": "Morning Walk",
  "frequency": "weekly",
  "frequency_data": {...},
  "start_date": "2026-01-15 08:00:00",
  "end_date": "2026-02-15 08:00:00"
}
```

**Status Codes:**
- `200 OK`: Updated successfully
- `201 Created`: Activity assigned to patient
- `403 Forbidden`: Permission denied
- `404 Not Found`: Activity not found

---

#### DELETE - Delete Activity
Deletes activity or removes activity assignment.

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `clinic_id` | Conditional | Required for Clinic Manager/Doctor |
| `patient_id` | Conditional | Required for Doctor |

**User Roles & Behavior:**
- **Admin** (no params): Deletes base activity
- **Clinic Manager** (`clinic_id`): Removes activity from clinic
- **Doctor** (`clinic_id` + `patient_id`): Removes activity from patient

**Response:**
```json
{
  "detail": "Activity removed from patient successfully"
}
```

**Status Codes:**
- `204 No Content`: Deleted successfully
- `400 Bad Request`: Missing required parameters
- `404 Not Found`: Activity not found

---

## Activity Bundles Endpoints

### 3. List/Create Bundles
**Endpoint:** `GET/POST /api/v1/activities/bundles/`

#### GET - List Bundles
Lists activity bundles based on user role and context.

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `clinic_id` | Optional | Filter bundles by clinic |
| `patient_id` | Optional | Show patient's assigned bundles (requires clinic_id) |

**User Roles & Behavior:**
- **Admin** (no params): Returns all bundles across all clinics
- **Clinic Manager** (`clinic_id`): Returns all bundles in the clinic
- **Doctor** (`clinic_id`): Returns all bundles in the clinic
- **Doctor** (`clinic_id` + `patient_id`): Returns bundles assigned to patient
- **Patient** (`clinic_id` + `patient_id`): Returns their own assigned bundles

**Response (Clinic Bundles):**
```json
[
  {
    "id": 1,
    "bundle_name": "Morning Routine",
    "activities": [
      {
        "id": 1,
        "name": "Morning Walk",
        "description": "30 minute walk"
      },
      {
        "id": 2,
        "name": "Stretching",
        "description": "15 minute stretching"
      }
    ]
  }
]
```

**Response (Patient Bundles):**
```json
[
  {
    "id": 1,
    "bundle_name": "Morning Routine",
    "doctor_id": 3,
    "doctor_name": "Dr. John Smith",
    "activities": [...]
  }
]
```

**Status Codes:**
- `200 OK`: Success
- `400 Bad Request`: Missing required parameters
- `403 Forbidden`: Access denied

---

#### POST - Create Bundle
Creates a new activity bundle.

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `clinic_id` | Yes | Clinic where bundle will be created |

**Request Body:**
```json
{
  "bundle_name": "Morning Routine",
  "activity_ids": [1, 2, 3]
}
```

**User Roles:**
- **Admin**: Can create bundles
- **Clinic Manager**: Can create bundles for their clinic

**Response:**
```json
{
  "id": 1,
  "bundle_name": "Morning Routine",
  "activities": [
    {"id": 1, "name": "Morning Walk"},
    {"id": 2, "name": "Stretching"}
  ]
}
```

**Status Codes:**
- `201 Created`: Bundle created successfully
- `400 Bad Request`: Missing fields or invalid activity IDs
- `404 Not Found`: Some activities not found

---

### 4. Bundle Details
**Endpoint:** `GET/PUT/DELETE /api/v1/activities/bundles/{id}/`

#### GET - Get Bundle Details
Retrieves bundle details based on user role.

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `clinic_id` | Conditional | Required for Clinic Manager/Doctor |

**User Roles & Behavior:**
- **Admin** (no params): Views any bundle
- **Clinic Manager** (`clinic_id`): Views bundle in their clinic
- **Doctor** (`clinic_id`): Views bundle in their clinic

**Response:**
```json
{
  "id": 1,
  "bundle_name": "Morning Routine",
  "activities": [
    {
      "id": 1,
      "name": "Morning Walk",
      "description": "30 minute walk"
    }
  ]
}
```

**Status Codes:**
- `200 OK`: Success
- `404 Not Found`: Bundle not found

---

#### PUT - Update Bundle or Assign to Patient
Updates bundle details or assigns bundle to patient.

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `clinic_id` | Conditional | Required for Clinic Manager/Doctor |
| `patient_id` | Conditional | Required for Doctor (assignment) |

**Request Body (Admin/Clinic Manager - Update Bundle):**
```json
{
  "bundle_name": "Updated Morning Routine",
  "activity_ids": [1, 2, 3, 4]
}
```

**Request Body (Doctor - Assign to Patient):**
```json
// Empty body - assignment based on query params
{}
```

**User Roles & Behavior:**
- **Admin/Clinic Manager** (no `patient_id`): Updates bundle name and activities
- **Doctor** (`clinic_id` + `patient_id`): Assigns bundle to patient

**Response (Doctor Assignment):**
```json
{
  "detail": "Bundle assigned to patient",
  "bundle_id": 1,
  "bundle_name": "Morning Routine"
}
```

**Status Codes:**
- `200 OK`: Updated or already assigned
- `201 Created`: Bundle assigned to patient
- `403 Forbidden`: Permission denied
- `404 Not Found`: Bundle not found

---

#### DELETE - Delete Bundle or Remove Assignment
Deletes bundle or removes bundle from patient.

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `clinic_id` | Conditional | Required for Clinic Manager/Doctor |
| `patient_id` | Conditional | Required for Doctor (removal) |

**User Roles & Behavior:**
- **Admin** (no params): Deletes bundle entirely
- **Clinic Manager** (`clinic_id`): Deletes bundle from clinic
- **Doctor** (`clinic_id` + `patient_id`): Removes bundle from patient

**Response:**
```json
{
  "detail": "Bundle removed from patient successfully"
}
```

**Status Codes:**
- `204 No Content`: Deleted successfully
- `404 Not Found`: Bundle not found

---

## Activity Reports Endpoints

### 5. List/Create Activity Reports
**Endpoint:** `GET/POST /api/v1/activity-reports/`

#### GET - List Activity Reports
Lists activity completion reports based on user role.

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `clinic_id` | Conditional | Required for non-admin users |
| `patient_id` | Conditional | Required for Doctor/Patient |

**User Roles & Behavior:**
- **Admin** (no params): Returns all reports across all clinics
- **Clinic Manager** (`clinic_id`): Returns all reports in their clinic
- **Doctor** (`clinic_id` + `patient_id`): Returns reports for specific patient (must be assigned)
- **Patient** (`clinic_id` + `patient_id`): Returns their own reports

**Response (Admin/Clinic Manager):**
```json
[
  {
    "id": 1,
    "activity": {
      "id": 3,
      "name": "Morning Walk",
      "description": "30 minute walk"
    },
    "patient": {
      "user_id": 5,
      "name": "John Doe"
    },
    "clinic": {
      "id": 1,
      "name": "Wellness Clinic"
    },
    "timestamp": "2026-01-14 10:30:00"
  }
]
```

**Response (Doctor/Patient):**
```json
[
  {
    "id": 1,
    "activity": {
      "id": 3,
      "name": "Morning Walk",
      "description": "30 minute walk"
    },
    "timestamp": "2026-01-14 10:30:00"
  }
]
```

**Status Codes:**
- `200 OK`: Success
- `400 Bad Request`: Missing required parameters
- `403 Forbidden`: Access denied

---

#### POST - Create Activity Report
Logs completion of an activity (typically called by patients).

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `clinic_id` | Yes | Clinic context |
| `patient_id` | Yes | Patient who completed activity |

**Request Body:**
```json
{
  "activity_id": 3,
  "timestamp": "2026-01-14 10:30:00"  // Optional - defaults to now
}
```

**Validations:**
- Activity must be assigned to the patient
- Patients can only create reports for themselves
- Timestamp format: "YYYY-MM-DD HH:MM:SS"

**Response:**
```json
{
  "detail": "Activity report created successfully"
}
```

**Status Codes:**
- `201 Created`: Report created successfully
- `400 Bad Request`: Missing required fields or invalid timestamp
- `403 Forbidden`: Patient not authorized
- `404 Not Found`: Activity not assigned to patient

---

## Common Error Responses

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "detail": "Permission denied"
}
```

### 404 Not Found
```json
{
  "detail": "Activity not found"
}
```

### 400 Bad Request
```json
{
  "detail": "Name and description are required"
}
```

---

## Frequency Data Structure

When assigning activities or bundles to patients, the `frequency_data` field follows this structure:

### Once (no frequency data needed)
```json
{
  "frequency": "once"
}
```

### Daily
```json
{
  "frequency": "daily",
  "frequency_data": {
    "dates": [],
    "days": [],
    "time": ["08:00", "20:00"]
  }
}
```

### Weekly
```json
{
  "frequency": "weekly",
  "frequency_data": {
    "dates": [],
    "days": ["monday", "wednesday", "friday"],
    "time": ["08:00"]
  }
}
```

### Monthly
```json
{
  "frequency": "monthly",
  "frequency_data": {
    "dates": ["2026-01-01", "2026-01-15"],
    "days": [],
    "time": ["08:00"]
  }
}
```

---

## Permission Summary

| Endpoint | Admin | Clinic Manager | Doctor | Patient |
|----------|-------|----------------|--------|---------|
| GET /activities/ | All activities | Clinic activities | Clinic/Patient activities | Own activities |
| POST /activities/ | Create base activity | Add to clinic | Assign to patient | ❌ |
| GET /activities/{id}/ | Base activity | Clinic activity | Patient activity | Own activity |
| PUT /activities/{id}/ | Update activity | ❌ | Assign/Update patient | ❌ |
| DELETE /activities/{id}/ | Delete activity | Remove from clinic | Remove from patient | ❌ |
| GET /bundles/ | All bundles | Clinic bundles | Clinic/Patient bundles | Own bundles |
| POST /bundles/ | Create bundle | Create bundle | ❌ | ❌ |
| GET /bundles/{id}/ | Any bundle | Clinic bundle | Clinic bundle | ❌ |
| PUT /bundles/{id}/ | Update bundle | Update bundle | Assign to patient | ❌ |
| DELETE /bundles/{id}/ | Delete bundle | Delete bundle | Remove from patient | ❌ |
| GET /activity-reports/ | All reports | Clinic reports | Patient reports | Own reports |
| POST /activity-reports/ | ✓ | ✓ | ✓ | Create own report |

---

## Notes

1. **Query Parameters**: Context parameters (clinic_id, patient_id) are always passed as query parameters
2. **Request Body**: Actual data (name, description, activity_ids, etc.) are passed in the request body
3. **Authentication**: All endpoints require authentication
4. **Timestamps**: All timestamps are in format "YYYY-MM-DD HH:MM:SS"
5. **Patient Authorization**: Patients can only access their own data
6. **Doctor Authorization**: Doctors can only access patients assigned to them
