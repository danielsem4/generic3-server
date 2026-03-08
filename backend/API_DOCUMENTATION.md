# GenericWeb API Documentation

## Overview
This document provides comprehensive documentation for the GenericWeb API, a Django REST Framework-based backend that manages clinics, users, medications, activities, and notifications for Generic3.

**Base URL:** `https://d291ffbbf342.ngrok-free.app/api/v1/`

## Authentication
The API uses Cookie-based Token authentication. Most endpoints require authentication except for login and logout.

### Headers Required:
- `Content-Type: application/json`

### Authentication Methods:
1. **Cookie Authentication (Primary)**: After successful login, an `auth_token` cookie is automatically set and used for subsequent requests
2. **Authorization Header (Fallback)**: `Authorization: Token <your_token>` can be used if cookies are not available

**Note**: The login endpoint automatically sets an HttpOnly cookie with a 7-day expiration that handles authentication for subsequent requests.

---

## 1. Authentication Endpoints

### 1.1 Login
**Endpoint:** `POST /api/v1/login/`
**Description:** Authenticate a user and return a token with user details and clinic information. Sets an HttpOnly authentication cookie for subsequent requests.
**Authentication:** Not required

**Request Body:**
```json
{
    "email": "user@example.com",
    "password": "password123"
}
```

**Response (Success - 200):**
```json
{
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+1234567890",
    "is_clinic_manager": true,
    "is_doctor": false,
    "is_patient": false,
    "is_research_patient": false,
    "clinicId": 1,
    "clinicName": "Test Clinic",
    "clinic_image": "http://localhost:8000/static/images/clinic.png",
    "modules": [
        {"name": "Medications", "id": 1},
        {"name": "Activities", "id": 2}
    ],
    "status": "Success",
    "server_url": "https://clinic.example.com"
}
```

**Cookie Set**: 
- `auth_token`: HttpOnly cookie with 7-day expiration, automatically used for authentication in subsequent requests

**Error Responses:**
- `400`: Missing email or password
- `401`: Invalid credentials
- `403`: No clinics found for user
- `404`: Clinic not found
- `202`: Multiple clinics found (returns clinic list)

### 1.2 Logout
**Endpoint:** `POST /api/v1/logout/`
**Description:** Log out the current user and clear authentication cookies.
**Authentication:** Required

**Response (Success - 200):**
```json
{
    "message": "Logged out successfully"
}
```

**Cookie Action**: Deletes the `auth_token` cookie

---

## 2. Users Management

### 2.1 Get Users
**Endpoint:** `GET /api/v1/users/{clinic_id}/{user_id}/`
**Description:** Get users for a specific clinic based on the requesting user's role.
**Authentication:** Required

**Parameters:**
- `clinic_id` (int): ID of the clinic
- `user_id` (int): ID of the requesting user

**Response (Success - 200):**
```json
{
    "1": {
        "email": "doctor@example.com",
        "first_name": "Jane",
        "last_name": "Smith",
        "phone_number": "+1234567890",
        "is_clinic_manager": false,
        "is_doctor": true,
        "is_patient": false,
        "is_research_patient": false
    },
    "2": {
        "email": "patient@example.com",
        "first_name": "Bob",
        "last_name": "Johnson",
        "phone_number": "+0987654321",
        "is_clinic_manager": false,
        "is_doctor": false,
        "is_patient": true,
        "is_research_patient": false
    }
}
```

**User Role Access:**
- **Staff users:** See all clinic managers
- **Clinic managers:** See doctors in their clinic
- **Doctors:** See patients in their clinic

**Error Responses:**
- `404`: User not found, Clinic not found, or No users found for this role

---

## 3. Medications Management

### 3.1 Clinic Medications

#### 3.1.1 Get Clinic Medications
**Endpoint:** `GET /api/v1/medications/clinic/{clinic_id}/`
**Description:** Get all medications available for a specific clinic.
**Authentication:** Required

**Parameters:**
- `clinic_id` (int): ID of the clinic

**Response (Success - 200):**
```json
[
    {
        "id": "1999022181",
        "medForm": "tablet",
        "medName": "Aspirin",
        "medUnitOfMeasurement": "mg"
    },
    {
        "id": "1000000809",
        "medForm": "capsule",
        "medName": "Ibuprofen",
        "medUnitOfMeasurement": "mg"
    }
]
```

#### 3.1.2 Add Clinic Medication
**Endpoint:** `POST /api/v1/medications/clinic/{clinic_id}/add/`
**Description:** Add a medication to a clinic's available medications.
**Authentication:** Required

**Request Body:**
```json
{
    "med_id": "1999022181"
}
```

**Response (Success - 201):**
```json
{
    "detail": "Medication added successfully"
}
```

#### 3.1.3 Delete Clinic Medication
**Endpoint:** `DELETE /api/v1/medications/clinic/{clinic_id}/delete/{medication_id}/`
**Description:** Remove a medication from a clinic's available medications.
**Authentication:** Required

**Response (Success - 204):**
```json
{
    "detail": "Medication deleted successfully"
}
```

### 3.2 Patient Medications

#### 3.2.1 Get Patient Medications
**Endpoint:** `GET /api/v1/medications/patient/{clinic_id}/{patient_id}/`
**Description:** Get all medications assigned to a specific patient in a clinic.
**Authentication:** Required

**Response (Success - 200):**
```json
[
    {
        "id": "1999022181",
        "medForm": "tablet",
        "medName": "Aspirin",
        "medUnitOfMeasurement": "mg",
        "doctor": "doctor@example.com",
        "frequency": "weekly",
        "frequency_data": {
            "dates": [],
            "days": ["monday", "wednesday", "friday"],
            "time": ["10:00", "14:00"]
        },
        "start_date": "2025-07-01",
        "end_date": "2025-07-31",
        "dosage": "pill"
    }
]
```

#### 3.2.2 Add Patient Medication
**Endpoint:** `POST /api/v1/medications/patient/{clinic_id}/{patient_id}/add/`
**Description:** Assign a medication to a patient with scheduling details.
**Authentication:** Required

**Request Body:**
```json
{
    "med_id": "1000000809",
    "frequency": "monthly",
    "frequency_data": {
        "dates": ["2025-07-01", "2025-07-08", "2025-07-15"],
        "days": [],
        "time": ["10:00", "14:00"]
    },
    "start_date": "2025-07-01",
    "end_date": "2025-07-31",
    "dosage": "pill"
}
```

**Frequency Types:**
- `weekly`: Use `days` array with day names and `time` array
- `monthly`: Use `dates` array with specific dates and `time` array
- `daily`: Use `time` array only

#### 3.2.3 Update Patient Medication
**Endpoint:** `PUT /api/v1/medications/patient/{clinic_id}/{patient_id}/update/`
**Description:** Update an existing patient medication assignment.
**Authentication:** Required

**Request Body:** Same as Add Patient Medication

#### 3.2.4 Delete Patient Medication
**Endpoint:** `DELETE /api/v1/medications/patient/{clinic_id}/{patient_id}/delete/{medication_id}/`
**Description:** Remove a medication assignment from a patient.
**Authentication:** Required

### 3.3 Medication Reporting

#### 3.3.1 Report Medication Taken
**Endpoint:** `POST /api/v1/medications/report/`
**Description:** Report that a patient has taken their medication.
**Authentication:** Required

**Request Body:**
```json
{
    "clinic_id": 1,
    "patient_id": 5,
    "medication_id": "1999022181",
    "timestamp": "2025-07-15 13:00:00"
}
```

---

## 4. Activities Management

### 4.1 Clinic Activities

#### 4.1.1 Get Clinic Activities
**Endpoint:** `GET /api/v1/activities/clinic/{clinic_id}/`
**Description:** Get all activities available for a specific clinic.
**Authentication:** Required

**Response (Success - 200):**
```json
[
    {
        "id": 1,
        "name": "Morning Walk",
        "description": "30-minute walk in the morning"
    },
    {
        "id": 2,
        "name": "Breathing Exercise",
        "description": "Deep breathing for 10 minutes"
    }
]
```

#### 4.1.2 Add Clinic Activity
**Endpoint:** `POST /api/v1/activities/clinic/{clinic_id}/add/`
**Description:** Add an activity to a clinic's available activities.
**Authentication:** Required

**Request Body:**
```json
{
    "activity_id": 4
}
```

#### 4.1.3 Delete Clinic Activity
**Endpoint:** `DELETE /api/v1/activities/clinic/{clinic_id}/delete/{activity_id}/`
**Description:** Remove an activity from a clinic's available activities.
**Authentication:** Required

### 4.2 Patient Activities

#### 4.2.1 Get Patient Activities
**Endpoint:** `GET /api/v1/activities/patient/{clinic_id}/{patient_id}/`
**Description:** Get all activities assigned to a specific patient.
**Authentication:** Required

#### 4.2.2 Add Patient Activity
**Endpoint:** `POST /api/v1/activities/patient/{clinic_id}/{patient_id}/add/`
**Description:** Assign an activity to a patient.
**Authentication:** Required

**Request Body:**
```json
{
    "activity_id": 1
}
```

#### 4.2.3 Delete Patient Activity
**Endpoint:** `DELETE /api/v1/activities/patient/{clinic_id}/{patient_id}/delete/{activity_id}/`
**Description:** Remove an activity assignment from a patient.
**Authentication:** Required

### 4.3 Activity Reporting

#### 4.3.1 Report Activity Completion
**Endpoint:** `POST /api/v1/activities/report/`
**Description:** Report that a patient has completed an activity.
**Authentication:** Required

**Request Body:**
```json
{
    "clinic_id": 1,
    "patient_id": 5,
    "activity_id": 3,
    "timestamp": "2025-07-15 13:00:00"
}
```

---

## 5. Notifications Management

### 5.1 Set Event Notification
**Endpoint:** `POST /api/v1/notifications/set/notification/`
**Description:** Set up notifications for medication or activity reminders.
**Authentication:** Required

**Request Body:**
```json
{
    "clinic_id": 1,
    "patient_id": 5,
    "event_type": "activity",
    "event_id": "3",
    "frequency": "weekly",
    "frequency_data": {
        "dates": [],
        "days": ["monday", "wednesday", "friday"],
        "time": ["08:30", "12:00"]
    },
    "start_date_time": "2025-07-01 08:00:00",
    "end_date_time": "2025-08-01 08:00:00"
}
```

**Event Types:**
- `medication`: Medication reminders
- `activity`: Activity reminders
- `questionnaire`: Questionnaire reminders

---

## Common Error Responses

### HTTP Status Codes
- `200`: Success
- `201`: Created successfully
- `204`: Deleted successfully
- `400`: Bad Request (missing or invalid data)
- `401`: Unauthorized (invalid credentials)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found (resource doesn't exist)

### Common Error Response Format
```json
{
    "detail": "Error message describing what went wrong"
}
```

---

## Data Models

### User Roles
- **Staff**: System administrators with access to all clinics
- **Clinic Manager**: Manages doctors and patients within their clinic
- **Doctor**: Manages patients assigned to them
- **Patient**: Regular patients who receive care
- **Research Patient**: Patients participating in research studies

### Frequency Data Structure
The `frequency_data` field is used for scheduling medications and activities:

```json
{
    "dates": ["2025-07-01", "2025-07-08"],  // Specific dates (for monthly)
    "days": ["monday", "wednesday"],         // Days of week (for weekly)
    "time": ["10:00", "14:00"]              // Times of day
    // leave empty one of those field if needed
}
```

---


## Security Notes
- All endpoints except login require authentication
- Token-based authentication is used
- Cookies are set with security flags in production
- Role-based access control is implemented
- Input validation is performed on all endpoints

---

*Last updated: July 30, 2025*
