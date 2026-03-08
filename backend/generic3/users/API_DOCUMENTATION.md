# Users API Documentation

## Table of Contents
1. [User Endpoints](#user-endpoints)

---

## User Endpoints

### 1. List/Create Users
**Endpoint:** `GET/POST /api/v1/users/`

#### GET - List All Users
Lists users in the system with pagination and role-based filtering.

**Authentication:** Required (Staff only - Admin, Clinic Manager, Doctor)

**User Roles:**
- **Admin**: Can view all users
- **Clinic Manager**: Can view doctors and patients in their clinic
- **Doctor**: Can view their assigned patients in the current clinic

**Query Parameters:**
- `role` (optional): Filter by user role. Values: `ADMIN`, `CLINIC_MANAGER`, `DOCTOR`, `PATIENT`, `RESEARCH_PATIENT`
- `page` (optional): Page number for pagination (default: 1)
- `page_size` (optional): Number of results per page (default: 20, max: 100)

**Example Requests:**
```
GET /api/v1/users/
GET /api/v1/users/?role=DOCTOR
GET /api/v1/users/?role=PATIENT&page=2&page_size=50
```

**Response:**
```json
{
  "count": 45,
  "next": "http://localhost:8000/api/v1/users/?page=2",
  "previous": null,
  "results": [
    {
      "id": 5,
      "email": "doctor1@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "phone_number": "1234567890",
      "role": "DOCTOR"
    },
    {
      "id": 7,
      "email": "patient1@example.com",
      "first_name": "Jane",
      "last_name": "Smith",
      "phone_number": "0987654321",
      "role": "PATIENT"
    }
  ]
}
```

**Status Codes:**
- `200 OK`: Success
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: User is not staff (patients cannot access)

---

#### POST - Create User
Creates a new user and assigns them to the current clinic.

**Authentication:** Required (Staff only - Admin, Clinic Manager, Doctor)

**User Roles & Permissions:**
- **Clinic Manager**: Can create doctors
- **Doctor**: Can create patients or research patients (depending on clinic type)
- **Admin**: Can create any user type

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "1234567890",
  "password": "SecurePass123!",
  "confirm_password": "SecurePass123!"
}
```

**Required Fields:**
- `email`: User's email address (must be unique)
- `first_name`: User's first name
- `last_name`: User's last name
- `phone_number`: User's phone number

**Optional Fields:**
- `password`: User's password (required for research patients, optional for others)
- `confirm_password`: Password confirmation (must match password if provided)

**Business Logic:**
- **Clinic Manager** creates → Doctor role assigned
- **Doctor** in regular clinic creates → Patient role assigned
- **Doctor** in research clinic creates → Research Patient role assigned
- If user exists with same email/phone, system validates data matches and assigns to clinic
- For non-research patients: temporary password generated and sent via email
- For research patients: password is required and must be provided

**Response (Success):**
```json
{
  "detail": "User added to clinic successfully",
  "user_id": 15
}
```

**Response (Error - Validation):**
```json
{
  "email": ["This field is required."],
  "first_name": ["This field is required."]
}
```

**Response (Error - Password Mismatch):**
```json
{
  "confirm_password": ["Passwords do not match"]
}
```

**Response (Error - User Exists):**
```json
{
  "detail": "User exists but provided data doesn't match existing user"
}
```

**Response (Error - Role Not Supported):**
```json
{
  "detail": "User role is not supported"
}
```

**Status Codes:**
- `201 Created`: User created successfully
- `400 Bad Request`: Validation error or data mismatch
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: User is not staff

**Notes:**
- Automatically creates Doctor or Patient profile based on role
- Links user to current clinic via session `current_clinic_id`
- Assigns patient to the creating doctor (for patient roles)
- Assigns all clinic modules to patients automatically
- Sends welcome email with temporary password (except research patients)

---

### 2. Current User Profile
**Endpoint:** `GET /api/v1/users/me/`

#### GET - Get Current User Profile
Retrieves the authenticated user's own profile information.

**Authentication:** Required

**User Roles:**
- Any authenticated user can access their own profile

**Response:**
```json
{
  "id": 5,
  "email": "doctor1@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "1234567890",
  "role": "DOCTOR",
  "patient_modules": null
}
```

**Response (Patient with Modules):**
```json
{
  "id": 7,
  "email": "patient1@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "phone_number": "0987654321",
  "role": "PATIENT",
  "patient_modules": [
    {
      "id": 1,
      "name": "Activities Tracking",
      "description": "Track daily activities",
      "active": true
    },
    {
      "id": 2,
      "name": "Medication Management",
      "description": "Manage medications",
      "active": true
    }
  ]
}
```

**Status Codes:**
- `200 OK`: Success
- `401 Unauthorized`: Not authenticated

**Notes:**
- Returns patient modules only for users with PATIENT or RESEARCH_PATIENT role
- Modules are filtered by current clinic from session
- Useful for frontend to display current user information

---

### 3. User Details
**Endpoint:** `GET/PUT/PATCH/DELETE /api/v1/users/{user_id}/`

#### GET - Get User Details
Retrieves detailed information about a specific user.

**Authentication:** Required

**User Roles:**
- Any authenticated user can view user details

**URL Parameters:**
- `user_id`: The ID of the user

**Response:**
```json
{
  "id": 5,
  "email": "doctor1@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "1234567890",
  "role": "DOCTOR",
  "patient_modules": null
}
```

**Response (Patient):**
```json
{
  "id": 7,
  "email": "patient1@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "phone_number": "0987654321",
  "role": "PATIENT",
  "patient_modules": [
    {
      "id": 1,
      "name": "Activities Tracking",
      "description": "Track daily activities",
      "active": true
    },
    {
      "id": 2,
      "name": "Medication Management",
      "description": "Manage medications",
      "active": false
    }
  ]
}
```

**Status Codes:**
- `200 OK`: Success
- `401 Unauthorized`: Not authenticated
- `404 Not Found`: User not found

---

#### PUT - Full Update User
Updates all fields of a user's profile.

**Authentication:** Required

**User Roles:**
- Any authenticated user can update user details (typically their own or their patients)

**URL Parameters:**
- `user_id`: The ID of the user

**Request Body:**
```json
{
  "email": "updated@example.com",
  "first_name": "Updated",
  "last_name": "Name",
  "phone_number": "9876543210"
}
```

**Updatable Fields:**
- `email`: User's email address
- `first_name`: User's first name
- `last_name`: User's last name
- `phone_number`: User's phone number

**Read-Only Fields:**
- `id`: Cannot be changed
- `role`: Cannot be changed

**Response (Success):**
```json
{
  "detail": "User updated successfully"
}
```

**Response (Error - Validation):**
```json
{
  "email": ["Enter a valid email address."],
  "phone_number": ["This field may not be blank."]
}
```

**Status Codes:**
- `200 OK`: Updated successfully
- `400 Bad Request`: Validation error
- `401 Unauthorized`: Not authenticated
- `404 Not Found`: User not found

---

#### PATCH - Partial Update User
Updates specific fields of a user's profile without requiring all fields.

**Authentication:** Required

**User Roles:**
- Any authenticated user can update user details

**URL Parameters:**
- `user_id`: The ID of the user

**Request Body (Example - Update only phone):**
```json
{
  "phone_number": "1112223333"
}
```

**Request Body (Example - Update name only):**
```json
{
  "first_name": "NewFirst",
  "last_name": "NewLast"
}
```

**Updatable Fields:**
- `email`: User's email address (optional)
- `first_name`: User's first name (optional)
- `last_name`: User's last name (optional)
- `phone_number`: User's phone number (optional)

**Response (Success):**
```json
{
  "detail": "User updated successfully"
}
```

**Response (Error):**
```json
{
  "email": ["This field must be unique."]
}
```

**Status Codes:**
- `200 OK`: Updated successfully
- `400 Bad Request`: Validation error
- `401 Unauthorized`: Not authenticated
- `404 Not Found`: User not found

**Notes:**
- PATCH allows partial updates - only send fields you want to change
- PUT requires all fields to be sent

---

#### DELETE - Delete/Remove User
Deletes a user permanently (Admin only) or removes them from the current clinic (Clinic Manager/Doctor).

**Authentication:** Required (Staff only)

**User Roles:**
- **Admin**: Permanently deletes user from database
- **Clinic Manager**: Removes user from their clinic
- **Doctor**: Removes patient from current clinic

**URL Parameters:**
- `user_id`: The ID of the user

**Admin Behavior:**
- Permanently deletes the user account from the database
- Validates that doctors don't have assigned patients before deletion
- Cannot delete yourself

**Non-Admin Behavior (Clinic Manager/Doctor):**
- Removes user from the current clinic (does not delete account)
- Removes clinic associations (DoctorClinic, PatientClinic, PatientDoctor)
- Cannot remove clinic managers (must be done via clinic management)
- Clinic managers cannot remove doctors with assigned patients
- Cannot remove yourself

**Response (Admin - Success):**
```json
{
  "detail": "User permanently deleted"
}
```

**Response (Non-Admin - Success):**
```json
{
  "detail": "User removed from clinic successfully"
}
```

**Response (Error - Cannot Delete Self):**
```json
{
  "detail": "Cannot delete yourself"
}
```

**Response (Error - Doctor Has Patients):**
```json
{
  "detail": "Cannot delete doctor with assigned patients. Remove patients first."
}
```

**Response (Error - Cannot Remove Doctor with Patients):**
```json
{
  "detail": "Cannot remove doctor with assigned patients"
}
```

**Response (Error - Cannot Delete Manager):**
```json
{
  "detail": "Cannot delete clinic manager - Only via clinic management"
}
```

**Response (Error - Permission Denied):**
```json
{
  "detail": "Permission denied"
}
```

**Status Codes:**
- `200 OK`: User deleted/removed successfully
- `400 Bad Request`: Business rule violation
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: User or clinic not found

**Notes:**
- Admin deletion is permanent and irreversible
- Non-admin deletion only removes clinic associations
- User can be re-added to clinic after removal
- Deleting removes all patient modules, doctor-patient relationships

---

## Common Error Responses

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden (Not Staff)
```json
{
  "error": "Permission denied, user is not staff"
}
```

### 404 Not Found
```json
{
  "detail": "User not found"
}
```

### 400 Bad Request
```json
{
  "field_name": ["Error message describing the issue"]
}
```

---

## Permission Summary

| Endpoint | Admin | Clinic Manager | Doctor | Patient |
|----------|-------|----------------|--------|---------|
| GET /api/v1/users/ | ✓ (all) | ✓ (clinic users) | ✓ (patients) | ❌ |
| POST /api/v1/users/ | ✓ | ✓ (doctors) | ✓ (patients) | ❌ |
| GET /api/v1/users/me/ | ✓ | ✓ | ✓ | ✓ |
| GET /api/v1/users/{id}/ | ✓ | ✓ | ✓ | ✓ |
| PUT /api/v1/users/{id}/ | ✓ | ✓ | ✓ | ✓ |
| PATCH /api/v1/users/{id}/ | ✓ | ✓ | ✓ | ✓ |
| DELETE /api/v1/users/{id}/ | ✓ (permanent) | ✓ (remove) | ✓ (remove) | ❌ |

---

## RESTful Design Principles Applied

1. **Resource-Based URLs**: URLs represent resources (`/users/`, `/users/{id}/`, `/users/me/`)
2. **HTTP Methods**: Standard CRUD operations (GET, POST, PUT, PATCH, DELETE)
3. **Proper Status Codes**:
   - `200 OK` for successful GET/PUT/PATCH/DELETE
   - `201 Created` for successful POST
   - `400 Bad Request` for validation errors
   - `401 Unauthorized` for authentication issues
   - `403 Forbidden` for authorization issues
   - `404 Not Found` for missing resources
4. **Pagination**: Large result sets are paginated with count, next, and previous links
5. **Filtering**: Support for filtering by role via query parameters
6. **Consistent Response Format**: JSON responses with consistent structure
7. **Partial Updates**: PATCH method for partial updates, PUT for full updates
8. **Self-Resource**: `/me/` endpoint for accessing current user's own profile

---

## Business Rules

1. **User Creation**:
   - Email and phone number must be unique
   - Role is determined by creator's role and clinic type
   - Clinic Manager creates Doctors
   - Doctor creates Patients or Research Patients
   - Existing users can be re-assigned to clinics

2. **Password Management**:
   - Research patients must provide password during creation
   - Regular patients receive temporary password via email
   - Password confirmation required when password is provided

3. **User Roles**:
   - `ADMIN`: System administrator with full access
   - `CLINIC_MANAGER`: Manages a specific clinic
   - `DOCTOR`: Medical professional treating patients
   - `PATIENT`: Regular patient in clinic
   - `RESEARCH_PATIENT`: Patient in research clinic

4. **Clinic Associations**:
   - Users are linked to clinics via session `current_clinic_id`
   - Patients are automatically linked to creating doctor
   - All clinic modules assigned to patients upon creation

5. **Deletion Behavior**:
   - Admin: Permanent deletion from database
   - Non-Admin: Removal from clinic only
   - Cannot delete/remove yourself
   - Cannot delete doctors with assigned patients
   - Cannot delete clinic managers (use clinic management)

6. **Authorization**:
   - Patients cannot create or list users
   - Clinic managers can only manage users in their clinic
   - Doctors can only manage their assigned patients
   - Admin has unrestricted access

---

## Data Models

### User
```python
{
  "id": Integer (Primary Key),
  "email": String (Unique),
  "username": String (Same as email),
  "first_name": String,
  "last_name": String,
  "phone_number": String,
  "role": String (Enum: ADMIN, CLINIC_MANAGER, DOCTOR, PATIENT, RESEARCH_PATIENT),
  "password": String (Hashed)
}
```

### Related Models
- **Doctor**: OneToOne relationship with User (for DOCTOR role)
- **Patient**: OneToOne relationship with User (for PATIENT/RESEARCH_PATIENT role)
- **ClinicManager**: OneToOne relationship with User (for CLINIC_MANAGER role)
- **DoctorClinic**: Links doctors to clinics
- **PatientClinic**: Links patients to clinics
- **PatientDoctor**: Links patients to their assigned doctors
- **PatientModules**: Links patients to available modules with active status

---

## Example Workflows

### Creating a New Patient
1. Doctor calls `POST /api/v1/users/` with patient details
2. System validates email/phone uniqueness
3. System generates temporary password
4. System sends welcome email to patient
5. System creates Patient profile
6. System links patient to doctor via PatientDoctor
7. System links patient to clinic via PatientClinic
8. System assigns all clinic modules to patient
9. Returns success with user_id

### Listing Clinic Patients (Doctor)
1. Doctor calls `GET /api/v1/users/?role=PATIENT`
2. System retrieves doctor's assigned patients in current clinic
3. System applies pagination (20 per page)
4. Returns paginated list with user details

### Getting Current User Profile
1. User calls `GET /api/v1/users/me/`
2. System retrieves authenticated user details
3. If patient, includes assigned modules for current clinic
4. Returns user profile with modules (if applicable)

### Updating User Phone Number
1. User calls `PATCH /api/v1/users/{id}/` with `{"phone_number": "new_number"}`
2. System validates phone number format
3. System updates only the phone_number field
4. Returns success message

### Removing Patient from Clinic (Doctor)
1. Doctor calls `DELETE /api/v1/users/{patient_id}/`
2. System validates permissions (doctor can remove patients)
3. System deletes PatientClinic association
4. System deletes PatientDoctor association
5. User account remains in database
6. Returns success message

### Permanently Deleting User (Admin)
1. Admin calls `DELETE /api/v1/users/{user_id}/`
2. System checks if user is doctor with patients
3. If doctor has patients, returns error
4. System permanently deletes user account
5. Cascading deletes remove all associations
6. Returns success message

---

## Pagination

The list users endpoint supports pagination with the following parameters:

- **page**: Page number to retrieve (default: 1)
- **page_size**: Number of results per page (default: 20, max: 100)

**Example Response Structure:**
```json
{
  "count": 156,
  "next": "http://localhost:8000/api/v1/users/?page=3&page_size=20",
  "previous": "http://localhost:8000/api/v1/users/?page=1&page_size=20",
  "results": [
    // Array of user objects
  ]
}
```

---

## Notes

1. **Authentication**: All endpoints require authentication via session or token
2. **Current Clinic**: Most operations are scoped to `current_clinic_id` from session
3. **Role-Based Access**: Permissions vary significantly by user role
4. **Email Notifications**: Temporary passwords sent via email for new users
5. **Atomic Operations**: User creation includes multiple database operations in transaction
6. **Serializer Validation**: All input validated via DRF serializers
7. **Patient Modules**: Automatically assigned from clinic modules upon patient creation
8. **Existing Users**: Can be re-added to clinics if they already exist
9. **Phone Uniqueness**: Phone numbers must be unique across system
10. **Research Clinics**: Different password handling for research patients
