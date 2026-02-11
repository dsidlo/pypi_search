# pypi-search-caching (pypi_search command)

 - Current Version: v0.0.3-Beta

Search PyPI package names by regex pattern 🐍📦

Fast, cached regex search over all PyPI packages (~736k+), with optional details (version, maintainer, description).

![Screenshot from 2026-02-08 15-44-00.png](docs/images/Screenshot%20from%202026-02-08%2015-44-00.png){width=100}

## Features

- Regex matching (e.g., `^aio.*`, `flask|django`).
- Access to pypi.org packages via the simple package API
  - 23h cache (`~/.cache/pip-search/`)
- Color output to console

## Program Options
```bash
❯ uv run python src/pypi_search.py -h
usage: pypi_search.py [-h] [--version] [-i] [--desc] [--count-only] [--refresh-cache] [--full-desc] pattern

Search PyPI packages by regex

positional arguments:
  pattern              Regular expression to match package names

options:
  -h, --help           show this help message and exit
  --version, -V        show program`s version number and exit
  -i, --ignore-case    Case-insensitive matching (default: on)
  --desc, -d           Fetch and show detailed info for first 10 matches
  --count-only         Only show count of matches
  --refresh-cache, -r  Refresh the PyPi cache now. Happens before search.
  --full-desc, -f      Include full description in details (with -d)
```

## Installation

```bash
# Standard pip install
pip install pypi-search-caching

# uv environment install
uv pip install pypi-search-caching
```

- Installs pypi_search to ~/.local/bin

## Usage

`pypi_search "pattern"`

`pypi_search --version`

Details for first 10: `pypi_search "flask|django" --desc`

Count only: `pypi_search "pattern" --count-only`

```shell
pypi_search "^aio" -d 
```

## Examples

Input argument is anchored between '^' start of line and '$' end of line. So if there are not regular expression character, it searches for a specific module...
```shell
✦ ❯ ./pypi_search aiohttp 
Using cached package list (age < 23h)
Found 1 matching packages:

aiohttp

Total matches: 1
````

Search for a module that begins with...
```shell
✦ ❯ pypi_search "^aio" | less

Found 2,159 matching packages:

AIO-CodeCheck
AIOAladdinConnect
AIOConductor
AIOPayeerAPI
AIOPools
...
aiozmq-heartbeat
aiozoneinfo
aiozoom
aiozyre

Total matches: 2,159
```


Search for a string in the middle of a package name:
```shell
 ❯ ./pypi_search '.*aio.*'  | less
Found 3,094 matching packages:

AIO-CodeCheck
AIOAladdinConnect
AIOConductor
AIOPayeerAPI
AIOPools
...
traio
trakt_aiohttp
transitions-aio
trio-aiohttp
twm-aiokafka
txaio
txaioetcd
types-aioboto3
types-aioboto3-lite
types-aiob[lib](.venv/lib)otocore
...
xmaios-bot
ya-aioclient
yandex-aiobot-py
yclients-aio-client
youtubeaio
youtubeaio-extended
z21aio

Total matches: 3,094
```

Search for a module that ends with...
```shell
✦ ❯ ./pypi_search '.*http$'  | less

Found 413 matching packages:

BasicHttp 
CANedge-HTTP 
CodernityDB-HTTP 
CydraGitHTTP 
Flask-Shell2HTTP 
...
zerohttp 
zhttp 
zhujiaying-boss-mcp-weather-http 
zimran-http 
zipr-http 
zope.app.http 

Total matches: 413
```

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

