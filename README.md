# pypi-search-caching
## Adds the command: pypi_search

 - Current Version: v0.0.4b1

Search PyPI package names by regex pattern 🐍📦

Fast, cached regex search over all PyPI packages (~736k+), with optional details (version, maintainer, description).

![Screenshot from 2026-02-08 15-44-00.png](docs/images/Screenshot%20from%202026-02-08%2015-44-00.png){width=100}

## Features

- Regex matching (e.g., `^aio.*`, `flask|django`).
- Access to pypi.org packages via the simple package API
  - ~23h TTL for package names (`~/.cache/pypi_search/`)
  - 7d LMDB caching for details
- Color output to console

LMDB caching for details, tqdm progress, test_mode for CI.

## Program Options
```bash
usage: pypi_search [-h] [--version] [-i] [-d] [--count-only] [-r] [-f] [--test_mode] pattern

positional arguments:
  pattern               Regular expression to match package names (required)

options:
  -h, --help            show this help message and exit
  --version, -V         show program's version number and exit
  -i, --ignore-case     Case-insensitive matching
  --desc, -d            Fetch and show detailed info for first 10 matches
  --count-only          Only show count of matches
  --refresh-cache, -r   Refresh the PyPI cache now. Happens before search.
  --full-desc, -f       Include full description in details (with -d)
  --test_mode           Use logger.info for progress instead of tqdm bars (for non-interactive/tests)
```

## Installation

```bash
# Using pip
pip install pypi-search-caching

# Using uv
uv pip install pypi-search-caching
```

- Installs `pypi_search` command to `~/.local/bin` (pip) or your virtual environment's bin (uv).

## Usage Examples

### Basic search
```shell
pypi_search "^aio"
```
Searches for packages starting with "aio" using cached names.

### With details
```shell
pypi_search "flask|django" -d
```
Shows details (version, homepage, etc.) for the first 10 matches.

### Refresh cache
```shell
pypi_search "pattern" -r
```
Refreshes the package names cache before searching.

### Test mode
```shell
pypi_search "^aio" --test_mode
```
Uses logging for progress instead of tqdm bars, useful for CI or non-interactive environments (shows logs).

Progress bars (tqdm) appear during long fetches like details or filtering; caching (~23h TTL for names, 7d for details via LMDB). Use `--test_mode` for non-interactive/tests.

### Filter by description
```shell
pypi_search "aio" --search "async" --count-only
```
Counts packages matching "aio" whose long descriptions contain "async".

### Searching Descriptions (Torch Example)

```bash
pypi_search '^torch.*' -s 'image'
```
Searches for torch packages and filters descriptions containing 'image'. Caches long descriptions for subsequent faster searches.

```bash
pypi_search '^torch.*' -s 'image' -d -f'
```
Subsequently, display summary and full long description (from cache) for matching modules.

## My Dev Environment: 

  - **Python Env:** uv
  - **IDE:** JetBrains PyCharm
  - **AI Agent Env:** 
    - Aider
    - Aider-Desk
    - Junie

## Feedback

  - Let me know what you think.
    Please post bug, suggestions, and wins from using pypi_search. I'd really appreciate it.
  - Links
    - [Report Bugs](https://github.com/dsidlo/pypi_search/issues)
    - [Announcements](https://github.com/dsidlo/pypi_search/discussions/categories/announcements)
    - [Feedback](https://github.com/dsidlo/pypi_search/discussions/)

## Licence

MIT License. Built with Requests + BeautifulSoup.