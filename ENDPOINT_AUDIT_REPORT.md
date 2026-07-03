# API Endpoint Audit Report

## Summary
Comprehensive audit of all API endpoints vs. HTML/Web Client calls to identify data format mismatches and missing endpoints.

---

## Critical Issues (High Priority)

### 1. ❌ Missing Endpoint: `/sms-activity-permission`
**Status:** MISSING - Endpoint does not exist  
**Called by:** 
- `website/activity-list.html` (line 283)
- `website/__activity-request.html` (line 219)

**Current Implementation:**
```javascript
// activity-list.html line 283
const res = await fetch(API_BASE_URL + '/sms-activity-permission', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ activity_id: id })
});

// __activity-request.html line 219
const res = await fetch(API_BASE_URL + '/sms-activity-permission', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({activity_id: activityId})
});
```

**Required Fix:**
- Create POST `/sms-activity-permission` endpoint
- Accept: `{activity_id: str}`
- Functionality: Send SMS to parents/guardians for activity permission

**Impact:** Activity permission SMS notifications will not work

---

### 2. ⚠️ URL Path Mismatch: `/activity/{id}` vs `/activities/{activity_id}`
**Status:** INCONSISTENT  
**Called by:**
- `website/activity-list.html` (lines 251, 270)

**Current Implementation:**
```javascript
// PUT request - line 251
const res = await fetch(`${API_BASE_URL}/activity/${id}`, {
  method: "PUT",
  headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
  body: JSON.stringify(payload)
});

// DELETE request - line 270
const res = await fetch(`${API_BASE_URL}/activity/${id}`, {
  method: "DELETE",
  headers: { Authorization: `Bearer ${token}` }
});
```

**API Implementation:**
- `/activities/{activity_id}` (PUT - line 684)
- `/activities/{activity_id}` (DELETE - line 674)

**Required Fix:**
- Update HTML to use `/activities/{id}` instead of `/activity/{id}`
- Both GET, PUT, DELETE should use `/activities/{activity_id}` pattern

**Impact:** Activity updates and deletions will fail with 404 errors

---

### 3. ⚠️ GET `/group-concerns` Missing Group Parameter
**Status:** PARAMETER MISMATCH  
**Called by:** `website/group-admin.html` (line 650)

**Current Implementation:**
```javascript
// group-admin.html line 650
const response = await fetch(`${API_BASE_URL}/group-concerns`, {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

**API Implementation:**
- GET `/group-concerns/{group}` (line 561) - expects `group` path parameter

**Required Fix:**
- Option A: Update HTML to pass group in URL: `/group-concerns/{currentUserGroup}`
- Option B: Modify API to accept query parameter: `/group-concerns?group={group}`
- Recommendation: Option A (consistent with existing pattern)

**Impact:** Cannot load group concerns, will return 404 error

---

### 4. ⚠️ GET `/interest-survey` Missing Group Parameter
**Status:** PARAMETER MISMATCH  
**Called by:** `website/group-admin.html` (line 585)

**Current Implementation:**
```javascript
// group-admin.html line 585
const response = await fetch(`${API_BASE_URL}/interest-survey`, {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

**API Implementation:**
- GET `/interest-survey/{group}` (line 553) - expects `group` path parameter

**Required Fix:**
- Update HTML to pass group in URL: `/interest-survey/{currentUserGroup}`

**Impact:** Cannot load interest survey results, will return 404 error

---

### 5. ⚠️ POST `/group-concerns` Data Format Mismatch
**Status:** REQUEST BODY MISMATCH  
**Called by:** `website/group-admin.html` (line 736)

**Current Implementation:**
```javascript
// group-admin.html line 736
body: JSON.stringify({
  concern: concern,           // singular string
  group: currentUserGroup
})
```

**API Implementation (schema.py line ~100):**
```python
class ConcernSurvey(BaseModel):
    concerns: List[str]        # plural array
    org_group: str
```

**Required Fix:**
- Option A: Update HTML to match schema:
  ```javascript
  body: JSON.stringify({
    concerns: [concern],       // wrap in array
    org_group: currentUserGroup
  })
  ```
- Option B: Create new schema to accept singular concern
- Recommendation: Option A (use existing schema)

**Impact:** Concern submission will fail with 422 validation error

---

## Verified Endpoints (No Issues)

✅ **POST `/login`** - Fixed in this session (now accepts JSON body)
✅ **POST `/user-activities`** - Created in this session
✅ **POST `/interest-survey-reset`** - Fixed in this session (now accepts username)
✅ **POST `/interest-survey`** - Works correctly with schema
✅ **POST `/group-concerns`** - Exists, needs data format fix (see #5)
✅ **GET `/interest-survey/{group}`** - Exists, needs group parameter (see #4)
✅ **GET `/group-concerns/{group}`** - Exists, needs group parameter (see #3)
✅ **POST `/activities`** - Works correctly
✅ **GET `/activities/{activity_id}`** - Works correctly
✅ **PUT `/activities/{activity_id}`** - Works correctly (but HTML calls wrong URL - see #2)
✅ **DELETE `/activities/{activity_id}`** - Works correctly (but HTML calls wrong URL - see #2)
✅ **POST `/activity-permissions`** - Exists
✅ **GET `/activities-all`** - Works correctly
✅ **GET `/activities-pending-approval`** - Works correctly
✅ **GET `/activity-groups`** - Works correctly
✅ **GET `/activity-permission-ecclesiastical`** - Works correctly
✅ **GET `/activity-qrcode`** - Works correctly
✅ **POST `/goals`** - Works correctly
✅ **GET `/goals/{youth_id}`** - Works correctly
✅ **PUT `/goals/{youth_id}/{goal_name}`** - Works correctly

---

## Fix Priority Order

**Priority 1 (Critical - Breaks Functionality):**
1. Create `/sms-activity-permission` endpoint
2. Fix `/activity/{id}` → `/activities/{activity_id}` in activity-list.html
3. Fix GET `/group-concerns` to include group parameter

**Priority 2 (High - Data Format Issues):**
4. Fix GET `/interest-survey` to include group parameter
5. Fix POST `/group-concerns` data format

---

## Implementation Checklist

- [ ] Create `/sms-activity-permission` endpoint in api_base/main.py
- [ ] Update activity-list.html lines 251, 270 to use `/activities/{id}`
- [ ] Update group-admin.html line 650 to use `/group-concerns/{currentUserGroup}`
- [ ] Update group-admin.html line 585 to use `/interest-survey/{currentUserGroup}`
- [ ] Update group-admin.html line 736 POST body to use `concerns` array and `org_group`
- [ ] Test all affected endpoints

