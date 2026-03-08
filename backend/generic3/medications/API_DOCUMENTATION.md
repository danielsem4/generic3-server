# Medications Module API Documentation

## Table of Contents
1. [Medications Endpoints](#medications-endpoints)
2. [Medication Bundles Endpoints](#medication-bundles-endpoints)
3. [Medication Reports Endpoints](#medication-reports-endpoints)

---

## Medications Endpoints

### 1. List/Create Medications
**Endpoint:** `GET/POST /api/v1/medications/`

#### GET - List Medications
Lists medications based on user role and context.

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `clinic_id` | Optional | Filter medications by clinic |
| `patient_id` | Optional | Filter medications by patient (requires clinic_id) |

**User Roles & Behavior:**
- **Admin** (no params): Returns all medications in the system
- **Clinic Manager** (`clinic_id`): Returns all medications available in the clinic
- **Doctor** (`clinic_id`): Returns all medications available in the clinic
- **Doctor** (`clinic_id` + `patient_id`): Returns medications assigned to specific patient
- **Patient** (`clinic_id` + `patient_id`): Returns their own assigned medications

**Response:**
```json
[
  {
    "id": "1000007960",
    "name": "Aspirin",
    "form": "Tablet",
    "unit_of_measurement": "mg"
  }
]
```

**Status Codes:**
- `200 OK`: Success
- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Clinic or patient not found

---

#### POST - Create Medication
Creates a new medication or assigns a medication based on user role.

**Request Body:**
```json
{
  "medication_name": "Aspirin",
  "medication_form": "Tablet",
  "medication_unit": "mg",
  "clinic_id": 1,          // Required for Clinic Manager/Doctor
  "patient_id": 5          // Required for Doctor
}
```

**User Roles & Behavior:**
- **Admin**: Creates a new base medication
- **Clinic Manager**: Adds existing medication to their clinic
- **Doctor**: Assigns existing medication to a patient

**Response:**
```json
{
  "id": "1000007960",
  "name": "Aspirin",
  "form": "Tablet",
  "unit_of_measurement": "mg"
}
```

**Status Codes:**
- `201 Created`: Medication created/assigned successfully
- `400 Bad Request`: Missing required fields or medication already exists
- `404 Not Found`: Medication, clinic, or patient not found

---

### 2. Medication Details
**Endpoint:** `GET/PUT/DELETE /api/v1/medications/{id}/`

#### GET - Get Medication Details
Retrieves medication details based on user role and context.

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `clinic_id` | Conditional | Required for Clinic Manager/Doctor/Patient |
| `patient_id` | Conditional | Required for Doctor/Patient |

**User Roles & Behavior:**
- **Admin** (no params): Returns base medication details
- **Clinic Manager** (`clinic_id`): Returns clinic medication details
- **Doctor/Patient** (`clinic_id` + `patient_id`): Returns patient medication details with schedule

**Response (Patient Medication):**
```json
{
  "id": "1000007960",
  "name": "Aspirin",
  "form": "Tablet",
  "unit_of_measurement": "mg",
  "doctor": 3,
  "frequency": "daily",
  "frequency_data": {
    "dates": [],
    "days": [],
    "time": ["08:00", "20:00"]
  },
  "start_date": "2026-01-15 08:00:00",
  "end_date": "2026-02-15 08:00:00",
  "dosage": "100mg"
}
```

**Status Codes:**
- `200 OK`: Success
- `400 Bad Request`: Missing required parameters
- `404 Not Found`: Medication not found

---

#### PUT - Update Medication
Updates medication details or assigns medication to patient.

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `clinic_id` | Conditional | Required for Doctor |
| `patient_id` | Conditional | Required for Doctor |

**Request Body (Admin - Update Medication):**
```json
{
  "medication_name": "Updated Name",
  "medication_form": "Capsule",
  "medication_unit": "mg"
}
```

**Request Body (Doctor - Assign/Update Patient Medication):**
```json
{
  "frequency": "daily",
  "frequency_data": {
    "dates": [],
    "days": [],
    "time": ["08:00", "20:00"]
  },
  "start_date": "2026-01-15 08:00:00",
  "end_date": "2026-02-15 08:00:00",
  "dosage": "100mg"
}
```

**User Roles & Behavior:**
- **Admin** (no params): Updates base medication name/form/unit
- **Doctor** (`clinic_id` + `patient_id`): Assigns medication to patient or updates schedule

**Response (Doctor Assignment):**
```json
{
  "detail": "Medication assigned to patient",
  "medication_id": "1000007960",
  "medication_name": "Aspirin",
  "frequency": "daily",
  "frequency_data": {...},
  "start_date": "2026-01-15 08:00:00",
  "end_date": "2026-02-15 08:00:00",
  "dosage": "100mg"
}
```

**Status Codes:**
- `200 OK`: Updated successfully
- `201 Created`: Medication assigned to patient
- `403 Forbidden`: Permission denied
- `404 Not Found`: Medication not found

---

#### DELETE - Delete Medication
Deletes medication or removes medication assignment.

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `clinic_id` | Conditional | Required for Clinic Manager/Doctor |
| `patient_id` | Conditional | Required for Doctor |

**User Roles & Behavior:**
- **Admin** (no params): Deletes base medication
- **Clinic Manager** (`clinic_id`): Removes medication from clinic
- **Doctor** (`clinic_id` + `patient_id`): Removes medication from patient

**Response:**
```json
{
  "detail": "Medication removed from patient successfully"
}
```

**Status Codes:**
- `204 No Content`: Deleted successfully
- `400 Bad Request`: Missing required parameters
- `404 Not Found`: Medication not found

---

## Medication Bundles Endpoints

### 3. List/Create Bundles
**Endpoint:** `GET/POST /api/v1/medications/bundles/`

#### GET - List Bundles
Lists medication bundles based on user role and context.

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
    "bundle_name": "Morning Medications",
    "medications": [
      {
        "id": "1000007960",
        "name": "Aspirin",
        "form": "Tablet",
        "unit_of_measurement": "mg"
      },
      {
        "id": "1000007961",
        "name": "Vitamin D",
        "form": "Capsule",
        "unit_of_measurement": "IU"
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
    "bundle_name": "Morning Medications",
    "doctor_id": 3,
    "doctor_name": "Dr. John Smith",
    "medications": [...]
  }
]
```

**Status Codes:**
- `200 OK`: Success
- `400 Bad Request`: Missing required parameters
- `403 Forbidden`: Access denied

---

#### POST - Create Bundle
Creates a new medication bundle.

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `clinic_id` | Yes | Clinic where bundle will be created |

**Request Body:**
```json
{
  "bundle_name": "Morning Medications",
  "medication_ids": ["1000007960", "1000007961", "1000007962"]
}
```

**User Roles:**
- **Admin**: Can create bundles
- **Clinic Manager**: Can create bundles for their clinic

**Response:**
```json
{
  "id": 1,
  "bundle_name": "Morning Medications",
  "medications": [
    {"id": "1000007960", "name": "Aspirin"},
    {"id": "1000007961", "name": "Vitamin D"}
  ]
}
```

**Status Codes:**
- `201 Created`: Bundle created successfully
- `400 Bad Request`: Missing fields or invalid medication IDs
- `404 Not Found`: Some medications not found

---

### 4. Bundle Details
**Endpoint:** `GET/PUT/DELETE /api/v1/medications/bundles/{id}/`

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
  "bundle_name": "Morning Medications",
  "medications": [
    {
      "id": "1000007960",
      "name": "Aspirin",
      "form": "Tablet",
      "unit_of_measurement": "mg"
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
  "bundle_name": "Updated Morning Medications",
  "medication_ids": ["1000007960", "1000007961", "1000007962", "1000007963"]
}
```

**Request Body (Doctor - Assign to Patient):**
```json
// Empty body - assignment based on query params
{}
```

**User Roles & Behavior:**
- **Admin/Clinic Manager** (no `patient_id`): Updates bundle name and medications
- **Doctor** (`clinic_id` + `patient_id`): Assigns bundle to patient

**Response (Doctor Assignment):**
```json
{
  "detail": "Bundle assigned to patient",
  "bundle_id": 1,
  "bundle_name": "Morning Medications"
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

## Medication Reports Endpoints

### 5. List/Create Medication Reports
**Endpoint:** `GET/POST /api/v1/medication-reports/`

#### GET - List Medication Reports
Lists medication intake reports based on user role.

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
    "medication": {
      "id": "1000007960",
      "name": "Aspirin",
      "form": "Tablet",
      "unit_of_measurement": "mg"
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
    "medication": {
      "id": "1000007960",
      "name": "Aspirin",
      "form": "Tablet",
      "unit_of_measurement": "mg"
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

#### POST - Create Medication Report
Logs intake of a medication (typically called by patients).

**Query Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `clinic_id` | Yes | Clinic context |
| `patient_id` | Yes | Patient who took medication |

**Request Body:**
```json
{
  "medication_id": "1000007960",
  "timestamp": "2026-01-14 10:30:00"  // Optional - defaults to now
}
```

**Validations:**
- Medication must be assigned to the patient
- Patients can only create reports for themselves
- Timestamp format: "YYYY-MM-DD HH:MM:SS"

**Response:**
```json
{
  "detail": "Medication report created successfully"
}
```

**Status Codes:**
- `201 Created`: Report created successfully
- `400 Bad Request`: Missing required fields or invalid timestamp
- `403 Forbidden`: Patient not authorized
- `404 Not Found`: Medication not assigned to patient

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
  "detail": "Medication not found"
}
```

### 400 Bad Request
```json
{
  "detail": "Medication name, form, and unit are required"
}
```

---

## Frequency Data Structure

When assigning medications to patients, the `frequency_data` field follows this structure:

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
| GET /medications/ | All medications | Clinic medications | Clinic/Patient medications | Own medications |
| POST /medications/ | Create base medication | Add to clinic | Assign to patient | ❌ |
| GET /medications/{id}/ | Base medication | Clinic medication | Patient medication | Own medication |
| PUT /medications/{id}/ | Update medication | ❌ | Assign/Update patient | ❌ |
| DELETE /medications/{id}/ | Delete medication | Remove from clinic | Remove from patient | ❌ |
| GET /bundles/ | All bundles | Clinic bundles | Clinic/Patient bundles | Own bundles |
| POST /bundles/ | Create bundle | Create bundle | ❌ | ❌ |
| GET /bundles/{id}/ | Any bundle | Clinic bundle | Clinic bundle | ❌ |
| PUT /bundles/{id}/ | Update bundle | Update bundle | Assign to patient | ❌ |
| DELETE /bundles/{id}/ | Delete bundle | Delete bundle | Remove from patient | ❌ |
| GET /medication-reports/ | All reports | Clinic reports | Patient reports | Own reports |
| POST /medication-reports/ | ✓ | ✓ | ✓ | Create own report |

---

## Notes

1. **Query Parameters**: Context parameters (clinic_id, patient_id) are always passed as query parameters
2. **Request Body**: Actual data (medication_name, medication_form, medication_ids, etc.) are passed in the request body
3. **Authentication**: All endpoints require authentication
4. **Timestamps**: All timestamps are in format "YYYY-MM-DD HH:MM:SS"
5. **Patient Authorization**: Patients can only access their own data
6. **Doctor Authorization**: Doctors can only access patients assigned to them
7. **Medication IDs**: Medication IDs are strings (e.g., "1000007960") and auto-generated starting from 1000000000
8. **Dosage**: The dosage field is a flexible string that can contain any dosage information (e.g., "100mg", "1 tablet", "2 capsules")
