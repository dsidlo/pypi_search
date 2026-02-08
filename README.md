# pip-search

Search PyPI package names by regex pattern 🐍📦

Fast, cached regex search over all PyPI packages (~500k+), with optional details (version, maintainer, description).

## Features
- Regex matching (e.g., `^aio.*`, `flask|django`).
- 23h cache (`~/.cache/pip-search/`).
- Optional details for top 10 matches (`-d`).
- Count-only mode.

## Installation

## Usage

`pip-search "pattern"`

Details for first 10 pip-search "flask|django" --desc pip-search "pattern" --count-only
```shell
pip-search "^aio" -d 
```

## Examples

Input argument is anchored between '^' start of line and '$' end of line. So if there are not regular expression character, it searches for a specific module...
```shell
✦ ❯ ./pip-search aiohttp 
Using cached package list (age < 23h)
Found 1 matching packages:

aiohttp

Total matches: 1
````

Search for a module that begins with...
```shell
✦ ❯ pip-search "^aio" | less

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
 ❯ ./pip-search '.*aio.*'  | less
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
✦ ❯ ./pip-search '.*http$'  | less

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

## Licence

MIT License. Built with Requests + BeautifulSoup.

