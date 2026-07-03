# Unit Test Fix Status & Known Issues

## ✅ Fixed

1. **Dependency Injection Mocking** (conftest.py)
   - Fixed `app.dependency_overrides` to properly override `DB.get_db` method
   - Tests now connect to in-memory SQLite test database
   - Database tables are being created in test fixtures

2. **pytest.ini Configuration**
   - Removed invalid `--html` and `--self-contained-html` options
   - Fixed `--cov=api` to `--cov=api_base`

3. **API Code Issues**
   - Fixed login endpoint tuple/dict access errors
   - Fixed /token endpoint to use correct column names

## ⚠️ Remaining Issues

### Critical - Blocking Test Execution

**Issue 1: audit_log_event() function signature change**
- **Location**: api_base/main.py (lines 136-182)
- **Problem**: Changed `db = Depends(DB.get_db)` to require explicit `db` parameter
- **Impact**: All 12 calls to `audit_log_event()` throughout the codebase need to pass `db` parameter
- **Fix**: Update all calls to include `db=db` parameter
- **Calls to update** (lines 238, 256, 273, 313, 507, 1075, 1102, 1169, 1189, 1214, 1410)

### Medium - Test Expectations Need Adjustment

**Issue 2: Test fixtures using plaintext passwords**
- **Problem**: test_admin_user fixture stores plaintext "password123", but API expects hashed passwords
- **Solution**: Use bcrypt-hashed password: `$2b$12$Xvez11kLy9DXaKTWGrp2k.3zKYRDfNLzFN.eHwf1Jva7nS6KQqePW`
- **Status**: Already updated in conftest.py

## Quick Fix Checklist

- [ ] Update all `audit_log_event()` calls to pass `db=db` parameter
- [ ] Verify password hashing in test fixtures matches API expectations
- [ ] Run auth tests: `pytest tests/unit/api/test_auth.py -v`
- [ ] Run health tests: `pytest tests/unit/api/test_health.py -v`
- [ ] Run all tests: `pytest tests/unit/api/ -v`

## Test Execution Example

```bash
# After fixing audit_log_event calls
pytest tests/unit/api/test_auth.py::TestLoginEndpoint::test_login_success_with_valid_credentials -xvs
```

## Notes

- The database mocking is now working correctly
- Tests are now properly isolated with in-memory SQLite
- The main issues are API code integration, not test infrastructure
