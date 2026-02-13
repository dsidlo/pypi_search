# PyPI Search: Running Tests

## Overview

This document outlines how to run tests for the `pypi_search_caching` project. The tests are implemented using `pytest` and cover various aspects of the functionality, including the main script execution, LMDB cache management, and other utilities.

## Prerequisites

Before running the tests, ensure you have the following installed:

- Python 3.8 or higher
- `pytest` (install via `pip install pytest`)
- `pytest-mock` (for mocking, install via `pip install pytest-mock`)
- `requests` (for HTTP-related tests, if any)
- `lmdb` (for database-related tests)
- `rich` (for console output handling in tests)

You can install all dependencies by running:

```bash
pip install -e .[test]
```

Assuming a `pyproject.toml` or `setup.py` with test extras.

## Running Tests

### Basic Test Run

To run all tests in the project:

```bash
pytest
```

This will discover and run all tests in the `src/test/` directory (or wherever tests are located, typically `tests/` or `test/`).

### Running Specific Test Files

To run tests from a specific file, e.g., `test_pypi_search.py`:

```bash
pytest src/test/test_pypi_search.py
```

### Running Specific Test Classes or Functions

- To run tests in a specific class, e.g., `TestMain`:

```bash
pytest src/test/test_pypi_search.py::TestMain
```

- To run a specific test method, e.g., `test_invalid_regex`:

```bash
pytest src/test/test_pypi_search.py::TestMain::test_invalid_regex
```

### Verbose Output

For more detailed output, including captured stdout/stderr:

```bash
pytest -v -s
```

- `-v`: Verbose mode, shows test names and results.
- `-s`: Do not capture print statements (useful for seeing console output in tests).

### Capturing Logs

Some tests may use logging. To see log output:

```bash
pytest -v -s --log-cli-level=INFO
```

### Coverage

To run tests with coverage reporting (requires `pytest-cov`):

```bash
pip install pytest-cov
pytest --cov=src/pypi_search_caching --cov-report=html
```

This generates an HTML report in `htmlcov/` directory.

### Test Markers

Some tests are marked with `@pytest.mark.refresh_cache` to indicate they perform cache refresh operations, which may involve network requests and take longer to execute.

By default (due to pyproject.toml addopts), pytest skips refresh_cache-marked tests, so standard runs (e.g., pytest src/test/) do not execute cache refresh logic (89 tests pass quickly).

#### Running Only Cache Refresh Tests

To run only the cache refresh tests:

```bash
pytest src/test/ -m refresh_cache
```

This runs the 3 marked tests.

#### Running All Tests

To run all tests:

```bash
pytest src/test/ -m "refresh_cache or not refresh_cache"
```

#### Default Run (Skips Refresh Cache Tests)

For the standard quick run (no additional flags needed due to pyproject.toml):

```bash
pytest src/test/
```

This executes the 89 non-refresh_cache tests quickly, skipping cache refresh logic.

## Test Structure

### TestMain Class

This class tests the `main()` function from `pypi_search_caching.py`.

- **test_invalid_regex**: Tests handling of invalid regex patterns in command-line arguments. Mocks `get_packages` and `sys.exit`. Expects the program to exit with code 2 on invalid regex.

- **test_version_flag**: Parametrized test for `--version` and `-V` flags. Mocks `sys.argv` and captures stdout to verify version output.

### TestLMDBCache Class

This class focuses on LMDB cache operations.

- **mock_home fixture**: Sets up a temporary cache directory using `tmp_path` and monkeypatches `pathlib.Path.home` to point to it.

- **test_store_package_data_exception**: Tests exception handling in `store_package_data`. Mocks LMDB transaction to raise exceptions and verifies error logging.

- **test_store_package_data_lmdb_warning**: Tests warning scenarios in `store_package_data` when LMDB put operation returns a warning. Uses `caplog` to capture and assert log messages.

## Mocking in Tests

Tests heavily use `pytest`'s `@patch` decorator and `monkeypatch` for mocking:

- Patching external calls like `sys.exit`, `sys.argv`, and module functions.
- Mocking LMDB transactions with custom `MockTxn` classes to simulate success, exceptions, and warnings.
- Using `capsys` fixture to capture and assert stdout/stderr.

Example from `test_invalid_regex`:

```python
@patch('src.pypi_search_caching.pypi_search_caching.get_packages')
@patch('sys.exit')
def test_invalid_regex(self, mock_exit, mock_get_packages, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['script', r'['])  # invalid regex
    main()
    mock_exit.assert_called_once_with(2)
```

## Troubleshooting

- **LMDB Issues**: If tests fail due to LMDB permissions, ensure the temporary directory has write permissions. The `mock_home` fixture handles this with `tmp_path`.

- **Import Errors**: Make sure to run tests from the project root and that `src/` is in `PYTHONPATH` or use editable install (`pip install -e .`).

- **ANSI Stripping**: Some tests use `strip_ansi` utility to clean console output for assertions. This is defined in `src/test/test_pypi_search.py`.

For more details on individual tests, refer to the source code in `src/test/test_pypi_search.py`.

## Additional Notes

### Internet Access in Tests

While most tests use mocks for external dependencies like HTTP requests and do not require internet access, cache refresh tests (marked with `@pytest.mark.refresh_cache`) may access the PyPI API via `requests.get(PYPI_SIMPLE_URL)` in `fetch_all_package_names()` if not fully mocked. This behavior simulates real cache refresh operations.

**Recommendations:**
1. For offline runs, use `pytest -m "not refresh_cache"` to skip these tests.
2. In CI environments, set the environment variable `PYPI_OFFLINE=true` to patch requests (consider adding this patching logic to the code if not already present).
3. Review the marked tests for complete mocks where necessary (e.g., patch `'requests.get'` in `test_cache_invalid_refresh`).

**Affected Tests:**
- `TestGetPackages.test_cache_invalid_refresh`
- `TestFetch100PackageNames.test_limited_fetch`
- `TestMain.test_main_early_return_refresh_empty_pattern`

- Run tests in a virtual environment to avoid conflicts.
- If adding new tests, follow the pattern: use fixtures for setup, patch external dependencies, and assert on expected behaviors/logs/exits.
