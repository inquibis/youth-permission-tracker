# API Unit Tests - Command Examples

## Quick Start

```bash
# Run all tests
pytest tests/unit/api/

# Run with verbose output
pytest tests/unit/api/ -v

# Run with coverage report
pytest tests/unit/api/ --cov=api_base --cov-report=html
```

## Running Specific Test Categories

### Authentication Tests
```bash
pytest tests/unit/api/test_auth.py -v
pytest tests/unit/api/test_auth.py::TestLoginEndpoint -v
```

### User Management Tests
```bash
pytest tests/unit/api/test_users.py -v
pytest tests/unit/api/test_users.py::TestYouthUserCreation -v
```

### Admin Query Tests
```bash
pytest tests/unit/api/test_admin_query.py -v
pytest tests/unit/api/test_admin_query.py::TestAdminQueryEndpoint -v
```

### Activity Tests
```bash
pytest tests/unit/api/test_activities.py -v
```

### Health & General Tests
```bash
pytest tests/unit/api/test_health.py -v
```

## Running Individual Tests

### Login Tests
```bash
# Test successful login
pytest tests/unit/api/test_auth.py::TestLoginEndpoint::test_login_success_with_valid_credentials -v

# Test login with invalid password
pytest tests/unit/api/test_auth.py::TestLoginEndpoint::test_login_failure_with_invalid_password -v

# Test login with missing username
pytest tests/unit/api/test_auth.py::TestLoginEndpoint::test_login_failure_with_missing_username -v
```

### Youth User Creation Tests
```bash
# Test successful creation
pytest tests/unit/api/test_users.py::TestYouthUserCreation::test_youth_creation_success -v

# Test duplicate user detection
pytest tests/unit/api/test_users.py::TestYouthUserCreation::test_youth_creation_with_duplicate_name -v

# Test missing fields
pytest tests/unit/api/test_users.py::TestYouthUserCreation::test_youth_creation_with_missing_first_name -v
```

### Admin Query Tests
```bash
# Test SELECT query
pytest tests/unit/api/test_admin_query.py::TestAdminQueryEndpoint::test_admin_query_select_success -v

# Test blocked DROP statement
pytest tests/unit/api/test_admin_query.py::TestAdminQueryEndpoint::test_admin_query_blocks_drop_statement -v

# Test SQL injection prevention
pytest tests/unit/api/test_admin_query.py::TestAdminQueryEndpoint::test_admin_query_blocks_truncate_statement -v

# Test requires authentication
pytest tests/unit/api/test_admin_query.py::TestAdminQueryEndpoint::test_admin_query_without_auth_token -v
```

## Filtering & Pattern Matching

### Run only passing tests
```bash
pytest tests/unit/api/ -v --co -q
```

### Run tests containing specific keyword
```bash
pytest tests/unit/api/ -k "login" -v
pytest tests/unit/api/ -k "creation" -v
pytest tests/unit/api/ -k "deletion" -v
```

### Run tests matching pattern
```bash
# All success tests
pytest tests/unit/api/ -k "success" -v

# All failure tests
pytest tests/unit/api/ -k "failure or invalid or error" -v
```

## Debugging

### Show print statements
```bash
pytest tests/unit/api/ -s -v
```

### Show extra verbose output
```bash
pytest tests/unit/api/ -vv
```

### Drop into debugger on failure
```bash
pytest tests/unit/api/ --pdb
```

### Show local variables on failure
```bash
pytest tests/unit/api/ -l
```

### Show slowest tests
```bash
pytest tests/unit/api/ --durations=10
```

## Coverage Reports

### Generate HTML coverage report
```bash
pytest tests/unit/api/ --cov=api_base --cov-report=html
# Open htmlcov/index.html in browser
```

### Show coverage in terminal with missing lines
```bash
pytest tests/unit/api/ --cov=api_base --cov-report=term-missing
```

### Coverage for specific module
```bash
pytest tests/unit/api/ --cov=api_base.main --cov-report=term-missing
```

## Continuous Integration

### Run tests with JUnit XML output
```bash
pytest tests/unit/api/ --junit-xml=test-results.xml
```

### Run tests with coverage XML (for code coverage tools)
```bash
pytest tests/unit/api/ --cov=api_base --cov-report=xml
```

### Combine multiple reports
```bash
pytest tests/unit/api/ \
  --cov=api_base \
  --cov-report=html \
  --cov-report=xml \
  --junit-xml=test-results.xml \
  -v
```

## Parallel Execution

### Run tests in parallel (requires pytest-xdist)
```bash
pip install pytest-xdist
pytest tests/unit/api/ -n auto
```

### Run with specific number of workers
```bash
pytest tests/unit/api/ -n 4
```

## Test Organization

### Run only auth tests
```bash
pytest tests/unit/api/test_auth.py
```

### Run only user tests
```bash
pytest tests/unit/api/test_users.py
```

### Run only admin query tests
```bash
pytest tests/unit/api/test_admin_query.py
```

### Run only activity tests
```bash
pytest tests/unit/api/test_activities.py
```

### Run only health/general tests
```bash
pytest tests/unit/api/test_health.py
```

## Performance Testing

### Run fastest tests first
```bash
pytest tests/unit/api/ --fastest
```

### Skip slow tests
```bash
pytest tests/unit/api/ -m "not slow"
```

### Show test execution times
```bash
pytest tests/unit/api/ --durations=0
```

## Stopping & Continuation

### Stop on first failure
```bash
pytest tests/unit/api/ -x
```

### Stop after N failures
```bash
pytest tests/unit/api/ --maxfail=3
```

### Continue from last failed
```bash
pytest tests/unit/api/ --lf
```

### Run only failed tests
```bash
pytest tests/unit/api/ --ff
```

## Markers

### Run tests by marker
```bash
pytest tests/unit/api/ -m auth
pytest tests/unit/api/ -m security
pytest tests/unit/api/ -m "not slow"
```

### List available markers
```bash
pytest tests/unit/api/ --markers
```

## Real-World Scenarios

### Run all tests before committing
```bash
pytest tests/unit/api/ -v --tb=short
```

### Quick smoke test (fast only)
```bash
pytest tests/unit/api/ -m "not slow" -q
```

### Full test suite with coverage
```bash
pytest tests/unit/api/ \
  -v \
  --cov=api_base \
  --cov-report=html \
  --cov-report=term-missing \
  --tb=short
```

### Generate detailed report for CI
```bash
pytest tests/unit/api/ \
  -v \
  --cov=api_base \
  --cov-report=xml \
  --cov-report=term \
  --junit-xml=test-results.xml \
  --tb=short \
  2>&1 | tee test-output.log
```

### Run tests with timestamps
```bash
pytest tests/unit/api/ -v --tb=short -p no:cacheprovider
```

## Troubleshooting Commands

### Check pytest version
```bash
pytest --version
```

### List all tests without running
```bash
pytest tests/unit/api/ --collect-only
```

### Verify fixtures are available
```bash
pytest tests/unit/api/ --fixtures
```

### Debug configuration
```bash
pytest tests/unit/api/ --setup-show
```

### Clear pytest cache
```bash
pytest tests/unit/api/ --cache-clear
```
