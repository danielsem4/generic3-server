# File Share API Documentation

## Table of Contents
1. [File Share Endpoints](#file-share-endpoints)

---

## File Share Endpoints

### 1. List/Upload Files
**Endpoint:** `GET/POST /api/v1/fileshare/`

#### GET - List Files
Lists files based on user role and query parameters.

**Authentication:** Required

**User Roles:**
- **Admin/Staff**: Can view all files in the system
- **Clinic Manager**: Can view all files for their clinic (requires `clinic_id`)
- **Doctor**: Can view files for specific patient (requires `clinic_id` and `patient_id`)
- **Patient/Research Patient**: Can view their own files

**Query Parameters:**
- `clinic_id` (optional for patients, required for clinic managers and doctors): Filter files by clinic
- `patient_id` (optional for clinic managers, required for doctors): Filter files by patient

**Response:**
```json
[
  {
    "id": 1,
    "file_name": "medical_report.pdf",
    "file_path": "clinic/1/patient/5/fileShare/medical_report.pdf",
    "size": 245678,
    "upload_date": "2026-01-25T10:30:00Z",
    "clinic_id": "Main Clinic",
    "patient_id": "John Doe",
    "doctor_id": "Dr. Jane Smith"
  }
]
```

**Status Codes:**
- `200 OK`: Success
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: Unauthorized role or missing required parameters
- `404 Not Found`: Clinic, doctor, or patient not found

---

#### POST - Upload Files
Uploads one or more files to S3 and stores metadata in the database.

**Authentication:** Required (Doctor, Patient, or Research Patient only)

**User Roles:**
- **Doctor**: Can upload files for their patients
- **Patient/Research Patient**: Can upload their own files

**Content-Type:** `multipart/form-data`

**Form Data:**
- `clinic_id` (required): The clinic ID
- `patient_id` (required): The patient's user ID
- `files` (required): One or more files to upload

**Request Example:**
```
POST /api/v1/fileshare/
Content-Type: multipart/form-data

clinic_id=1
patient_id=5
files=<file1>
files=<file2>
```

**Response (Success):**
```json
{
  "uploaded_files": [
    {
      "id": 1,
      "name": "medical_report.pdf",
      "path": "clinic/1/patient/5/fileShare/medical_report.pdf",
      "size": 245678,
      "content_type": "application/pdf"
    },
    {
      "id": 2,
      "name": "xray_image.jpg",
      "path": "clinic/1/patient/5/fileShare/xray_image.jpg",
      "size": 512345,
      "content_type": "image/jpeg"
    }
  ]
}
```

**Response (Error - Missing Fields):**
```json
{
  "detail": "patient_id is required"
}
```

```json
{
  "detail": "clinic_id is required"
}
```

```json
{
  "detail": "No files uploaded"
}
```

**Response (Error - Not Found):**
```json
{
  "detail": "Clinic not found"
}
```

```json
{
  "detail": "Patient not found"
}
```

**Response (Error - Permission Denied):**
```json
{
  "detail": "Only doctors and patients can upload files"
}
```

**Status Codes:**
- `201 Created`: Files uploaded successfully
- `400 Bad Request`: Missing required fields or no files provided
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: User role not allowed to upload files
- `404 Not Found`: Clinic or patient not found
- `500 Internal Server Error`: S3 upload failed or server error

**Notes:**
- Files are stored in S3 at path: `clinic/{clinic_id}/patient/{patient_id}/fileShare/{filename}`
- Content type is automatically detected from file extension
- A notification is generated for the recipient (doctor or patient)
- Multiple files can be uploaded in a single request

---

### 2. File Details
**Endpoint:** `GET/DELETE /api/v1/fileshare/{id}/`

#### GET - View File
Retrieves a specific file's content in base64 encoding.

**Authentication:** Required

**User Roles:**
- All authenticated users can view files (permission checks apply)

**URL Parameters:**
- `id`: The file ID

**Response:**
```json
{
  "base64_data": "JVBERi0xLjQKJeLjz9MKMSAwIG9iago8PC9UeXBlL...",
  "content_type": "application/pdf"
}
```

**Response (Error - File Not Found in Database):**
```json
{
  "detail": "File not found"
}
```

**Response (Error - File Not Found in S3):**
```json
{
  "detail": "File not found in S3"
}
```

**Status Codes:**
- `200 OK`: Success
- `401 Unauthorized`: Not authenticated
- `404 Not Found`: File not found in database or S3

**Notes:**
- File content is returned as base64-encoded string
- Content type is provided for proper client-side handling
- Large files may take time to retrieve and encode

---

#### DELETE - Delete File
Deletes a file from both S3 storage and the database.

**Authentication:** Required

**User Roles:**
- **Admin/Staff**: Can delete any file
- **Doctor**: Can delete files they uploaded (file.doctor == current user)
- **Patient/Research Patient**: Can delete their own files (file.patient == current user)

**URL Parameters:**
- `id`: The file ID

**Response:**
```
(No content - HTTP 204)
```

**Response (Error - Unauthorized):**
```json
{
  "detail": "Unauthorized"
}
```

**Response (Error - File Not Found):**
```json
{
  "detail": "File not found"
}
```

**Response (Error - S3 Deletion Failed):**
```json
{
  "error": "Failed to delete file from S3"
}
```

**Status Codes:**
- `204 No Content`: File deleted successfully
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: User not authorized to delete this file
- `404 Not Found`: File not found
- `500 Internal Server Error`: Failed to delete from S3 or database error

**Notes:**
- File is deleted from both S3 and database
- If S3 deletion fails, database record is not removed
- Operation cannot be undone

---

## Common Error Responses

### 401 Unauthorized
```json
{
  "detail": "Authentication required"
}
```

### 403 Forbidden (Permission Denied)
```json
{
  "detail": "Only doctors and patients can upload files"
}
```

```json
{
  "detail": "Unauthorized"
}
```

### 404 Not Found
```json
{
  "detail": "File not found"
}
```

```json
{
  "detail": "Clinic not found"
}
```

```json
{
  "detail": "Patient not found"
}
```

```json
{
  "detail": "Doctor not found"
}
```

```json
{
  "detail": "File not found in S3"
}
```

### 400 Bad Request
```json
{
  "detail": "patient_id is required"
}
```

```json
{
  "detail": "clinic_id is required"
}
```

```json
{
  "detail": "No files uploaded"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Error uploading filename.pdf: [error message]"
}
```

```json
{
  "error": "Failed to delete file from S3"
}
```

```json
{
  "detail": "Error deleting file: [error message]"
}
```

---

## Permission Summary

| Endpoint | Admin/Staff | Clinic Manager | Doctor | Patient |
|----------|-------------|----------------|--------|---------|
| GET /api/v1/fileshare/ | ✓ (all files) | ✓ (clinic files) | ✓ (patient files) | ✓ (own files) |
| POST /api/v1/fileshare/ | ❌ | ❌ | ✓ | ✓ |
| GET /api/v1/fileshare/{id}/ | ✓ | ✓ | ✓ | ✓ |
| DELETE /api/v1/fileshare/{id}/ | ✓ | ❌ | ✓ (own uploads) | ✓ (own files) |

---

## RESTful Design Principles Applied

1. **Resource-Based URLs**: URLs represent resources (`/fileshare/`, `/fileshare/{id}/`), not actions
2. **HTTP Methods**: Use standard HTTP methods (GET, POST, DELETE) for CRUD operations
3. **Proper Status Codes**: 
   - `200 OK` for successful GET
   - `201 Created` for successful POST
   - `204 No Content` for successful DELETE (no response body)
   - `400 Bad Request` for validation errors
   - `401 Unauthorized` for authentication issues
   - `403 Forbidden` for authorization issues
   - `404 Not Found` for missing resources
   - `500 Internal Server Error` for server/S3 errors
4. **Consistent Response Format**: All endpoints use DRF's `Response` class
5. **Standard Field Names**: Uses `files` instead of HTML-specific field names

---

## Business Rules

1. **File Upload**:
   - Only doctors and patients can upload files
   - Both `clinic_id` and `patient_id` are required
   - At least one file must be provided
   - Files are stored in S3 with path: `clinic/{clinic_id}/patient/{patient_id}/fileShare/{filename}`
   - Doctor is automatically determined from patient-doctor relationship in the clinic
   - Content type is auto-detected from file extension

2. **File Access**:
   - Staff can view all files
   - Clinic managers can view files for their clinic
   - Doctors can view files for their patients
   - Patients can only view their own files
   - Files are returned as base64-encoded strings

3. **File Deletion**:
   - Staff can delete any file
   - Doctors can only delete files they uploaded
   - Patients can only delete their own files
   - File must be deleted from both S3 and database
   - If S3 deletion fails, database record is preserved

4. **Notifications**:
   - When a doctor uploads a file, the patient receives a notification
   - When a patient uploads a file, the doctor receives a notification

5. **Storage**:
   - All files are stored in AWS S3 bucket: `generic3-bucket`
   - Region: `il-central-1`
   - Files are organized by clinic and patient IDs

---

## Data Models

### SharedFiles
```python
{
  "id": Integer (Primary Key),
  "file_name": String,
  "file_path": String,
  "size": Integer (bytes),
  "upload_date": DateTime,
  "clinic": ForeignKey (Clinic),
  "patient": ForeignKey (Patient),
  "doctor": ForeignKey (Doctor, Optional)
}
```

---

## Example Workflows

### Uploading Files as a Doctor
1. Doctor calls `POST /api/v1/fileshare/` with form data:
   - `clinic_id`: 1
   - `patient_id`: 5
   - `files`: medical_report.pdf
2. System validates doctor, clinic, and patient exist
3. System determines doctor-patient relationship
4. Files are uploaded to S3
5. Metadata is saved to database
6. Notification is sent to patient
7. Returns list of uploaded files with IDs

### Viewing Patient Files
1. Patient calls `GET /api/v1/fileshare/`
2. System identifies user as patient
3. System retrieves all files where `patient` matches current user
4. Returns list of file metadata
5. Patient calls `GET /api/v1/fileshare/15/` to view specific file
6. System retrieves file from S3
7. File content is base64-encoded
8. Returns base64 data and content type

### Deleting a File
1. User calls `DELETE /api/v1/fileshare/15/`
2. System checks if user is authorized (staff, file owner, or uploader)
3. System deletes file from S3
4. If S3 deletion succeeds, database record is deleted
5. Returns 204 No Content

---

## Notes

1. **Authentication**: All endpoints require authentication via `@permission_classes([IsAuthenticated])`
2. **File Size**: No explicit file size limit is enforced at the API level (S3/server limits apply)
3. **Supported Formats**: All file types are supported; content type is auto-detected
4. **Multiple Files**: POST endpoint supports uploading multiple files in one request
5. **Base64 Encoding**: GET endpoint returns files as base64 strings for easy client-side handling
6. **S3 Integration**: All files are stored in S3, not on the application server
7. **Atomic Operations**: File uploads are atomic - if S3 upload fails, no database record is created
8. **Query Parameters**: GET list endpoint uses query parameters for filtering, not URL paths
9. **Field Name**: Uses standard `files` field name instead of HTML-specific names
10. **Doctor Assignment**: Doctor is automatically determined from patient-doctor-clinic relationship

---

## Security Considerations

1. **Authorization**: All endpoints check user roles and ownership
2. **File Access**: Users can only access files they're authorized to view
3. **S3 Permissions**: Files stored in S3 should have appropriate bucket policies
4. **Content Type Validation**: Content types are validated and sanitized
5. **Path Traversal**: File paths are constructed server-side to prevent path traversal attacks
6. **Authentication Required**: All endpoints require valid authentication tokens

---

## Migration from Non-RESTful Endpoints

The following non-RESTful endpoints have been removed and replaced:

### Removed Endpoints:
- ❌ `GET /api/v1/fileshare/files/{clinic_id}/{patient_id}/` 
- ❌ `POST /api/v1/fileshare/files/{clinic_id}/{patient_id}/add/`
- ❌ `DELETE /api/v1/fileshare/files/{clinic_id}/{patient_id}/delete/{file_id}/`

### New RESTful Approach:
- ✅ `GET /api/v1/fileshare/?clinic_id=X&patient_id=Y` - List files with query params
- ✅ `POST /api/v1/fileshare/` - Upload files with clinic_id and patient_id in body
- ✅ `DELETE /api/v1/fileshare/{id}/` - Delete file by ID

**Benefits:**
- Cleaner URLs following REST conventions
- Consistent with other API endpoints
- No action words in URLs (`/add/`, `/delete/`)
- Uses HTTP methods for actions instead of URL paths
- Better separation of concerns
