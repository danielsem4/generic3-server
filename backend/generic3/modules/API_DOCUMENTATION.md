# Modules API Documentation

## Table of Contents
1. [Module Endpoints](#module-endpoints)
2. [Clinic Module Endpoints](#clinic-module-endpoints)
3. [Patient Module Endpoints](#patient-module-endpoints)

---

## Module Endpoints

### 1. List/Create Modules
**Endpoint:** `GET/POST /api/v1/modules/`

#### GET - List Modules
Lists all modules in the system.

**Authentication:** Required

**User Roles:**
- Any authenticated user can list modules

**Response:**
```json
[
  {
    "id": 1,
    "name": "Activities Tracking",
    "description": "Track patient daily activities"
  },
  {
    "id": 2,
    "name": "Medication Management",
    "description": "Manage patient medications"
  }
]
```

**Status Codes:**
- `200 OK`: Success
- `401 Unauthorized`: Not authenticated

---

#### POST - Create Module
Creates a new module in the system.

**Authentication:** Required (Admin only)

**Request Body:**
```json
{
  "module_name": "New Module",
  "module_description": "Description for new module"
}
```

**User Roles:**
- **Admin**: Can create new modules

**Response (Created):**
```json
{
  "id": 5,
  "name": "New Module",
  "description": "Description for new module"
}
```

**Response (Already Exists):**
```json
{
  "detail": "Module \"New Module\" already exists."
}
```

**Status Codes:**
- `201 Created`: Module created successfully
- `200 OK`: Module already exists (via get_or_create)
- `400 Bad Request`: Module name is required
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: User is not admin
- `409 Conflict`: Module with same name already exists
- `500 Internal Server Error`: Server error occurred

---

### 2. Module Details
**Endpoint:** `GET/PUT/PATCH/DELETE /api/v1/modules/{module_id}/`

#### GET - Get Module Details
Retrieves details of a specific module.

**Authentication:** Required

**User Roles:**
- Any authenticated user can view module details

**Response:**
```json
{
  "id": 1,
  "name": "Activities Tracking",
  "description": "Track patient daily activities"
}
```

**Status Codes:**
- `200 OK`: Success
- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Module not found

---

#### PUT/PATCH - Update Module
Updates an existing module's name and/or description.

**Authentication:** Required (Admin only)

**Request Body:**
```json
{
  "module_name": "Updated Module Name",
  "module_description": "Updated description"
}
```

**Note:** 
- `PUT` typically requires all fields
- `PATCH` allows partial updates (only changed fields)

**User Roles:**
- **Admin**: Can update modules

**Response:**
```json
{
  "id": 1,
  "name": "Updated Module Name",
  "description": "Updated description"
}
```

**Status Codes:**
- `200 OK`: Updated successfully
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: User is not admin
- `404 Not Found`: Module not found
- `500 Internal Server Error`: Server error occurred

---

#### DELETE - Delete Module
Deletes a module from the system.

**Authentication:** Required (Admin only)

**User Roles:**
- **Admin**: Can delete modules

**Constraints:**
- Cannot delete modules that are associated with clinics

**Response:**
```json
// No content on success
```

**Response (Conflict):**
```json
{
  "detail": "Module cannot be deleted as it is associated with clinics."
}
```

**Status Codes:**
- `204 No Content`: Deleted successfully
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: User is not admin
- `404 Not Found`: Module not found
- `409 Conflict`: Module is associated with clinics
- `500 Internal Server Error`: Server error occurred

---

## Clinic Module Endpoints

### 3. List/Add Clinic Modules
**Endpoint:** `GET/POST /api/v1/clinics/{clinic_id}/modules/`

#### GET - List Clinic Modules
Lists all modules available in a specific clinic.

**Authentication:** Required

**User Roles:**
- **Admin**: Can view any clinic's modules
- **Clinic Manager**: Can view their clinic's modules
- **Doctor**: Can view their clinic's modules

**Response:**
```json
[
  {
    "id": 1,
    "name": "Activities Tracking",
    "description": "Track patient daily activities",
    "is_active": true
  },
  {
    "id": 2,
    "name": "Medication Management",
    "description": "Manage patient medications",
    "is_active": false
  }
]
```

**Status Codes:**
- `200 OK`: Success
- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Clinic not found

---

#### POST - Add Module to Clinic
Adds an existing module to a clinic.

**Authentication:** Required (Admin or Clinic Manager)

**Request Body:**
```json
{
  "module_id": 4
}
```

**User Roles:**
- **Admin**: Can add modules to any clinic
- **Clinic Manager**: Can add modules to their clinic

**Response (Created):**
```json
{
  "detail": "Clinic module added successfully."
}
```

**Response (Already Exists):**
```json
{
  "detail": "Clinic module already exists."
}
```

**Status Codes:**
- `201 Created`: Module added to clinic successfully
- `400 Bad Request`: Module ID is required
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: User doesn't have permission
- `404 Not Found`: Clinic or module not found
- `409 Conflict`: Module already added to clinic

---

### 4. Clinic Module Details
**Endpoint:** `GET/PATCH/DELETE /api/v1/clinics/{clinic_id}/modules/{module_id}/`

#### GET - Get Clinic Module Details
Retrieves details of a specific module in a clinic.

**Authentication:** Required

**User Roles:**
- **Admin**: Can view any clinic module
- **Clinic Manager**: Can view modules in their clinic
- **Doctor**: Can view modules in their clinic

**Response:**
```json
{
  "module_id": 1,
  "module_name": "Activities Tracking",
  "is_active": true
}
```

**Status Codes:**
- `200 OK`: Success
- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Clinic, module, or clinic module not found

---

#### PATCH - Update Clinic Module
Updates the active status of a module in a clinic.

**Authentication:** Required (Admin or Clinic Manager)

**Request Body (Toggle):**
```json
// Empty body - toggles current state
```

**Request Body (Explicit Set):**
```json
{
  "is_active": false
}
```

**User Roles:**
- **Admin**: Can update any clinic module
- **Clinic Manager**: Can update modules in their clinic

**Behavior:**
- If `is_active` is provided in body: Sets to that value
- If no body or `is_active` not provided: Toggles current state

**Response:**
```json
{
  "detail": "Clinic module updated successfully.",
  "is_active": false
}
```

**Status Codes:**
- `200 OK`: Updated successfully
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: User doesn't have permission
- `404 Not Found`: Clinic, module, or clinic module not found

---

#### DELETE - Remove Module from Clinic
Removes a module from a clinic.

**Authentication:** Required (Admin or Clinic Manager)

**User Roles:**
- **Admin**: Can remove modules from any clinic
- **Clinic Manager**: Can remove modules from their clinic

**Response:**
```json
// No content on success
```

**Status Codes:**
- `204 No Content`: Deleted successfully
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: User doesn't have permission
- `404 Not Found`: Clinic, module, or clinic module not found

---

## Patient Module Endpoints

### 5. List/Add Patient Modules
**Endpoint:** `GET/POST /api/v1/clinics/{clinic_id}/patients/{patient_id}/modules/`

#### GET - List Patient Modules
Lists all modules assigned to a specific patient in a clinic.

**Authentication:** Required

**User Roles:**
- **Admin**: Can view any patient's modules
- **Doctor**: Can view modules of their assigned patients
- **Patient**: Can view their own modules

**Response:**
```json
[
  {
    "id": 1,
    "name": "Activities Tracking",
    "description": "Track patient daily activities",
    "is_active": true
  },
  {
    "id": 3,
    "name": "Questionnaires",
    "description": "Patient health questionnaires",
    "is_active": true
  }
]
```

**Status Codes:**
- `200 OK`: Success
- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Clinic or patient not found

---

#### POST - Add Module to Patient
Assigns a module to a patient.

**Authentication:** Required (Admin or Doctor)

**Request Body:**
```json
{
  "module_id": 3
}
```

**User Roles:**
- **Admin**: Can assign modules to any patient
- **Doctor**: Can assign modules to their patients

**Constraints:**
- The module must already be added to the clinic before assigning to a patient

**Response (Created):**
```json
{
  "detail": "Patient module added successfully."
}
```

**Response (Already Exists):**
```json
{
  "detail": "Patient module already exists."
}
```

**Response (Module Not in Clinic):**
```json
{
  "detail": "Clinic does not have this module."
}
```

**Status Codes:**
- `201 Created`: Module assigned to patient successfully
- `400 Bad Request`: Module ID required or clinic doesn't have module
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: User doesn't have permission
- `404 Not Found`: Patient, clinic, or module not found
- `409 Conflict`: Module already assigned to patient

---

### 6. Patient Module Details
**Endpoint:** `GET/PATCH/DELETE /api/v1/clinics/{clinic_id}/patients/{patient_id}/modules/{module_id}/`

#### GET - Get Patient Module Details
Retrieves details of a specific module assigned to a patient.

**Authentication:** Required

**User Roles:**
- **Admin**: Can view any patient module
- **Doctor**: Can view modules of their assigned patients
- **Patient**: Can view their own modules

**Response:**
```json
{
  "module_id": 1,
  "module_name": "Activities Tracking",
  "is_active": true
}
```

**Status Codes:**
- `200 OK`: Success
- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Clinic, patient, module, or patient module not found

---

#### PATCH - Update Patient Module
Updates the active status of a module for a patient.

**Authentication:** Required (Admin or Doctor)

**Request Body (Toggle):**
```json
// Empty body - toggles current state
```

**Request Body (Explicit Set):**
```json
{
  "is_active": true
}
```

**User Roles:**
- **Admin**: Can update any patient module
- **Doctor**: Can update modules for their assigned patients

**Behavior:**
- If `is_active` is provided in body: Sets to that value
- If no body or `is_active` not provided: Toggles current state

**Response:**
```json
{
  "detail": "Patient module updated successfully.",
  "is_active": true
}
```

**Status Codes:**
- `200 OK`: Updated successfully
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: User doesn't have permission
- `404 Not Found`: Clinic, patient, module, or patient module not found

---

#### DELETE - Remove Module from Patient
Removes a module assignment from a patient.

**Authentication:** Required (Admin or Doctor)

**User Roles:**
- **Admin**: Can remove modules from any patient
- **Doctor**: Can remove modules from their assigned patients

**Response:**
```json
// No content on success
```

**Status Codes:**
- `204 No Content`: Deleted successfully
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: User doesn't have permission
- `404 Not Found`: Clinic, patient, module, or patient module not found

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
  "detail": "You do not have permission to add modules."
}
```

### 404 Not Found
```json
{
  "detail": "Module not found."
}
```

### 400 Bad Request
```json
{
  "detail": "Module name is required."
}
```

### 409 Conflict
```json
{
  "detail": "Module cannot be deleted as it is associated with clinics."
}
```

---

## Module Hierarchy

The module system follows a three-tier hierarchy:

1. **Base Modules** (`Modules` model)
   - Created by admins
   - Global module definitions
   - Can be reused across multiple clinics

2. **Clinic Modules** (`ClinicModules` model)
   - Links base modules to specific clinics
   - Has `is_active` flag to enable/disable at clinic level
   - Managed by admins and clinic managers

3. **Patient Modules** (`PatientModules` model)
   - Links modules to specific patients within a clinic
   - Has `is_active` flag to enable/disable at patient level
   - Managed by admins and doctors
   - Requires the module to be added to the clinic first

---

## Permission Summary

| Endpoint | Admin | Clinic Manager | Doctor | Patient |
|----------|-------|----------------|--------|---------|
| GET /modules/ | ✓ | ✓ | ✓ | ✓ |
| POST /modules/ | ✓ | ❌ | ❌ | ❌ |
| GET /modules/{id}/ | ✓ | ✓ | ✓ | ✓ |
| PUT/PATCH /modules/{id}/ | ✓ | ❌ | ❌ | ❌ |
| DELETE /modules/{id}/ | ✓ | ❌ | ❌ | ❌ |
| GET /clinics/{id}/modules/ | ✓ | ✓ (own clinic) | ✓ (own clinic) | ❌ |
| POST /clinics/{id}/modules/ | ✓ | ✓ (own clinic) | ❌ | ❌ |
| GET /clinics/{id}/modules/{id}/ | ✓ | ✓ (own clinic) | ✓ (own clinic) | ❌ |
| PATCH /clinics/{id}/modules/{id}/ | ✓ | ✓ (own clinic) | ❌ | ❌ |
| DELETE /clinics/{id}/modules/{id}/ | ✓ | ✓ (own clinic) | ❌ | ❌ |
| GET /clinics/{id}/patients/{id}/modules/ | ✓ | ❌ | ✓ (assigned patients) | ✓ (own) |
| POST /clinics/{id}/patients/{id}/modules/ | ✓ | ❌ | ✓ (assigned patients) | ❌ |
| GET /clinics/{id}/patients/{id}/modules/{id}/ | ✓ | ❌ | ✓ (assigned patients) | ✓ (own) |
| PATCH /clinics/{id}/patients/{id}/modules/{id}/ | ✓ | ❌ | ✓ (assigned patients) | ❌ |
| DELETE /clinics/{id}/patients/{id}/modules/{id}/ | ✓ | ❌ | ✓ (assigned patients) | ❌ |

---

## RESTful Design Principles Applied

1. **Resource-Based URLs**: URLs represent resources (`/modules/`, `/clinics/{id}/modules/`), not actions
2. **HTTP Methods**: Use standard HTTP methods (GET, POST, PUT, PATCH, DELETE) for CRUD operations
3. **Nested Resources**: Clinic modules and patient modules are properly nested under their parent resources
4. **Proper Status Codes**: 
   - `200 OK` for successful GET/PUT/PATCH
   - `201 Created` for successful POST
   - `204 No Content` for successful DELETE
   - `400 Bad Request` for validation errors
   - `401 Unauthorized` for authentication issues
   - `403 Forbidden` for authorization issues
   - `404 Not Found` for missing resources
   - `409 Conflict` for business logic conflicts
5. **Idempotency**: DELETE and PUT operations are idempotent
6. **PATCH for Partial Updates**: Use PATCH for updating specific fields (like toggling `is_active`)

---

## Notes

1. **Authentication**: All endpoints require authentication
2. **Module Assignment Flow**: 
   - Admin creates base module → 
   - Clinic Manager adds to clinic → 
   - Doctor assigns to patient
3. **Active Status**: Both clinic modules and patient modules have independent `is_active` flags
4. **Cascading Deletes**: Deleting a clinic will also delete associated clinic modules and patient modules
5. **Toggle Behavior**: PATCH endpoints support both explicit setting (`{"is_active": true}`) and toggling (empty body)
6. **Doctor Authorization**: Doctors can only manage modules for patients assigned to them
7. **Patient Access**: Patients can only view their own modules, not modify them
