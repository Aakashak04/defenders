# Authentication Integration

## Overview

The attack simulator now authenticates with the Virtual Bank API before running attacks, ensuring that authenticated endpoints are properly tested.

## Authentication Flow

1. **Login First**: The simulator logs in with admin credentials before any attacks
2. **Token Extraction**: Extracts `access_token` from the login response
3. **Token Usage**: Automatically adds `Authorization: Bearer {token}` header to authenticated requests

## Credentials

- **Email**: `admin@virtualbank.com`
- **Password**: `AdminPass123!`

## Endpoints That Require Authentication

Based on the OpenAPI spec, these endpoints require the `Authorization: Bearer {token}` header:

- ✅ `/accounts` (GET, POST)
- ✅ `/accounts/{account_id}` (GET)
- ✅ `/accounts/{account_id}/freeze` (PATCH)
- ✅ `/accounts/{account_id}/unfreeze` (PATCH)
- ✅ `/accounts/{from_id}/transfer` (POST)
- ✅ `/transactions` (GET)
- ✅ `/admin/audit-logs` (GET)
- ✅ `/admin/analytics` (GET)

## Endpoints That Don't Require Authentication

- `/health` (GET)
- `/auth/register` (POST)
- `/auth/login` (POST)
- `/auth/refresh` (POST)
- `/auth/logout` (POST)

## How It Works

### 1. Login Phase

```python
# At the start of run_attack_suite()
auth_token = await login_and_get_token(session, target_url)
```

The login function:
- Sends POST to `/auth/login` with credentials
- Extracts `access_token` from response
- Returns token for use in subsequent requests

### 2. Request Phase

For each request, the simulator:
- Checks if endpoint needs authentication
- Adds `Authorization: Bearer {token}` header if needed
- Sends request with proper authentication

### 3. Attack Patterns

All attack patterns that target authenticated endpoints now include the token:
- SQL Injection on `/accounts/{id}` → Uses token
- SQL Injection on `/transactions` → Uses token
- Path Traversal on `/accounts/{payload}` → Uses token
- RCE on `/admin/audit-logs` → Uses token
- XSS on `/transactions` → Uses token

**Exception**: SQL Injection on `/auth/login` doesn't use token (it's the login endpoint itself)

## Example Output

When you run the attack simulator:

```
🔐 Authenticating...
--------------------------------------------------------------------------------
✅ Successfully logged in as admin@virtualbank.com
   Access token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOi...

✅ Legitimate Requests (Should Pass Through):
--------------------------------------------------------------------------------
  ✅ ALLOWED | /health                              | Health check endpoint | Status: 200
  ✅ ALLOWED | /accounts                            | List accounts (requires auth) | Status: 200
  ...
```

## Error Handling

If login fails:
- Warning message is displayed
- Simulator continues (some requests may fail with 401/403)
- This allows testing of unauthenticated attack scenarios

## Benefits

1. **Realistic Testing**: Tests actual authenticated endpoints
2. **Better Coverage**: Can test protected endpoints that require auth
3. **Accurate Results**: Shows how defender handles authenticated vs unauthenticated requests
4. **Admin Access**: Uses admin credentials to test admin-only endpoints

## Customization

To change credentials, edit `attack.py`:

```python
ADMIN_EMAIL = "your-email@example.com"
ADMIN_PASSWORD = "YourPassword123!"
```

## Security Note

⚠️ **Important**: The credentials are hardcoded in the attack script for testing purposes. In production, never commit credentials to version control. Use environment variables or secure credential storage.

