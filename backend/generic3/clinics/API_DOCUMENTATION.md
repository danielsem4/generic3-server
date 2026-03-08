# Clinics API Documentation

## Table of Contents
1. [Clinic Endpoints](#clinic-endpoints)

---

## Clinic Endpoints

### 1. List/Create Clinics
**Endpoint:** `GET/POST /api/v1/clinics/`

#### GET - List All Clinics
Lists all clinics in the system with their details, including managers and modules.

**Authentication:** Required (Staff only)

**User Roles:**
- **Admin/Staff**: Can view all clinics

**Response:**
```json
[
  {
    "Id": 1,
    "Name": "Main Clinic",
    "Clinic url": "https://mainclinic.com",
    "Research clinic": "no",
    "Clinic manager": {
      "Id": 5,
      "First name": "John",
      "Last name": "Doe",
      "Email": "john.doe@example.com"
    },
    "Modules": [
      {
        "Id": 1,
        "Module name": "Activities Tracking"
      },
      {
        "Id": 2,
        "Module name": "Medication Management"
      }
    ]
  }
]
```

**Status Codes:**
- `200 OK`: Success
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: User is not staff

---

#### POST - Create Clinic
Creates a new clinic with a clinic manager and associated modules.

**Authentication:** Required (Staff only)

**Request Body:**
```json
{
  "clinic_name": "New Clinic",
  "clinic_url": "https://newclinic.com",
  "clinic_image_url": "https://example.com/image.jpg",
  "clinic_type": "Research",
  "manager_first_name": "Jane",
  "manager_last_name": "Smith",
  "manager_email": "jane.smith@example.com",
  "manager_phone_number": "1234567890",
  "selected_modules": [1, 2, 3]
}
```

**Required Fields:**
- `clinic_name`: Name of the clinic
- `clinic_url`: URL/domain of the clinic
- `manager_first_name`: Clinic manager's first name
- `manager_last_name`: Clinic manager's last name
- `manager_email`: Clinic manager's email address
- `manager_phone_number`: Clinic manager's phone number

**Optional Fields:**
- `clinic_image_url`: URL to clinic logo/image (default: "")
- `clinic_type`: Type of clinic - "Research" or "Default" (default: "Default")
- `selected_modules`: Array of module IDs to associate with clinic (default: [])

**User Roles:**
- **Admin/Staff**: Can create clinics

**Response (Success):**
```json
{
  "message": "Clinic created successfully"
}
```

**Response (Error - Duplicate):**
```json
{
  "error": "Clinic with this name or URL already exists"
}
```

**Response (Error - Missing Fields):**
```json
{
  "error": "All fields are required"
}
```

**Response (Error - Manager Creation Failed):**
```json
{
  "error": "Failed to create clinic manager"
}
```

**Status Codes:**
- `201 Created`: Clinic created successfully
- `400 Bad Request`: Missing required fields or duplicate clinic
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: User is not staff
- `500 Internal Server Error`: Server error occurred

**Notes:**
- Creates a new user account for the clinic manager
- Manager will receive account credentials via email
- The clinic manager is automatically associated with the clinic
- All specified modules are linked to the clinic upon creation
- Transaction is atomic - if any step fails, all changes are rolled back

---

### 2. Clinic Details
**Endpoint:** `GET/PUT/DELETE /api/v1/clinics/{clinic_id}/`

#### GET - Get Clinic Details
Retrieves detailed information about a specific clinic.

**Authentication:** Required

**User Roles:**
- Any authenticated user can view clinic details

**URL Parameters:**
- `clinic_id`: The ID of the clinic

**Response:**
```json
{
  "Id": 1,
  "Name": "Main Clinic",
  "Clinic url": "https://mainclinic.com",
  "Research clinic": "yes",
  "Clinic manager": {
    "Id": 5,
    "First name": "John",
    "Last name": "Doe",
    "Email": "john.doe@example.com"
  },
  "Modules": [
    {
      "Id": 1,
      "Module name": "Activities Tracking"
    },
    {
      "Id": 2,
      "Module name": "Medication Management"
    }
  ]
}
```

**Status Codes:**
- `200 OK`: Success
- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Clinic not found

---

#### PUT - Update Clinic
Updates an existing clinic's information and associated modules.

**Authentication:** Required (Staff or Clinic Manager)

**User Roles:**
- **Admin/Staff**: Can update any clinic
- **Clinic Manager**: Can update their own clinic

**URL Parameters:**
- `clinic_id`: The ID of the clinic

**Request Body (All fields optional):**
```json
{
  "clinic_name": "Updated Clinic Name",
  "clinic_url": "https://updatedclinic.com",
  "clinic_image_url": "https://example.com/newimage.jpg",
  "clinic_type": "Default",
  "selected_modules": [1, 3, 4]
}
```

**Updatable Fields:**
- `clinic_name`: New name for the clinic
- `clinic_url`: New URL for the clinic
- `clinic_image_url`: New image URL
- `clinic_type`: "Research" or "Default"
- `selected_modules`: Array of module IDs (replaces all existing modules)

**Response (Success):**
```json
{
  "message": "Clinic updated successfully"
}
```

**Response (Error - Empty Name):**
```json
{
  "error": "Clinic name cannot be empty"
}
```

**Response (Error - Duplicate Name):**
```json
{
  "error": "Clinic with this name already exists"
}
```

**Response (Error - Empty URL):**
```json
{
  "error": "Clinic URL cannot be empty"
}
```

**Response (Error - Duplicate URL):**
```json
{
  "error": "Clinic with this URL already exists"
}
```

**Response (Error - Invalid Module):**
```json
{
  "error": "Module with id {module_id} not found"
}
```

**Status Codes:**
- `200 OK`: Updated successfully
- `400 Bad Request`: Validation error or duplicate values
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: User is not staff or clinic manager
- `404 Not Found`: Clinic not found
- `500 Internal Server Error`: Server error occurred

**Notes:**
- Only provided fields will be updated
- When updating `selected_modules`, all existing module associations are removed and replaced with the new list
- Duplicate name/URL checks exclude the current clinic
- Transaction is atomic - if any step fails, all changes are rolled back

---

#### DELETE - Delete Clinic
Deletes a clinic and all associated data.

**Authentication:** Required (Staff only)

**User Roles:**
- **Admin/Staff**: Can delete clinics

**URL Parameters:**
- `clinic_id`: The ID of the clinic

**Response:**
```json
{
  "message": "Clinic deleted successfully"
}
```

**Status Codes:**
- `204 No Content`: Deleted successfully
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: User is not staff
- `404 Not Found`: Clinic not found
- `500 Internal Server Error`: Server error occurred

**Cascading Deletions:**
When a clinic is deleted, the following associated data is also deleted:
1. **Clinic Medications** (`ClinicMedicine`)
2. **Medication Bundles** (`MedicationsBundle`)
3. **Clinic Activities** (`ClinicActivity`)
4. **Activities Bundles** (`ActivitiesBundle`)
5. **Clinic Modules** (`ClinicModules`)
6. **Doctor-Clinic Associations** (`DoctorClinic`)
7. **Patient-Clinic Associations** (`PatientClinic`)
8. **Patient-Doctor Associations** (`PatientDoctor`)
9. **Clinic Manager Association** (`ManagerClinic`)
10. **Clinic Manager User** (`ClinicManager` and `User`)

**Notes:**
- This is a destructive operation and cannot be undone
- All patient data, doctor associations, and clinic content will be permanently deleted
- The clinic manager's user account is also deleted
- Transaction is atomic - if any step fails, all changes are rolled back

---

## Common Error Responses

### 401 Unauthorized
```json
{
  "error": "Authentication required"
}
```

### 403 Forbidden (Not Staff)
```json
{
  "error": "Permission denied , user is not staff"
}
```

### 403 Forbidden (Not Staff or Clinic Manager)
```json
{
  "error": "Permission denied , user is not staff or clinic manager"
}
```

### 404 Not Found
```json
{
  "error": "Clinic not found"
}
```

### 400 Bad Request
```json
{
  "error": "All fields are required"
}
```

### 500 Internal Server Error
```json
{
  "error": "Error message describing what went wrong"
}
```

---

## Permission Summary

| Endpoint | Admin/Staff | Clinic Manager | Doctor | Patient |
|----------|-------------|----------------|--------|---------|
| GET /api/v1/clinics/ | ✓ | ❌ | ❌ | ❌ |
| POST /api/v1/clinics/ | ✓ | ❌ | ❌ | ❌ |
| GET /api/v1/clinics/{id}/ | ✓ | ✓ | ✓ | ✓ |
| PUT /api/v1/clinics/{id}/ | ✓ | ✓ (own clinic) | ❌ | ❌ |
| DELETE /api/v1/clinics/{id}/ | ✓ | ❌ | ❌ | ❌ |

---

## RESTful Design Principles Applied

1. **Resource-Based URLs**: URLs represent resources (`/clinics/`, `/clinics/{id}/`), not actions
2. **HTTP Methods**: Use standard HTTP methods (GET, POST, PUT, DELETE) for CRUD operations
3. **Proper Status Codes**: 
   - `200 OK` for successful GET/PUT
   - `201 Created` for successful POST
   - `204 No Content` for successful DELETE
   - `400 Bad Request` for validation errors
   - `401 Unauthorized` for authentication issues
   - `403 Forbidden` for authorization issues
   - `404 Not Found` for missing resources
   - `500 Internal Server Error` for server errors
4. **Idempotency**: DELETE and PUT operations are idempotent
5. **Atomic Transactions**: All write operations use database transactions to ensure data consistency

---

## Business Rules

1. **Clinic Creation**:
   - Clinic name must be unique across the system
   - Clinic URL must be unique across the system
   - A clinic manager is automatically created and linked to the clinic
   - Manager email must be unique (enforced at user level)

2. **Clinic Manager**:
   - Each clinic must have exactly one clinic manager
   - The clinic manager is created as a new user during clinic creation
   - Deleting a clinic also deletes the associated manager and their user account

3. **Modules**:
   - Clinics can have zero or more modules
   - Modules must exist in the system before being assigned to a clinic
   - Updating modules replaces the entire module list (not additive)

4. **Clinic Types**:
   - "Research" clinics set `is_research_clinic` flag to `true`
   - All other types (including "Default") set the flag to `false`

5. **Authorization**:
   - Only staff users can list all clinics
   - Only staff users can create new clinics
   - Only staff users can delete clinics
   - Both staff and clinic managers can update clinic details
   - All authenticated users can view individual clinic details

---

## Data Models

### Clinic
```python
{
  "id": Integer (Primary Key),
  "clinic_name": String (Unique),
  "clinic_url": String (Unique),
  "clinic_image_url": String (Optional),
  "is_research_clinic": Boolean
}
```

### Related Models
- **ManagerClinic**: Links clinic to its manager
- **ClinicModules**: Links clinic to available modules
- **DoctorClinic**: Links doctors to clinics
- **PatientClinic**: Links patients to clinics
- **ClinicMedicine**: Medications available in clinic
- **ClinicActivity**: Activities available in clinic
- **MedicationsBundle**: Medication bundles in clinic
- **ActivitiesBundle**: Activity bundles in clinic

---

## Example Workflows

### Creating a New Clinic
1. Admin calls `POST /api/v1/clinics/` with clinic and manager details
2. System creates clinic record
3. System creates clinic manager user account
4. System links manager to clinic via `ManagerClinic`
5. System associates specified modules with clinic via `ClinicModules`
6. Manager receives welcome email with credentials
7. Returns success response

### Updating Clinic Modules
1. Staff/Manager calls `PUT /api/v1/clinics/{id}/` with `selected_modules`
2. System validates all module IDs exist
3. System deletes all existing `ClinicModules` records for clinic
4. System creates new `ClinicModules` records for each specified module
5. Returns success response

### Deleting a Clinic
1. Admin calls `DELETE /api/v1/clinics/{id}/`
2. System begins transaction
3. System deletes all clinic medications and bundles
4. System deletes all clinic activities and bundles
5. System deletes all clinic module associations
6. System deletes all doctor and patient associations
7. System deletes clinic manager and user account
8. System deletes clinic record
9. Transaction commits
10. Returns success response

---

## Notes

1. **Authentication**: All endpoints require authentication
2. **Staff Permissions**: Most administrative operations require staff/admin privileges
3. **Clinic Manager Scope**: Clinic managers can only modify their own clinic
4. **Atomic Operations**: All create, update, and delete operations use transactions
5. **Cascading Deletes**: Deleting a clinic removes all associated data
6. **Email Notifications**: Clinic managers receive account setup emails upon creation
7. **Module Prerequisites**: Modules must exist in the system before being assigned to clinics
8. **URL Uniqueness**: Clinic URLs must be unique to prevent routing conflicts
