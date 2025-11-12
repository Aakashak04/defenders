# Virtual Bank - Complete URL Reference

## Overview

Complete reference of all URLs including frontend routes and backend API endpoints.

---

## 🌐 Frontend URLs (React SPA)

**Base URL:** `http://localhost:3000`

### Public Routes

```
http://localhost:3000/
```
**Description:** Home page (redirects to /dashboard)  
**Access:** Public (redirects to login if not authenticated)

```
http://localhost:3000/login
```
**Description:** Login page  
**Access:** Public  
**Features:** Email/password form, pre-filled with Alice's credentials

---

### Protected Routes (Require Authentication)

```
http://localhost:3000/dashboard
```
**Description:** Account dashboard  
**Access:** Authenticated users  
**Features:**
- View all accounts (role-based filtering)
- Account balances (decrypted)
- Account numbers and types
- Refresh button

```
http://localhost:3000/transfer
```
**Description:** Transfer money page  
**Access:** Authenticated users  
**Features:**
- Select source account
- Enter destination account ID
- Enter amount and note
- Review step
- Submit transfer
- View result

```
http://localhost:3000/transactions
```
**Description:** Transaction history  
**Access:** Authenticated users  
**Features:**
- Select account
- Filter by date range
- Filter by type (credit/debit/all)
- View transaction table
- Color-coded amounts

---

### Planned Frontend Routes

```
http://localhost:3000/kyc-upload
```
**Description:** KYC document upload  
**Access:** Customer  
**Features:**
- Upload ID documents
- Enter date of birth
- Enter address
- Submit for approval

```
http://localhost:3000/scheduled-transfers
```
**Description:** Manage scheduled/recurring transfers  
**Access:** Authenticated users  
**Features:**
- Create recurring transfers
- View scheduled transfers
- Pause/resume/cancel

```
http://localhost:3000/admin
```
**Description:** Admin dashboard  
**Access:** Admin, Management only  
**Features:**
- KPI cards (users, accounts, balance, transfers)
- Analytics charts (daily activity, account status)
- Pending KYC approvals
- System statistics

```
http://localhost:3000/admin/audit-logs
```
**Description:** Audit log viewer  
**Access:** Admin only  
**Features:**
- Filter by user, action, date
- View detailed audit trail
- Export logs

```
http://localhost:3000/admin/backups
```
**Description:** Database backup management  
**Access:** Admin only  
**Features:**
- View available backups
- Create manual backup
- Restore from backup
- Download backups

---

## 🔌 Backend API URLs

**Base URL:** `http://localhost:8000`

### Documentation URLs

```
http://localhost:8000/docs
```
**Description:** Swagger UI - Interactive API documentation  
**Access:** Public  
**Features:**
- Test endpoints directly
- View request/response schemas
- Authorize with Bearer token

```
http://localhost:8000/redoc
```
**Description:** ReDoc - Alternative API documentation  
**Access:** Public  
**Features:**
- Clean, readable format
- Detailed endpoint descriptions
- Schema definitions

```
http://localhost:8000/openapi.json
```
**Description:** OpenAPI specification (JSON)  
**Access:** Public  
**Use:** Import into API clients (Postman, Insomnia)

---

### Health & Status

```
http://localhost:8000/health
```
**Method:** GET  
**Description:** System health check  
**Access:** Public  
**Response:** `{"status": "ok"}`

---

### Authentication Endpoints

```
http://localhost:8000/auth/register
```
**Method:** POST  
**Description:** Register new user  
**Access:** Public

```
http://localhost:8000/auth/login
```
**Method:** POST  
**Description:** Login and get tokens  
**Access:** Public

```
http://localhost:8000/auth/refresh
```
**Method:** POST  
**Description:** Refresh access token  
**Access:** Public (with refresh token)

```
http://localhost:8000/auth/logout
```
**Method:** POST  
**Description:** Logout and revoke refresh token  
**Access:** Authenticated

---

### Account Endpoints

```
http://localhost:8000/accounts
```
**Method:** POST  
**Description:** Create new account  
**Access:** Admin, Management

```
http://localhost:8000/accounts
```
**Method:** GET  
**Description:** List accounts (role-based filtering)  
**Access:** Authenticated

```
http://localhost:8000/accounts/{account_id}
```
**Method:** GET  
**Description:** Get specific account details  
**Access:** Authenticated (own account or admin/management)  
**Example:** `http://localhost:8000/accounts/abc123-uuid`

```
http://localhost:8000/accounts/{account_id}/freeze
```
**Method:** PATCH  
**Description:** Freeze account  
**Access:** Admin, Management  
**Example:** `http://localhost:8000/accounts/abc123-uuid/freeze`

```
http://localhost:8000/accounts/{account_id}/unfreeze
```
**Method:** PATCH  
**Description:** Unfreeze account  
**Access:** Admin, Management  
**Example:** `http://localhost:8000/accounts/abc123-uuid/unfreeze`

```
http://localhost:8000/accounts/{account_id}/statement
```
**Method:** GET  
**Description:** Download account statement (PDF or CSV)  
**Access:** Authenticated (own account or admin/management)  
**Query Parameters:**
- `format=pdf` or `format=csv`
- `start_date=2025-01-01`
- `end_date=2025-12-31`  
**Example:** `http://localhost:8000/accounts/abc123-uuid/statement?format=pdf&start_date=2025-01-01&end_date=2025-12-31`

---

### Transfer Endpoints

```
http://localhost:8000/accounts/{from_id}/transfer
```
**Method:** POST  
**Description:** Transfer funds between accounts  
**Access:** Authenticated (must own source account or be admin/management)  
**Example:** `http://localhost:8000/accounts/abc123-uuid/transfer`

---

### Transaction Endpoints

```
http://localhost:8000/transactions
```
**Method:** GET  
**Description:** Get transaction history with filters  
**Access:** Authenticated  
**Query Parameters:**
- `account_id=abc123-uuid` (required)
- `start_date=2025-01-01` (optional)
- `end_date=2025-12-31` (optional)
- `transaction_type=credit|debit|all` (optional)  
**Example:** `http://localhost:8000/transactions?account_id=abc123-uuid&transaction_type=credit&start_date=2025-11-01`

---

### Scheduled Transfer Endpoints (Planned)

```
http://localhost:8000/scheduled-transfers
```
**Method:** POST  
**Description:** Create scheduled/recurring transfer  
**Access:** Authenticated

```
http://localhost:8000/scheduled-transfers
```
**Method:** GET  
**Description:** List scheduled transfers  
**Access:** Authenticated  
**Query Parameters:**
- `status=active|paused|cancelled|all`

```
http://localhost:8000/scheduled-transfers/{id}
```
**Method:** PATCH  
**Description:** Update scheduled transfer (pause/resume/cancel)  
**Access:** Authenticated (own transfer)  
**Example:** `http://localhost:8000/scheduled-transfers/xyz789-uuid`

---

### KYC Endpoints (Planned)

```
http://localhost:8000/users/kyc-upload
```
**Method:** POST  
**Description:** Upload KYC documents  
**Access:** Authenticated (customer)  
**Content-Type:** multipart/form-data

```
http://localhost:8000/users/{user_id}/kyc-status
```
**Method:** PATCH  
**Description:** Approve/reject KYC  
**Access:** Admin, Management  
**Example:** `http://localhost:8000/users/user123-uuid/kyc-status`

```
http://localhost:8000/users/pending-kyc
```
**Method:** GET  
**Description:** Get users with pending KYC  
**Access:** Admin, Management

---

### Admin Endpoints (Planned)

```
http://localhost:8000/admin/audit-logs
```
**Method:** GET  
**Description:** View audit logs  
**Access:** Admin only  
**Query Parameters:**
- `user_id=user123-uuid` (optional)
- `action=LOGIN` (optional)
- `start_date=2025-01-01` (optional)
- `end_date=2025-12-31` (optional)
- `limit=100` (optional, max 1000)  
**Example:** `http://localhost:8000/admin/audit-logs?action=TRANSFER&limit=50`

```
http://localhost:8000/admin/analytics
```
**Method:** GET  
**Description:** Get system analytics and statistics  
**Access:** Admin, Management

---

## 📊 Complete URL Map

### Frontend Routes (10 total)

| URL | Status | Access | Description |
|-----|--------|--------|-------------|
| `/` | ✅ Implemented | Public | Home (redirects) |
| `/login` | ✅ Implemented | Public | Login page |
| `/dashboard` | ✅ Implemented | Authenticated | Account dashboard |
| `/transfer` | ✅ Implemented | Authenticated | Transfer page |
| `/transactions` | ✅ Implemented | Authenticated | Transaction history |
| `/kyc-upload` | ⏳ Planned | Customer | KYC upload |
| `/scheduled-transfers` | ⏳ Planned | Authenticated | Scheduled transfers |
| `/admin` | ⏳ Planned | Admin/Management | Admin dashboard |
| `/admin/audit-logs` | ⏳ Planned | Admin | Audit logs |
| `/admin/backups` | ⏳ Planned | Admin | Backup management |

### Backend API Endpoints (21 total)

| URL | Method | Status | Access |
|-----|--------|--------|--------|
| `/health` | GET | ✅ Implemented | Public |
| `/docs` | GET | ✅ Implemented | Public |
| `/redoc` | GET | ✅ Implemented | Public |
| `/auth/register` | POST | ✅ Implemented | Public |
| `/auth/login` | POST | ✅ Implemented | Public |
| `/auth/refresh` | POST | ✅ Implemented | Public |
| `/auth/logout` | POST | ✅ Implemented | Authenticated |
| `/accounts` | POST | ✅ Implemented | Admin/Management |
| `/accounts` | GET | ✅ Implemented | Authenticated |
| `/accounts/{id}` | GET | ✅ Implemented | Authenticated |
| `/accounts/{id}/transfer` | POST | ✅ Implemented | Authenticated |
| `/transactions` | GET | ✅ Implemented | Authenticated |
| `/accounts/{id}/freeze` | PATCH | ⏳ Planned | Admin/Management |
| `/accounts/{id}/unfreeze` | PATCH | ⏳ Planned | Admin/Management |
| `/accounts/{id}/statement` | GET | ⏳ Planned | Authenticated |
| `/scheduled-transfers` | POST | ⏳ Planned | Authenticated |
| `/scheduled-transfers` | GET | ⏳ Planned | Authenticated |
| `/scheduled-transfers/{id}` | PATCH | ⏳ Planned | Authenticated |
| `/users/kyc-upload` | POST | ⏳ Planned | Customer |
| `/users/{id}/kyc-status` | PATCH | ⏳ Planned | Admin/Management |
| `/users/pending-kyc` | GET | ⏳ Planned | Admin/Management |
| `/admin/audit-logs` | GET | ⏳ Planned | Admin |
| `/admin/analytics` | GET | ⏳ Planned | Admin/Management |

---

## 🔗 Quick Access Links (Development)

### Frontend
- **Home:** http://localhost:3000
- **Login:** http://localhost:3000/login
- **Dashboard:** http://localhost:3000/dashboard
- **Transfer:** http://localhost:3000/transfer
- **Transactions:** http://localhost:3000/transactions

### Backend
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **ReDoc:** http://localhost:8000/redoc

---

## 🧪 Testing URLs

### Test Login (Alice)
```bash
# Frontend
http://localhost:3000/login
# Pre-filled: alice@virtualbank.com / AlicePass123!

# Backend API
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@virtualbank.com","password":"AlicePass123!"}'
```

### Test Dashboard
```bash
# Frontend
http://localhost:3000/dashboard

# Backend API
curl http://localhost:8000/accounts \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Test Transfer
```bash
# Frontend
http://localhost:3000/transfer

# Backend API
curl -X POST http://localhost:8000/accounts/ACCOUNT_ID/transfer \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"to_account_id":"DEST_ID","amount":"100.00","currency":"USD"}'
```

---

## 🌍 Environment-Specific URLs

### Development
- **Frontend:** http://localhost:3000
- **Backend:** http://localhost:8000

### Production (Example)
- **Frontend:** https://virtualbank.example.com
- **Backend:** https://api.virtualbank.example.com

### Staging (Example)
- **Frontend:** https://staging.virtualbank.example.com
- **Backend:** https://api-staging.virtualbank.example.com

---

## 📱 Mobile/PWA URLs (Future)

### Deep Links (Planned)
```
virtualbank://dashboard
virtualbank://transfer
virtualbank://transactions
virtualbank://account/{id}
```

---

## 🔒 CORS Configuration

**Allowed Origins (Development):**
- http://localhost:3000 (Frontend)
- http://127.0.0.1:3000 (Alternative localhost)

**Backend CORS Settings:**
```python
CORS_ORIGINS = ["http://localhost:3000"]
```

---

## 📋 URL Patterns

### Frontend (React Router)
```javascript
/                           → Navigate to /dashboard
/login                      → Login page
/dashboard                  → Dashboard page (protected)
/transfer                   → Transfer page (protected)
/transactions               → Transaction history (protected)
/kyc-upload                 → KYC upload (protected)
/scheduled-transfers        → Scheduled transfers (protected)
/admin                      → Admin dashboard (admin only)
/admin/audit-logs          → Audit logs (admin only)
/admin/backups             → Backup management (admin only)
*                          → 404 Not Found
```

### Backend (FastAPI)
```python
/health                                    → Health check
/docs                                      → Swagger UI
/redoc                                     → ReDoc
/auth/*                                    → Authentication
/accounts                                  → Account management
/accounts/{id}/*                          → Account operations
/transactions                              → Transaction history
/scheduled-transfers                       → Scheduled transfers
/scheduled-transfers/{id}                 → Scheduled transfer operations
/users/kyc-upload                         → KYC upload
/users/{id}/kyc-status                    → KYC status update
/users/pending-kyc                        → Pending KYC list
/admin/*                                   → Admin operations
```

---

## 🎯 Most Commonly Used URLs

### For Customers:
1. `http://localhost:3000/login` - Login
2. `http://localhost:3000/dashboard` - View accounts
3. `http://localhost:3000/transfer` - Send money
4. `http://localhost:3000/transactions` - View history

### For Admins:
1. `http://localhost:3000/admin` - Admin dashboard
2. `http://localhost:8000/admin/analytics` - System stats
3. `http://localhost:8000/admin/audit-logs` - Audit trail
4. `http://localhost:3000/admin/backups` - Backup management

### For Developers:
1. `http://localhost:8000/docs` - API documentation
2. `http://localhost:8000/health` - Health check
3. `http://localhost:8000/redoc` - Alternative docs

---

## 📊 Statistics

**Total URLs:** 31
- **Frontend Routes:** 10 (5 implemented, 5 planned)
- **Backend Endpoints:** 21 (10 implemented, 11 planned)

**By Access Level:**
- **Public:** 6 URLs
- **Authenticated:** 15 URLs
- **Admin/Management:** 10 URLs

**By Status:**
- **Implemented:** 15 URLs (48%)
- **Planned:** 16 URLs (52%)

---

## 🔍 URL Conventions

### Frontend
- Lowercase, hyphen-separated
- RESTful resource naming
- Protected routes require authentication
- Admin routes under `/admin` prefix

### Backend
- Lowercase, hyphen-separated
- RESTful conventions (GET, POST, PATCH, DELETE)
- Versioning in path (future: `/v1/accounts`)
- Resource IDs in path parameters
- Filters in query parameters

---

## 📚 Related Documentation

- **API_ENDPOINTS.md** - Detailed API endpoint reference
- **CODEBASE_OVERVIEW.md** - Technical implementation details
- **PROJECT_SUMMARY.md** - High-level overview

---

**Last Updated:** November 10, 2025  
**Version:** 1.0  
**Status:** Development
