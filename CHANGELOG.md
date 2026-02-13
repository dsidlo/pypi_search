# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- tqdm progress bars to main() loops for --search/--desc (with disable=isatty).
- --test_mode argparse flag for logger fallback in tests.
- TestTestModeAndProgress class (7 tests) and `@pytest.mark.refresh_cache` to 3 tests.
- docs/notes/pypi_search_running-tests.md with test run guides.

### Changed
- Updated pyproject.toml: Added tqdm dep, pytest addopts="-m 'not refresh_cache'", markers.
- Bumped version to 0.0.5a2.

## [0.0.5a1] - 2023-10-01
### Added
- Initial LMDB caching.

## [v0.0.4b1] - 2026-02-08
### Added
- Basic regex search
- Legacy file cache (~23h TTL)
- Rich output
- argparse for --desc/-d
- --count-only
- --refresh-cache/-r

## [v0.0.3b1] - 2026-01-15
### Added
- Initial PyPI simple API fetch
- Package name list

## [v0.0.1a1] - 2025-12-01
### Added
- Core structure
- main() CLI skeleton