# Storage Tests

This directory contains comprehensive tests for the storage system. The tests are organized into several files, each focusing on different aspects of the storage functionality.

## Test Organization

1. **test_storage.py**: Basic functionality tests for the `MemoryStorage` class
   - Environment variable configuration
   - Database initialization
   - File validation
   - Database operations (load, save)
   - Context management

2. **test_contexts.py**: Tests for multiple context handling
   - Working with multiple contexts simultaneously
   - Context isolation
   - Edge cases (special characters, Unicode)
   - Concurrent access simulation

3. **test_error_handling.py**: Tests for error conditions and recovery
   - Handling of corrupted JSON
   - Safety marker validation
   - Permission issues
   - Recovery scenarios
   - Unexpected data types

4. **test_performance.py**: Performance and stress tests
   - Bulk operations with large datasets
   - Operations with many contexts
   - Large text handling
   - Repeated operations

## Running Tests

To run all tests:

```bash
uv run pytest
```

To run a specific test file:

```bash
uv run pytest tests/test_storage.py
```

To run a specific test:

```bash
uv run pytest tests/test_storage.py::TestMemoryStorage::test_initialize_storage
```

## Test Coverage

These tests cover:
- All public methods of the `MemoryStorage` class
- Error handling and edge cases
- Performance characteristics
- Different types of data and contexts

The test suite uses temporary directories for testing to avoid interfering with actual user data.