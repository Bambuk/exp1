# Testing Strategy

## Overview

This document describes the testing strategy for the Radiator project, with lessons learned from the testing returns feature implementation.

## Testing Pyramid

### 1. Unit Tests (Bottom Layer)
**Purpose**: Test individual functions and methods in isolation

**When to use**:
- Testing pure logic without external dependencies
- Testing calculations and transformations
- Testing edge cases and error handling

**Example**: `test_testing_returns_calculation.py`
- Tests `count_status_returns` method with various history patterns
- Uses mocks for dependencies
- Fast execution (<1ms per test)

**Best Practices**:
- ✅ Use mocks for external dependencies
- ✅ Test edge cases (empty input, None values, malformed data)
- ✅ Keep tests simple and focused on one aspect
- ❌ Don't mock the code under test
- ❌ Don't test implementation details

### 2. Integration Tests (Middle Layer)
**Purpose**: Test interactions between components with real dependencies

**When to use**:
- Testing database queries
- Testing service interactions
- Testing data transformations with real data structures

**Example**: `test_testing_returns_e2e.py`
- Tests with real database (PostgreSQL)
- Tests with real SQLAlchemy models
- Tests actual data flows

**Best Practices**:
- ✅ Use **real database** (test DB, not mocks)
- ✅ Use **real data structures** matching production
- ✅ Test with realistic data scenarios
- ✅ Clean up after each test (rollback transactions)
- ❌ Don't mock database interactions
- ❌ Don't use "perfect" test data that doesn't match reality

### 3. Performance Tests (Special Layer)
**Purpose**: Ensure acceptable performance characteristics

**When to use**:
- Testing query performance
- Testing N+1 query problems
- Testing bulk operations

**Example**: `test_get_task_hierarchy_performance.py`
- Uses `QueryCounter` to track database queries
- Tests with large datasets (100+ records)
- Asserts on query count limits

**Best Practices**:
- ✅ Test with realistic data volumes
- ✅ Count database queries
- ✅ Set reasonable thresholds
- ✅ Test worst-case scenarios
- ❌ Don't test with trivial datasets

### 4. End-to-End Tests (Top Layer)
**Purpose**: Test complete user flows from start to finish

**When to use**:
- Testing full workflows
- Testing command-line interfaces
- Testing report generation

**Best Practices**:
- ✅ Test with real data
- ✅ Test complete flows
- ✅ Verify end results
- ❌ Don't over-use (they're slow)

## Lessons Learned: Testing Returns Feature

### What Went Wrong

#### Problem 1: Excessive Mocking
**Symptom**: Tests passed, but production code failed

**Root Cause**: Unit tests used mocks that didn't match real data structure
```python
# Test used this structure (WRONG):
mock_subtask.links = [{
    "type": {"id": "subtask"},
    "direction": "inward",
    "object": {"key": "FULLSTACK-123"},
    "queue": {"key": "FULLSTACK"}  # ❌ This doesn't exist in real DB!
}]

# Real DB has this structure:
task.links = [{
    "type": {"id": "subtask"},
    "direction": "inward",
    "object": {"key": "FULLSTACK-123"}
    # ❌ NO "queue" field!
}]
```

**Solution**: E2E tests with real database revealed the mismatch

#### Problem 2: Missing Performance Tests
**Symptom**: Report generation took 10+ minutes

**Root Cause**: `get_task_hierarchy` made 62,111 database queries

**Why tests didn't catch it**: No performance tests existed

**Solution**: Added performance tests with `QueryCounter`
```python
def test_get_task_hierarchy_does_not_load_all_tasks(self, db_session):
    # Create 11 tasks in hierarchy
    # ...

    with QueryCounter(db_session) as counter:
        hierarchy = service.get_task_hierarchy("FULLSTACK-1000")

    # Assert: should be < 50 queries, not 62,111!
    assert counter.query_count < 50
```

#### Problem 3: Missing Integration Tests
**Symptom**: Individual components worked, but integration failed

**Root Cause**: No tests for complete flow: CPO → FULLSTACK → returns → report

**Solution**: Added E2E tests with real database
```python
def test_ttm_report_finds_testing_returns_in_real_data(self, db_session):
    # 1. Create CPO task in test DB
    cpo_task = TrackerTask(key="CPO-999", ...)

    # 2. Create FULLSTACK task with returns
    fullstack_task = TrackerTask(key="FULLSTACK-999", ...)

    # 3. Create history with 2 returns
    history = [...]

    # 4. Verify returns are calculated correctly
    returns, external = service.calculate_testing_returns(...)
    assert returns == 2
```

### What Was Revealed by New Tests

#### Issue 1: Missing `tracker_id` in History
```
IntegrityError: ОШИБКА: значение NULL в столбце "tracker_id"
отношения "tracker_task_history" нарушает ограничение NOT NULL
```

**Why this matters**: Production code requires `tracker_id`, but tests didn't set it

**Fix needed**: Update test fixtures to include `tracker_id`

#### Issue 2: JSON vs JSONB Column Type
```
UndefinedFunction: ОШИБКА: функция jsonb_array_elements(json) не существует
```

**Why this matters**: Optimized SQL queries assume JSONB, but column is JSON

**Fix needed**: Migration to convert `links` from JSON to JSONB (already exists)

#### Issue 3: `get_fullstack_links` Returns Empty List
```
AssertionError: FULLSTACK-111 должен быть найден
assert 'FULLSTACK-111' in []
```

**Why this matters**: Logic for finding linked tasks is broken

**Fix needed**: Review and fix link parsing logic

## Testing Best Practices

### When to Mock vs Real Data

| Scenario | Approach | Reason |
|----------|----------|--------|
| Testing calculation logic | Mock | Fast, isolated |
| Testing database queries | Real DB | Catch schema mismatches |
| Testing API calls | Mock | Don't depend on external services |
| Testing data transformations | Real data structures | Catch format mismatches |
| Testing performance | Real DB | Accurate measurements |

### Fixture Strategy

#### ✅ Good: Realistic Fixtures
```python
@pytest.fixture
def cpo_task_with_fullstack_links(db_session):
    """Create CPO task with realistic link structure."""
    task = TrackerTask(
        tracker_id="cpo-001",
        key="CPO-123",
        links=[{
            "type": {"id": "relates"},
            "object": {"key": "FULLSTACK-456"}
            # Matches REAL API response structure
        }]
    )
    db_session.add(task)
    db_session.commit()
    return task
```

#### ❌ Bad: Mock with Wrong Structure
```python
def test_something():
    mock_task = Mock()
    mock_task.links = [{
        "queue": {"key": "FULLSTACK"},  # ❌ Doesn't exist in real data!
        "object": {"key": "FULLSTACK-456"}
    }]
```

### Performance Test Guidelines

1. **Set Realistic Limits**
   - Don't assert `query_count == 1` (too strict)
   - Do assert `query_count < 100` (reasonable threshold)

2. **Test with Scale**
   - Small dataset: 10-50 records
   - Medium dataset: 100-500 records
   - Large dataset: 1000+ records

3. **Test Worst Case**
   - Deep hierarchies
   - Many relationships
   - Edge cases

### Database Test Guidelines

1. **Use Test Database**
   ```python
   @pytest.fixture(scope="session")
   def test_db_engine():
       engine = create_engine(TEST_DATABASE_URL)
       Base.metadata.create_all(bind=engine)
       yield engine
       Base.metadata.drop_all(bind=engine)
   ```

2. **Rollback After Each Test**
   ```python
   @pytest.fixture
   def db_session(test_db_engine):
       session = SessionLocal()
       try:
           yield session
       finally:
           session.rollback()  # Clean up
           session.close()
   ```

3. **Match Production Schema**
   - Use same column types (JSON vs JSONB)
   - Use same constraints (NOT NULL, UNIQUE)
   - Use same indexes

## Testing Checklist

Before marking a feature complete, ensure:

- [ ] **Unit tests** for core logic
- [ ] **Integration tests** with real database
- [ ] **Performance tests** for database queries
- [ ] **E2E tests** for complete workflows
- [ ] Tests use **realistic data structures**
- [ ] Tests catch **common production errors** (NULL, missing fields, wrong types)
- [ ] Performance tests catch **N+1 query problems**
- [ ] Tests **don't over-mock** (especially database)

## Tools and Utilities

### QueryCounter
Utility for tracking database query count in tests:

```python
class QueryCounter:
    """Count database queries in a context."""

    def __init__(self, db_session):
        self.db_session = db_session
        self.query_count = 0

    def __enter__(self):
        self.original_execute = self.db_session.execute

        def counting_execute(*args, **kwargs):
            self.query_count += 1
            return self.original_execute(*args, **kwargs)

        self.db_session.execute = counting_execute
        return self

    def __exit__(self, *args):
        self.db_session.execute = self.original_execute
```

### Usage Example
```python
def test_performance(db_session):
    with QueryCounter(db_session) as counter:
        # Code under test
        result = service.get_data()

    assert counter.query_count < 10, "Too many queries!"
```

## Conclusion

**Key Takeaway**: The right balance between mocks and real data is critical.

- **Too many mocks** → Tests pass but production fails
- **Too few mocks** → Tests are slow and flaky
- **Just right** → Fast unit tests + thorough integration tests

**The new test strategy revealed**:
1. Missing `tracker_id` in test data
2. JSON vs JSONB column type mismatch
3. Broken link parsing logic
4. Missing performance tests

These are exactly the kind of issues that should be caught by tests!
