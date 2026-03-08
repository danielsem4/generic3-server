# Authentication API Documentation

## Table of Contents
1. [Session Management](#session-management)
2. [Token Management](#token-management)
3. [Two-Factor Authentication](#two-factor-authentication)
4. [Password Management](#password-management)
5. [TOTP/QR Code](#totpqr-code)

---

## Session Management

### 1. Create Session (Login)
**Endpoint:** `POST /api/v1/auth/sessions/`

Creates a new user session and returns authentication tokens with user profile.

**Authentication:** Not required (AllowAny)

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Required Fields:**
- `email`: User's email address
- `password`: User's password

**Response (Success - Single Clinic):**
```json
{
  "user": {
    "id": 5,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "1234567890",
    "role": "DOCTOR",
    "clinicId": 1,
    "clinicName": "Main Clinic",
    "clinic_image": "http://localhost:8000/static/images/Main_Clinic.png",
    "modules": [
      {"name": "Activities", "id": 1},
      {"name": "Medications", "id": 2}
    ],
    "status": "Success",
    "server_url": "https://clinic.example.com",
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

**Response (Multiple Clinics - Selection Required):**
```json
{
  "detail": "Multiple clinics found for this user",
  "clinics": [
    "https://clinic1.example.com",
    "https://clinic2.example.com"
  ]
}
```

**Cookies Set:**
- `access`: JWT access token (HttpOnly, 60 min expiry)
- `refresh`: JWT refresh token (HttpOnly, 24 hours expiry)

**Status Codes:**
- `201 Created`: Login successful, session created
- `202 Accepted`: Multiple clinics, user must select
- `400 Bad Request`: Email or password missing
- `401 Unauthorized`: Invalid credentials
- `403 Forbidden`: No clinics found for user

**Notes:**
- Returns clinic-specific data including modules
- Sets secure HTTP-only cookies for token storage
- For multi-clinic users, must login from correct clinic URL
- Staff users bypass clinic checks

---

### 2. Destroy Session (Logout)
**Endpoint:** `DELETE /api/v1/auth/sessions/`

Destroys the current user session and clears authentication tokens.

**Authentication:** Required

**Request Body:** None

**Response (Success):**
```json
{
  "message": "Logged out successfully"
}
```

**Response (Not Logged In):**
```json
{
  "message": "User was not logged in"
}
```

**Status Codes:**
- `204 No Content`: Logout successful
- `400 Bad Request`: User was not authenticated
- `401 Unauthorized`: Invalid or missing authentication

**Notes:**
- Deletes auth token from database
- Clears `access` and `refresh` cookies
- Invalidates current session

---

## Token Management

### 1. Refresh Access Token
**Endpoint:** `POST /api/v1/auth/tokens/refresh/`

Refreshes an expired access token using the refresh token from cookies.

**Authentication:** Not required (AllowAny)

**Request Body:** None (uses refresh token from cookie)

**Response (Success):**
```json
{
  "detail": "Token refreshed"
}
```

**Response (Error - No Refresh Token):**
```json
{
  "detail": "No refresh cookie"
}
```

**Response (Error - Invalid Token):**
```json
{
  "detail": "Invalid refresh token"
}
```

**Cookies Set:**
- `access`: New JWT access token (HttpOnly, 60 min expiry)

**Status Codes:**
- `200 OK`: Token refreshed successfully
- `401 Unauthorized`: No refresh token or invalid refresh token

**Notes:**
- Reads refresh token from `refresh` cookie
- Issues new access token
- Does not issue new refresh token
- Use before access token expires for seamless experience

---

## Two-Factor Authentication

### 1. Request 2FA Code
**Endpoint:** `POST /api/v1/auth/2fa/`

Requests a 2FA verification code to be sent to the user via email or SMS.

**Authentication:** Not required (AllowAny)

**Request Body:**
```json
{
  "email": "user@example.com",
  "send_method": "email"
}
```

**Required Fields:**
- `email`: User's email address

**Optional Fields:**
- `send_method`: Method to send code (`email` or `sms`, default: `email`)

**Response (Success):**
```json
{
  "message": "Credentials verified. Please enter 2FA code.",
  "requires_2fa": true
}
```

**Response (Error - Missing Email):**
```json
{
  "error": "Email is required"
}
```

**Response (Error - Invalid Email):**
```json
{
  "error": "Invalid email or password"
}
```

**Status Codes:**
- `200 OK`: 2FA code sent successfully
- `400 Bad Request`: Email missing
- `401 Unauthorized`: Invalid email

**Session Data Stored:**
- `pending_2fa_user_id`: User ID awaiting verification
- `pending_2fa_timestamp`: Timestamp for expiration check (5 min)

**Notes:**
- Verifies user exists before sending code
- Stores temporary session data for verification
- Session expires after 5 minutes
- Code sent via email or SMS based on `send_method`

---

### 2. Verify 2FA Code
**Endpoint:** `POST /api/v1/auth/2fa/verify/`

Verifies the 2FA code and completes the authentication process.

**Authentication:** Not required (AllowAny)

**Request Body:**
```json
{
  "code": "123456",
  "code_type": "login"
}
```

**Required Fields:**
- `code`: 6-digit verification code
- `code_type`: Type of verification (`login`, `signup`, etc.)

**Response (Success - Login):**
```json
{
  "message": "2FA verification successful",
  "user": {
    "id": 5,
    "email": "user@example.com"
  }
}
```

**Response (Error - Invalid Request):**
```json
{
  "error": "Invalid request"
}
```

**Response (Error - Expired Session):**
```json
{
  "error": "2FA session expired"
}
```

**Response (Error - Invalid Code):**
```json
{
  "error": "Invalid or expired 2FA code"
}
```

**Cookies Set (if code_type is "login"):**
- `access`: JWT access token (HttpOnly, 60 min expiry)
- `refresh`: JWT refresh token (HttpOnly, 24 hours expiry)

**Status Codes:**
- `200 OK`: Code verified successfully
- `400 Bad Request`: Invalid request, expired session, or wrong code

**Notes:**
- Validates code against stored session
- Session must be initiated within 5 minutes
- Clears pending session data on success or failure
- For login type, issues JWT tokens

---

## Password Management

### 1. Change Password
**Endpoint:** `PUT /api/v1/auth/password/`

Changes the user's password with validation.

**Authentication:** Required (IsAuthenticated) - User must be logged in

**Request Headers:**
```
Cookie: access=<jwt_access_token>
```

**Request Body:**
```json
{
  "old_password": "OldPass123!",
  "new_password": "NewSecure123!",
  "confirm_new_password": "NewSecure123!"
}
```

**Required Fields:**
- `old_password`: Current password for verification
- `new_password`: New password
- `confirm_new_password`: Password confirmation (must match)

**Password Requirements:**
- Length: 8-20 characters
- At least one digit (0-9)
- At least one letter (a-z, A-Z)
- At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?/)
- At least one uppercase letter (A-Z)

**Response (Success):**
```json
{
  "message": "Password changed successfully"
}
```

**Response (Error - Missing Fields):**
```json
{
  "error": "Old password, new password, and confirm new password are required"
}
```

**Response (Error - Password Mismatch):**
```json
{
  "error": "New password and confirm new password do not match"
}
```

**Response (Error - Incorrect Old Password):**
```json
{
  "error": "Incorrect old password"
}
```

**Response (Error - Validation):**
```json
{
  "error": "Password must be between 8 and 20 characters"
}
```

```json
{
  "error": "Password must contain at least one digit"
}
```

```json
{
  "error": "Password must contain at least one letter"
}
```

```json
{
  "error": "Password must contain at least one special character"
}
```

```json
{
  "error": "Password must contain at least one uppercase letter"
}
```

**Status Codes:**
- `200 OK`: Password changed successfully
- `400 Bad Request`: Validation error or missing fields
- `401 Unauthorized`: Invalid email

**Notes:**
- Requires user authentication via email
- Enforces strong password policy
- Both new password fields must match
- Old password is not required (uses email authentication)

---

## TOTP/QR Code

### 1. Get User QR Code
**Endpoint:** `GET /api/v1/auth/users/{user_id}/qr-code/`

Retrieves a QR code image for TOTP (Time-based One-Time Password) setup.

**Authentication:** Required (IsAuthenticated)

**URL Parameters:**
- `user_id`: The ID of the user

**Authorization:**
- Users can only get their own QR code
- Staff/Admin can get any user's QR code

**Response (Success):**
Returns a QR code image (binary data) that can be scanned by authenticator apps.

**Response (Error - User Not Found):**
```json
{
  "detail": "User not found"
}
```

**Response (Error - Permission Denied):**
```json
{
  "detail": "Permission denied"
}
```

**Status Codes:**
- `200 OK`: QR code image returned
- `403 Forbidden`: User trying to access another user's QR code
- `404 Not Found`: User not found

**Notes:**
- Returns image file for scanning with authenticator apps
- Used for setting up TOTP-based 2FA
- Non-staff users can only access their own QR code
- Typically used during account setup or 2FA enrollment

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
  "detail": "User not found"
}
```

### 400 Bad Request
```json
{
  "error": "Error message describing the issue"
}
```

---

## RESTful Design Principles Applied

1. **Resource-Based URLs**: 
   - `/sessions/` for login/logout (session management)
   - `/tokens/refresh/` for token operations
   - `/2fa/` and `/2fa/verify/` for two-factor auth
   - `/password/` for password management
   - `/users/{id}/qr-code/` for user-specific QR codes

2. **HTTP Methods**:
   - `POST` for creating sessions and requesting codes
   - `DELETE` for destroying sessions
   - `PUT` for updating passwords
   - `GET` for retrieving QR codes

3. **Proper Status Codes**:
   - `200 OK` for successful GET/POST operations
   - `201 Created` for successful login (session creation)
   - `202 Accepted` for pending multi-clinic selection
   - `204 No Content` for successful logout
   - `400 Bad Request` for validation errors
   - `401 Unauthorized` for authentication failures
   - `403 Forbidden` for authorization issues
   - `404 Not Found` for missing resources

4. **HTTP-Only Cookies**: Secure token storage using HTTP-only cookies

5. **Consistent Response Format**: JSON responses with consistent structure

6. **Stateless with Sessions**: JWT tokens for stateless auth, temporary sessions for 2FA flow

---

## Security Features

1. **JWT Tokens**: 
   - Access tokens expire in 60 minutes
   - Refresh tokens expire in 24 hours
   - Stored in HTTP-only cookies

2. **Cookie Security**:
   - HttpOnly: Prevents JavaScript access
   - Secure flag: HTTPS only in production
   - SameSite: CSRF protection

3. **2FA Support**:
   - Time-limited session (5 minutes)
   - Code sent via email or SMS
   - Session-based temporary storage

4. **Password Policy**:
   - Minimum length: 8 characters
   - Maximum length: 20 characters
   - Complexity requirements enforced

5. **TOTP Support**:
   - QR code generation for authenticator apps
   - Permission-based access control

---

## Authentication Flow

### Standard Login Flow:
1. `POST /api/v1/auth/sessions/` with email/password
2. Server validates credentials
3. Server checks clinic membership
4. Server generates JWT tokens
5. Server sets HTTP-only cookies
6. Client receives user profile with tokens

### 2FA Login Flow:
1. `POST /api/v1/auth/2fa/` with email
2. Server sends verification code
3. `POST /api/v1/auth/2fa/verify/` with code
4. Server validates code
5. Server generates JWT tokens (if login type)
6. Server sets HTTP-only cookies

### Token Refresh Flow:
1. Access token expires
2. `POST /api/v1/auth/tokens/refresh/` (automatic)
3. Server reads refresh token from cookie
4. Server issues new access token
5. Server updates access cookie

### Logout Flow:
1. `DELETE /api/v1/auth/sessions/`
2. Server deletes auth token
3. Server clears cookies
4. Session terminated

---

## Example Workflows

### Logging In
```bash
curl -X POST http://localhost:8000/api/v1/auth/sessions/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

### Refreshing Token
```bash
curl -X POST http://localhost:8000/api/v1/auth/tokens/refresh/ \
  -b "refresh=<refresh_token_from_cookie>"
```

### Logging Out
```bash
curl -X DELETE http://localhost:8000/api/v1/auth/sessions/ \
  -H "Authorization: Bearer <access_token>"
```

### Requesting 2FA Code
```bash
curl -X POST http://localhost:8000/api/v1/auth/2fa/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "send_method": "email"
  }'
```

### Verifying 2FA Code
```bash
curl -X POST http://localhost:8000/api/v1/auth/2fa/verify/ \
  -H "Content-Type: application/json" \
  -d '{
    "code": "123456",
    "code_type": "login"
  }'
```

### Changing Password
```bash
curl -X PUT http://localhost:8000/api/v1/auth/password/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "new_password": "NewSecure123!",
    "confirm_new_password": "NewSecure123!"
  }'
```

### Getting QR Code
```bash
curl -X GET http://localhost:8000/api/v1/auth/users/5/qr-code/ \
  -H "Authorization: Bearer <access_token>" \
  --output qrcode.png
```

---

## Data Models

### sentMessages
```python
{
  "id": Integer (Primary Key),
  "userid": String (User ID),
  "msg_type": String (EMAIL or SMS),
  "sender": String (Sender email/phone),
  "destinatary": String (Recipient email/phone),
  "sent_date": DateTime (Default: now),
  "status": String (SUCCESS or FAIL),
  "registered": Boolean (Default: False)
}
```

**Message Types:**
- `EMAIL`: Email message
- `SMS`: SMS/Text message

**Status Values:**
- `SUCCESS`: Message sent successfully
- `FAIL`: Message failed to send

---

## Notes

1. **Multi-Clinic Support**: Users can belong to multiple clinics but must access from correct clinic URL
2. **Cookie-Based Auth**: Tokens stored in HTTP-only cookies for security
3. **Session Expiry**: 2FA sessions expire after 5 minutes
4. **Token Expiry**: Access tokens expire after 60 minutes, refresh tokens after 24 hours
5. **Password Security**: Strong password policy enforced with multiple requirements
6. **TOTP Integration**: QR codes for authenticator app setup
7. **Message Logging**: All 2FA messages logged in sentMessages model
