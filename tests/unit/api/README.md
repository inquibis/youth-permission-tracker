# API Unit Tests

This directory contains comprehensive unit tests for the Youth Permission Tracker API using pytest framework.

## Quick Start
* Install test dependencies
`pip install -r test-requirements.txt`

* Run all tests
`pytest tests/unit/api/ -v`

* Run with coverage report
`pytest tests/unit/api/ --cov=api_base --cov-report=html`

* Run specific test file
`pytest tests/unit/api/test_auth.py -v`

* Run specific test
`pytest tests/unit/api/test_auth.py::TestLoginEndpoint::test_login_success_with_valid_credentials -v`

## Test Structure

```
tests/unit/api/
├── conftest.py              # Pytest configuration and shared fixtures
├── test_auth.py             # Authentication and authorization tests
├── test_users.py            # User management endpoint tests
├── test_activities.py       # Activity CRUD endpoint tests
├── test_admin_query.py      # Admin SQL query endpoint tests
└── test_health.py           # Health checks and general endpoint tests
```

## Test Coverage

### Authentication & Authorization (`test_auth.py`)
- ✅ Login with valid/invalid credentials
- ✅ Token generation and verification
- ✅ JWT token validation
- ✅ Role-based access control
- ✅ Admin user creation
- ✅ Permission checking

### User Management (`test_users.py`)
- ✅ Youth user creation
- ✅ User creation with medical information
- ✅ Duplicate user detection
- ✅ User retrieval and updates
- ✅ User deletion
- ✅ User activity interests submission
- ✅ Input validation and error handling

### Activities (`test_activities.py`)
- ✅ Activity creation, retrieval, update, deletion
- ✅ Activity listing and filtering
- ✅ Participant management
- ✅ Permission assignment
- ✅ Health reports
- ✅ Activity reconciliation
- ✅ Ecclesiastical approvals

### Admin Query Tool (`test_admin_query.py`)
- ✅ SELECT/INSERT/UPDATE/DELETE query execution
- ✅ Query validation and dangerous operation blocking
- ✅ Role-based access control
- ✅ Error handling and reporting
- ✅ Audit logging
- ✅ Query execution metrics

### General Endpoints (`test_health.py`)
- ✅ Health check endpoint
- ✅ Root endpoint
- ✅ CORS header handling
- ✅ HTTP method validation
- ✅ Error response formats
- ✅ Content-type handling

## Installation

1. Install pytest and dependencies:
```bash
pip install pytest pytest-asyncio pytest-cov
```

2. Install the API package dependencies:
```bash
pip install -r api_base/requirements.txt
```

## Running Tests

### Run all tests:
```bash
pytest
```

### Run specific test file:
```bash
pytest tests/unit/api/test_auth.py
```

### Run specific test class:
```bash
pytest tests/unit/api/test_auth.py::TestLoginEndpoint
```

### Run specific test:
```bash
pytest tests/unit/api/test_auth.py::TestLoginEndpoint::test_login_success_with_valid_credentials
```

### Run with verbose output:
```bash
pytest -v
```

### Run with coverage report:
```bash
pytest --cov=api_base --cov-report=html
```
This generates an HTML coverage report in `htmlcov/index.html`

### Run with markers (e.g., only auth tests):
```bash
pytest -m auth
```

### Run only negative tests:
```bash
pytest -k "failure or invalid or missing or error"
```

### Run tests in parallel (requires pytest-xdist):
```bash
pip install pytest-xdist
pytest -n auto
```

### Stop on first failure:
```bash
pytest -x
```

### Show print statements:
```bash
pytest -s
```

### Run with specific log level:
```bash
pytest --log-cli-level=DEBUG
```

## Test Patterns

### Positive Tests (Happy Path)
- Valid input → Expected success response
- Example: `test_login_success_with_valid_credentials`

### Negative Tests (Error Handling)
- Invalid input → Expected error response
- Missing fields → Validation error
- Unauthorized access → Permission error
- Example: `test_login_failure_with_invalid_password`

### Edge Cases
- Empty values
- Null values
- Duplicate entries
- Boundary conditions
- Example: `test_user_creation_with_duplicate_name`

### Security Tests
- Role-based access control
- SQL injection prevention
- Authorization checks
- Example: `test_admin_query_blocks_drop_statement`

## Fixtures

The `conftest.py` provides shared fixtures:

- `client` - FastAPI test client
- `test_db` - In-memory SQLite database
- `auth_token` - Valid JWT token for testing
- `test_admin_user` - Pre-created admin user
- `test_youth_user` - Pre-created youth user
- `test_activity` - Pre-created activity

## Test Database

Tests use an in-memory SQLite database that:
- Is created fresh for each test session
- Includes all required tables (admin_users, activities, youth_medical, etc.)
- Is isolated and doesn't affect production data
- Provides consistent test environment

## Markers

Tests can be categorized using markers:

```python
@pytest.mark.auth
def test_login_success():
    pass

@pytest.mark.security
def test_sql_injection_prevention():
    pass
```

Run specific marker groups:
```bash
pytest -m auth              # Only auth tests
pytest -m "not slow"        # Skip slow tests
pytest -m "auth and security"  # Multiple conditions
```

## Debugging Tests

### Print debug information:
```bash
pytest -s  # Show print statements
pytest -vv # Very verbose
```

### Drop into debugger on failure:
```bash
pytest --pdb  # Drop into pdb on failures
```

### Run with detailed traceback:
```bash
pytest --tb=long
```

### Show local variables in traceback:
```bash
pytest -l
```

## Continuous Integration

To run tests in CI/CD pipeline:

```bash
pytest \
  --cov=api_base \
  --cov-report=xml \
  --cov-report=term \
  --junit-xml=test-results.xml \
  -v
```

## Best Practices

1. **Test Isolation**: Each test is independent and doesn't rely on others
2. **Descriptive Names**: Test names clearly describe what is being tested
3. **Single Assertion**: Each test focuses on one behavior
4. **Fixtures**: Use fixtures for common setup (database, auth tokens)
5. **Mocking**: Mock external dependencies (email, SMS, external APIs)
6. **Error Messages**: Use descriptive assertion error messages
7. **Performance**: Keep tests fast; use in-memory database
8. **Coverage**: Aim for >80% code coverage

## Troubleshooting

### Tests fail with database errors
- Clear database: `rm -f tests/unit/api/test.db`
- Check conftest.py database creation

### Import errors
- Add api_base to PYTHONPATH: `export PYTHONPATH="${PYTHONPATH}:$(pwd)/api_base"`
- Or run from project root: `cd youth-permission-tracker && pytest`

### Authentication fails
- Check that `SECRET_KEY` environment variable is set
- Verify JWT token creation in conftest.py fixtures

### Tests timeout
- Increase timeout in pytest.ini
- Check for infinite loops in code
- Use `pytest --durations=10` to find slow tests

## Adding New Tests

1. Create test file: `tests/unit/api/test_feature.py`
2. Import fixtures from conftest.py
3. Use `Test` prefix for classes, `test_` prefix for functions
4. Write both positive and negative test cases
5. Use descriptive names and docstrings
6. Add markers for categorization

Example:
```python
import pytest

class TestNewFeature:
    """Tests for new feature endpoint"""
    
    def test_feature_success(self, client):
        """Test successful feature operation"""
        response = client.get("/feature")
        assert response.status_code == 200
    
    def test_feature_invalid_input(self, client):
        """Test feature fails with invalid input"""
        response = client.post("/feature", json={})
        assert response.status_code == 422
```

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLite in Python](https://docs.python.org/3/library/sqlite3.html)
- [JWT testing patterns](https://python-jose.readthedocs.io/)
