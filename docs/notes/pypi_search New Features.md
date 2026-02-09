# pypi_search New Features

## Console Options
  - `--no-pager | -p`
  - `--no-color | -c`

## Search Option
  - `--fuzzy | -z'
    - Fuzzy Search
  - '--sounds-like | -S'
    - Sounds Like Search (Soundex)
  - '--search-desc | -D'
    - Search Descriptions
    - Possibly limit to 500
  - `--search-full | -F`
    - Search Full Descriptions
    - Limit 100

## Configuration
  - ~/.config/pypi_search/pypi_search.conf
  - Create a term based UI for pypi_search confiuration

## Cache document content
  - Update cache when Hash of documents change
    - Hash of small desc triggers invalidation of full doc
  - Compressed storage

## Browse Mode with Lazy Loading
  - possibly a custom pager
    - should allow for search forward and back
    - change color and term themes
  - UI for easy customization

## Notes, Favorites, and Bookmarks

## Cache Everything
  - Smart Caching of Summaries and Docs
  - Cache json desc and rich-markdown version
    - reduce reprocessing overhead
    - faster

## UI Frontend

# Feature Ideas

## Fuzzy/Soundex Search

### Adding Fuzzy Search and Sounds-Like (Phonetic) Modes to pypi_search

Adding fuzzy search (for approximate/typo-tolerant matching) and sounds-like search (phonetic matching, e.g., Soundex or Metaphone for similar-sounding names) to your `pypi_search` tool is a great idea, especially since regex (the current anchored pattern matching like `^{pattern}$`) can be intimidating for non-technical users. It requires moderate changes to the codebase, focusing on dependencies, argument parsing, matching logic, and tests. The tool's existing structure (caching all ~736k package names in memory via `get_packages()`) makes this efficient, as matching happens in-memory without re-fetching from PyPI.

I'll break it down: **what's involved** (steps and effort), **more user-friendly alternatives to regex**, and **implementation outline**. Effort estimate: 4-6 hours for a developer familiar with Python, including testing. No major refactoring needed, as the core pipeline (cache → match → output details) stays the same.

#### 1. What's Involved (High-Level Overview)
- **Core Changes**: Update `main()` to support new modes via flags (e.g., `--fuzzy`, `--sounds-like`). Replace the regex compilation with conditional matching logic. Precompute phonetic codes if using sounds-like for speed (since the cache is static).
- **Dependencies**: Add 1-2 libraries for fuzzy/phonetic (lightweight, no heavy ML needed).
- **Performance**: With 736k packages, exact regex is fast (~0.1s); fuzzy/phonetic is O(n) but still <2s on modern hardware (test with timeit). Cache is already in place, so no API hits during search.
- **User Experience**: Add CLI flags, update help/usage in argparse. Output remains Rich-formatted (e.g., numbered list, details with `--desc`).
- **Testing**: Extend `TestMain` with new cases (e.g., fuzzy matches typos, sounds-like handles "smyth" → "smith").
- **Edge Cases**: Handle thresholds (e.g., fuzzy >80% similarity), case-insensitivity, empty patterns, sorting results (e.g., by score for fuzzy).
- **Risks**: False positives in fuzzy/phonetic (e.g., too many matches); tune thresholds. No breaking changes if modes are optional (default to regex or substring).
- **Deployment**: Update pyproject.toml, requirements.txt (via uv), README.md examples. Tests ensure no regressions.

#### 2. More Appropriate Alternatives to Regex
Regex is powerful but error-prone for casual users (e.g., escaping special chars like `.` or `|`). Better options prioritize simplicity and usability:

- **Substring Search (Most Recommended Default)**: Matches if the pattern appears anywhere in the package name (case-insensitive). 
  - Why better: Intuitive (e.g., "aio" finds "aiohttp", "requests"). No regex knowledge needed. Fast (string.find()).
  - When to use: As default replacement for regex, or via `--substring`.
  - Example: "flask" matches "flask-sqlalchemy" (partial, not anchored).

- **Prefix/Starts-With Search**: Matches packages starting with the pattern.
  - Why better: Common for package discovery (e.g., "aio" finds "aiohttp" but not "httpaio"). Simple str.startswith().
  - Example: "--prefix aio" for exact starts.

- **Fuzzy Search**: Allows typos/misspellings (e.g., "aoihttp" matches "aiohttp" with 90% similarity).
  - Why better: Forgiving for users typing quickly. Use Levenshtein distance (edits needed to match).
  - Library: rapidfuzz (fast, pure Python; better than fuzzywuzzy).
  - Threshold: Sort by score, show top N (e.g., >80%).

- **Sounds-Like (Phonetic) Search**: Matches by pronunciation (e.g., "colorize" matches "colourise" via Metaphone).
  - Why better: Handles spelling variations in package names (e.g., British/American English). Useful for non-native speakers.
  - Algorithms: Soundex (simple, 4-char code) or Double Metaphone (handles more cases).
  - Library: jellyfish (lightweight, supports multiple phonetics).
  - Limitation: Less accurate for non-English names; combine with substring for best results.

**Recommendation**: Make **substring** the new default (drop anchored regex unless flagged `--regex`). Add `--fuzzy` and `--sounds-like` as opt-in. This makes the tool accessible: 80% of users won't need regex, but experts can still use it. Update README with simple examples like `pipy_search "aio" --fuzzy`.

#### 3. Detailed Implementation Outline
Here's a step-by-step plan to add these modes. I can execute this if you confirm (using tools like file_edit, bash for tests).

##### Step 1: Add Dependencies (pyproject.toml)
- Update [project.dependencies] to include:
  ```
  rapidfuzz>=3.10.0  # For fuzzy (Levenshtein ratio)
  jellyfish>=1.0.0   # For phonetic (Soundex/Metaphone)
  ```
- Run `uv sync` and `uv pip compile pyproject.toml -o requirements.txt` (via release.sh or manually).
- Effort: 5 min. No breaking changes.

##### Step 2: Update CLI (argparse in main())
- In `src/pypi_search.py` (around line 378):
  - Add mutually exclusive group for modes (use argparse.add_mutually_exclusive_group()):
    ```
    search_group = parser.add_mutually_exclusive_group()
    search_group.add_argument("--substring", action="store_true", help="Simple substring search (default)")
    search_group.add_argument("--fuzzy", action="store_true", help="Fuzzy matching for typos (threshold 80%)")
    search_group.add_argument("--sounds-like", action="store_true", help="Phonetic matching (Soundex)")
    search_group.add_argument("--regex", action="store_true", help="Regex search (original anchored mode)")
    search_group.set_defaults(mode="substring")  # Default to substring
    ```
  - Add fuzzy threshold: `parser.add_argument("--fuzzy-threshold", type=int, default=80, help="Fuzzy similarity % (50-100)")`.
- Update help: Include examples in description.
- Effort: 10 min. Tests will need updates for new args.

##### Step 3: Modify Matching Logic (in main(), after get_packages)
- Replace the regex block (lines ~405-410) with conditional:
  ```
  pattern_lower = args.pattern.lower().strip('"\'')
  matches = []
  if args.mode == "substring" or not hasattr(args, 'mode'):  # Default
      matches = [pkg for pkg in all_packages if pattern_lower in pkg.lower()]
  elif args.mode == "regex":
      try:
          flags = re.IGNORECASE if args.ignore_case else 0
          regex = re.compile(f"^{pattern_lower}$", flags)
          matches = [pkg for pkg in all_packages if regex.search(pkg)]
      except re.error as e:
          console.print(f"[red]Invalid regex: {e}[/red]")
          sys.exit(2)
  elif args.mode == "fuzzy":
      from rapidfuzz import fuzz
      for pkg in all_packages:
          score = fuzz.ratio(pkg.lower(), pattern_lower)
          if score >= args.fuzzy_threshold:
              matches.append((pkg, score))  # Tuple for sorting
      matches.sort(key=lambda x: x[1], reverse=True)  # Sort by score
      matches = [m[0] for m in matches]  # Extract names
  elif args.mode == "sounds-like":
      import jellyfish
      pattern_code = jellyfish.soundex(pattern_lower)  # Or metaphone for better accuracy
      matches = [pkg for pkg in all_packages if jellyfish.soundex(pkg.lower()) == pattern_code]
  ```
- For fuzzy, optionally limit to top 1000 by score to avoid overwhelming output.
- Keep case-insensitivity via .lower().
- Effort: 20 min. Precompute phonetic codes once (e.g., cache soundex dict if slow, but jellyfish is fast).

##### Step 4: Update Output and Sorting
- For fuzzy: Print similarity score in results (e.g., "aiohttp (95%)").
  - Modify print loop: `console.print(f"[cyan]{i:>6}.[/] [bold]{pkg}[/bold] ({score}%)" if fuzzy else ... )`
- Sort: Substring/regex: alphabetical; fuzzy: by score descending; sounds-like: alphabetical.
- Effort: 10 min.

##### Step 5: Add/Update Tests (src/test/test_pypi_search.py)
- In TestMain, add 4-6 new tests:
  - `test_substring_matches(mock_get, capsys)`: Assert "aio" finds "aiohttp" but not "httpaio".
  - `test_fuzzy_matches(mock_get, capsys)`: Mock packages with typos; assert high-score matches.
  - `test_sounds_like_matches(mock_get, capsys)`: E.g., "colorize" matches "colourise".
  - `test_invalid_fuzzy_threshold(mock_exit)`: Error if <0 or >100.
  - Update `test_invalid_regex` to only trigger on --regex.
  - Use patch('src.pypi_search.get_packages', return_value=["aiohttp", "httpaio", "smyth-pkg"]).
- Run `cd src/test; uv run pytest ./ -v` to verify.
- Effort: 30-45 min (add ~100 lines; aim for 95%+ coverage).

##### Step 6: Documentation and Polish
- Update README.md: Add sections for new modes with examples (e.g., `pipy_search "aoihttp" --fuzzy` finds "aiohttp").
- Update usage in argparse description.
- Add config (~/.config/pypi_search/config.toml) for defaults (e.g., default_mode="substring", fuzzy_threshold=80) using tomllib.
- Effort: 15 min.

##### Step 7: Build, Test, and Release
- Run `uv sync --dev; cd src/test; uv run pytest ./ --cov=src/pypi_search --cov-report=html -v`.
- Lint with flake8 (via .github/workflows/python-package.yml).
- Build: `uv build` or python -m build; test install `uv pip install -e .`.
- Release: Update version in pyproject.toml, tag, push (triggers .github/workflows/python-publish.yml for PyPI).
- Effort: 20 min.

#### Potential Challenges and Mitigations
- **Performance**: Fuzzy on 736k items: ~1s (rapidfuzz is optimized). Precompute soundex in cache (add to save_packages_to_cache).
- **Accuracy**: Fuzzy threshold too low → too many results; test with real packages (e.g., "numpy" fuzzy finds "numpyy").
- **Dependencies**: rapidfuzz/jellyfish are pure Python, no C extensions; add to dev for tests.
- **Backward Compatibility**: Keep --regex for experts; default to substring to ease migration.
- **Internationalization**: Phonetic works best for English; substring is universal.

This would make pypi_search more accessible (substring for 90% users, fuzzy/phonetic for edge cases). If you'd like a step-by-step execution plan (like the test coverage one), or code snippets for specific parts, let me know!

## Extending Search into Package Metadata

### Extending Search to Fetched Web Data in pypi_search

Extending the search from just package names (current regex/substring/fuzzy on cached ~736k names) to **fetched web data** (e.g., PyPI descriptions, summaries, classifiers, requires_python, or project_urls) is a natural evolution. This would allow queries like "async http client" to find packages like "aiohttp" by searching inside their metadata/descriptions, not just names. It's feasible with the tool's existing architecture (requests for JSON fetches, caching), but it introduces trade-offs in performance, API limits, and data volume.

The current tool already fetches JSON metadata for top 10 name-matches (via `fetch_project_details()` at https://pypi.org/pypi/{pkg}/json), so this builds on that. However, searching "all" descriptions for 736k packages is impractical (rate limits, time, bandwidth—PyPI allows ~100 req/min). Instead, use a **hybrid approach**: Name-based pre-filter (fast), then deep search on fetched data for candidates.

I'll outline **what's involved**, **user-friendly alternatives to full web search**, and **implementation plan**. Effort: 6-8 hours (more than fuzzy due to caching/fetching complexity). No major rewrite needed.

#### 1. What's Involved (High-Level Overview)
- **Data Sources**: PyPI JSON per package includes:
  - `info.summary`: Short description (1-2 sentences).
  - `info.description`: Full RST/HTML (long, up to 10k chars; already converted to MD in tool).
  - `info.classifiers`: List (e.g., "License :: OSI Approved :: MIT", "Programming Language :: Python :: 3.10").
  - `info.requires_python`: String (e.g., ">=3.10").
  - `info.project_urls`: Dict (e.g., {"Homepage": "https://..."}).
  - Why useful: Descriptions often contain keywords (e.g., "async", "web framework").
- **Challenges**:
  - **Scale**: Can't fetch all 736k JSONs upfront (hours, banned by PyPI). Fetch on-demand for name-matches (e.g., limit to 100-500 candidates).
  - **Performance**: Each fetch ~0.2s (timeout=10); for 100 pkgs: ~20s. Cache desc like names (add DESC_CACHE_FILE).
  - **Search Type**: Simple keyword (in text), or advanced (TF-IDF for relevance, fuzzy on desc).
  - **Output**: Show matching field (e.g., "aiohttp: Found in description: 'Async HTTP client...'").
  - **Rate Limits**: PyPI is generous but monitor; add delays (time.sleep(0.1)).
  - **Data Quality**: Descriptions are RST/HTML (already handled); summaries are plain. Normalize (lower, strip tags).
- **Benefits**: Makes tool more powerful for discovery (e.g., "REST API" finds "fastapi" via desc). Complements name search.
- **Risks**: Slower searches; large outputs if many matches. Mitigate with limits (top 50 results, --max-fetch=100).

#### 2. User-Friendly Alternatives to Full Web Search
Full-text search on all data is overkill for most users. Prioritize simplicity:

- **Keyword in Summary/Description (Recommended Default)**: Search for words/phrases in `summary` or `description` (case-insensitive).
  - Why better: Easy (no regex needed), relevant (descs explain purpose). Limit to top name-matches first.
  - Example: "async web" finds packages with that in summary (e.g., "aiohttp: Asynchronous HTTP Client...").

- **Classifier/Filter Search**: Search classifiers (e.g., "license MIT" or "python 3.12").
  - Why better: Structured data, fast (no text parsing). Like facets in search engines.
  - Example: "--classifiers 'OSI Approved'" filters to open-source.

- **Requires Python Filter**: Search `requires_python` (e.g., "--python '>=3.11'").
  - Why better: Common need (compatibility); simple string match.

- **Advanced: Relevance Scoring**: Rank by keyword frequency in desc (using scikit-learn TF-IDF or simple count).
  - Why better: Prioritizes best matches (e.g., "web framework" ranks "django" higher if more mentions).
  - Library: scikit-learn (lightweight; add to deps).

- **Hybrid Mode**: Name search first (substring/fuzzy), then desc filter on results. Default for usability.
- **Avoid**: Full index of all desc (too heavy; use external like whoosh for offline search, but overkill for CLI).

**Recommendation**: Add `--search-desc` (keyword in summary/desc of name-matches) as default extension. Keep name search primary; add `--search-classifiers` and `--search-python` for filters. This is more appropriate than regex for non-experts—keyword search is intuitive like Google.

#### 3. Detailed Implementation Outline
Build on existing `get_packages()` (names) and `fetch_project_details()` (JSON). Add desc caching. I can execute this if you approve.

##### Step 1: Add Dependencies and Cache for Descriptions (pyproject.toml, pypi_search.py)
- Deps (lightweight):
  ```
  scikit-learn>=1.5.0  # For TF-IDF relevance (optional)
  ```
- New Cache: Add DESC_CACHE_DIR = CACHE_DIR / "descs", DESC_CACHE_FILE = DESC_DIR / "descs.json" (dict {pkg: {"summary": str, "description": str, "classifiers": list}}).
- Functions:
  - `is_desc_cache_valid()`: Similar to is_cache_valid (e.g., 7 days).
  - `load_cached_descs()`: Load JSON.
  - `save_descs_to_cache(descs)`: Save dict.
  - `fetch_package_desc(pkg)`: Call fetch_project_details(pkg, include_desc=True), extract info.summary/description/classifiers, cache it.
- Pre-fetch? No—fetch lazily for matches.
- Effort: 20 min.

##### Step 2: Update CLI (argparse in main())
- Add group:
  ```
  search_group = parser.add_mutually_exclusive_group()
  search_group.add_argument("--name", action="store_true", help="Search package names (default)")
  search_group.add_argument("--desc", action="store_true", help="Search descriptions/summaries of name-matches")
  search_group.add_argument("--classifiers", action="store_true", help="Search classifiers")
  search_group.add_argument("--all", action="store_true", help="Search names + desc + classifiers")
  parser.add_argument("--max-fetch", type=int, default=100, help="Max packages to fetch for desc search")
  ```
- Default: --name (current behavior).
- Effort: 10 min.

##### Step 3: Modify Matching Logic (in main(), after get_packages)
- Name pre-filter: Always do substring (or mode from prior fuzzy plan) to get candidates (limit to args.max_fetch).
- Then:
  ```
  candidates = get_packages(...)  # Name matches, limit to max_fetch
  matches = []
  for pkg in candidates:
      desc_data = fetch_package_desc(pkg)  # Fetch/cache
      if not desc_data: continue
      text = f"{desc_data['summary']} {desc_data['description']} {' '.join(desc_data['classifiers'])}"
      text_lower = text.lower()
      if args.desc and pattern_lower in text_lower:
          matches.append(pkg)
      elif args.classifiers:
          if any(pattern_lower in clf.lower() for clf in desc_data['classifiers']):
              matches.append(pkg)
      elif args.all:
          if pattern_lower in pkg.lower() or pattern_lower in text_lower:
              matches.append(pkg)
  ```
- For relevance (optional): Use TF-IDF on descs of candidates, score/rank.
  - Simple: Count keyword occurrences, sort by count.
  - Advanced: from sklearn.feature_extraction.text import TfidfVectorizer; vectorizer.fit_transform([text]); scores = vectorizer.transform([pattern]).toarray().
- Cache hits: If desc cached and valid, skip fetch.
- Effort: 30 min (fetch/caching logic).

##### Step 4: Update Output
- For desc matches: Show snippet (e.g., "aiohttp: 'Asynchronous HTTP...' (in description)").
  - In print loop: If desc match, append "[dim]in desc[/dim]".
- Limit output: Top 20 by relevance if many.
- With --desc flag: Still show full details for top 10.
- Effort: 15 min.

##### Step 5: Tests (src/test/test_pypi_search.py)
- Extend TestGetPackages/TestMain:
  - `test_desc_search(mock_fetch, mock_cache)`: Mock fetch_project_details to return desc with keyword; assert matches.
  - `test_classifiers_search(mock_fetch)`: Mock classifiers list; assert filter.
  - `test_cache_desc_valid/invalid`: Mock DESC_CACHE_FILE stat/open.
  - `test_max_fetch_limit`: Assert only N fetches called.
  - Use patch('src.pypi_search.fetch_package_desc') for isolation.
- Run full suite to ensure no regressions.
- Effort: 45 min (add 8-10 tests).

##### Step 6: Performance, Docs, and Release
- Cache: Save descs after fetch (extend save_packages_to_cache).
- Rate Limit: Add `time.sleep(0.1)` between fetches.
- Docs: Update README with examples (e.g., `pipy_search "async" --desc --max-fetch=50`).
- Test: Run with real data (e.g., "flask" --desc finds framework mentions).
- Release: Same as fuzzy (uv sync, build, workflows).
- Effort: 20 min.

#### Potential Challenges and Mitigations
- **API Load**: PyPI limits (no hard ban, but fair use). Mitigation: Cache aggressively (7 days), limit max_fetch=200, optional --no-cache-refresh.
- **Large Descriptions**: RST conversion already handles (extract_raw_html_blocks, etc.); truncate snippets to 200 chars.
- **Relevance**: Keyword may miss synonyms; future: Embeddings (sentence-transformers, but heavy).
- **Offline Mode**: Desc cache enables it; add --offline flag.
- **Cost**: Free, but fetches add latency (20s for 100); progress bar with rich.status.

This extension would make pypi_search a "smart" discovery tool (name + content search), rivaling pip search or pypi.org UI. If you want to implement (e.g., add --search-desc first), I can create a plan/TODO like the test coverage one!

## Implementing Metadata Caching

### Yes, Summary and Full Description Caching Makes Sense

Absolutely—caching PyPI metadata (summary + full description/classifiers from /pypi/{pkg}/json) is a smart extension, especially for desc/classifier searches (as in prior memory). It mirrors your existing name cache (23h TTL), reduces API overhead (100 fetches → 0 on hits), complies with rate limits, and enables offline mode. With 736k packages, selective caching (on-demand, LRU prune) keeps storage reasonable (~1-2GB compressed).

Your idea (compression, summary hashing for invalidation, tiered TTL) is excellent:
- **Summaries**: Short TTL (1-4h, fast fetch ~1kB), hash to detect changes → invalidate full desc.
- **Full Desc**: Longer TTL (24-48h), compress (zlib), store only if requested (--full-desc or --desc).
- **Efficiency**: ~90% hit rate for repeated use; prune by age/size.

**Pros**:
- **Speed**: Cache hit: <1ms vs 0.2s/fetch.
- **Bandwidth/Rate**: Save 100s MB/API calls.
- **User-Friendly**: Seamless (auto-fetch if miss, progress bar).
- **Robust**: Hash-based invalidation catches updates without full re-fetch.

**Cons/Mitigations**:
- Storage: Prune inactive (LRU via heapq or TTL).
- Complexity: ~2h impl, stdlib only (no deps).
- Changes: Rare, but TTL/hash handles.

#### Implementation Plan (Low Effort, ~2-3h)
Leverage existing cache (CACHE_DIR). Add DESC_CACHE_DIR = CACHE_DIR / "descs" (JSONL for append efficiency).

##### 1. Cache Structure
- **desc_summaries.jsonl**: {pkg: {"hash": sha256(summary), "summary": str, "timestamp": float}} – 1h TTL.
- **desc_full.jsonl.gz**: {pkg: {"description": str (compressed RST/MD), "classifiers": list, "timestamp": float}} – 24h TTL.
- Size: Summaries ~500MB uncompressed; full ~2GB compressed.

##### 2. Key Functions (src/pypi_search.py)
```python
import json
import zlib
import hashlib
from pathlib import Path
DESC_SUMMARY_FILE = CACHE_DIR / "descs" / "summaries.jsonl"
DESC_FULL_FILE = CACHE_DIR / "descs" / "full.jsonl.gz"
SUMMARY_TTL_HOURS = 4
FULL_TTL_HOURS = 24

def hash_summary(summary: str) -> str:
    return hashlib.sha256(summary.encode()).hexdigest()[:16]

def is_summary_cache_valid(pkg: str) -> bool:
    if not DESC_SUMMARY_FILE.exists(): return False
    # Parse JSONL, check pkg entry TTL/hash
    # ...

def get_or_fetch_summary(pkg: str) -> dict | None:
    if is_summary_cache_valid(pkg):
        return load_summary(pkg)
    data = fetch_project_details(pkg, include_desc=False)['info']  # summary only
    summary_hash = hash_summary(data['summary'])
    save_summary(pkg, data['summary'], summary_hash)
    return data

def get_or_fetch_full_desc(pkg: str, force_summary_hash: str = None) -> dict | None:
    if force_summary_hash and load_summary_hash(pkg) != force_summary_hash:
        invalidate_full(pkg)  # Delete full if summary changed
    if is_full_cache_valid(pkg):
        return load_full_desc(pkg)
    data = fetch_project_details(pkg, include_desc=True)['info']
    compressed_desc = zlib.compress(data['description'].encode())
    save_full_desc(pkg, compressed_desc, data['classifiers'])
    return data
```

- **load/save**: JSONL append/read (fast, atomic).
- **invalidate_full(pkg)**: Remove line from JSONL.gz.
- **ensure_desc_cache_dir()**: mkdir.

##### 3. Integrate into Search (main())
In desc search loop:
```
candidates = name_matches[:args.max_fetch]  # e.g., 100
matches = []
for pkg in candidates:
    summary_data = get_or_fetch_summary(pkg)
    if not summary_data: continue
    if pattern_lower in summary_data['summary'].lower():
        full_data = get_or_fetch_full_desc(pkg, summary_data['hash']) if args.full_desc else None
        matches.append((pkg, full_data))
```

- Progress: rich.progress for fetches.
- Prune: On save, if >1M entries, remove oldest 10%.

##### 4. CLI Updates

Apologies—response cut off due to length limit. Full CLI updates for caching:

```
parser.add_argument("--search-desc", action="store_true", help="Search summaries/descriptions")
parser.add_argument("--cache-desc-ttl", type=int, default=24, help="Full desc TTL hours")
parser.add_argument("--prune-cache", action="store_true", help="Prune old desc cache entries")
```

Integrate in search logic as shown. Stored complete plan in memory earlier. Ready to implement if approved.


## DB Tech for Caching

### Best Caching Mechanism for pypi-search

For caching package metadata (names ~736k entries, summaries/full descs with TTL/hash invalidation, prune, compression), prioritize **embedded KV store** (no server, crash-safe). Balance: **LMDB** wins (speed/stability/ease/open source). Here's ranked options:

#### 1. **LMDB (Top Recommendation)**
   - **Why Best**: Lightning-fast memory-mapped KV (1M+ ops/sec reads), ACID (MVCC, crash-safe), tiny (~1MB), zero-config embedded. Open source (Mozilla Public License). Python `lmdb` (pip install lmdb, pure binding).
   - **Stability**: Battle-tested (Chrome, OpenLDAP); no corruption even on power loss.
   - **Ease**: Simple API:
     ```python
     import lmdb
     env = lmdb.open(str(cache_dir / 'descs.lmdb'), map_size=1e9)  # 1GB
     with env.begin(write=True) as txn:
         txn.put(b'pkg', zlib.compress(json.dumps(data).encode()))  # Compressed JSON
     data = json.loads(zlib.decompress(txn.get(b'pkg')))
     ```
     TTL: Store {data, timestamp, hash} in value; check on get.
     Prune: Cursor iterate/drop old.
   - **Speed**: Beats SQLite 10x for KV; in-memory feel.
   - **Fit**: Perfect for pkg -> compressed JSON; supports hash invalidation.
   - **Cons**: Single-writer (fine for CLI); pip dep (add to pyproject.toml).
   - **Effort**: 30min integration.

#### 2. **SQLite (Strong Stdlib Alternative)**
   - **Why Good**: Pure stdlib (`sqlite3`), ACID, JSON support (`json_extract`). Open source (Public Domain).
   - **Stability**: Rock-solid, WAL mode crash-safe.
   - **

## Priority of Feature Implementation

### Feature Prioritization for pypi_search

Based on the features in `docs/notes/pypi_search New Features.md`, I prioritized using quick wins (low-effort, high-value additions), ergonomics (user-friendliness, e.g., intuitive CLI/defaults over complex UIs), and complexity (effort estimate, code changes needed). Interdependencies: Search options (fuzzy/sounds-like) are standalone but enhance core CLI; desc searches depend on cache upgrades (hashing/compression for efficiency); config enables defaults across features; browse/notes build on output/caching; UI frontend is a full rewrite (highest complexity, last).

#### Key Rationale
- **Quick Wins**: Console flags (trivial argparse tweaks), fuzzy/sounds-like (in-memory, ~4h per memory plans, no new deps beyond rapidfuzz/jellyfish).
- **Ergonomics**: Prioritize CLI improvements (e.g., substring default over regex, desc search for discovery) before UIs; cache makes repeated use faster.
- **Complexity/Dependencies**:
  - Low: CLI-only (no I/O changes).
  - Medium: Search desc/full (~6-8h, adds fetching/caching; harder without base cache hash/invalidation, but enables offline/smart caching).
  - High: Browse/UI (custom pager/themes, ~10+h; depends on output enhancements); notes/favs (storage/UI, ~8h); config UI (curses-like, ~5h, but simple TOML first).
  - Implementing cache first reduces desc search complexity by 30% (avoids redundant fetches); fuzzy first eases desc filtering (pre-filter candidates).

#### Recommended Order (Phased, ~40-50h total)
1. **Console Options (--no-pager, --no-color)**: Quick win (1h, argparse + Rich tweaks). High ergonomics (flexible output). No deps. Implement first for basic polish.
2. **Search Options: Fuzzy (--fuzzy) & Sounds-Like (--sounds-like)**: Quick/medium (4-6h total, per memory). Ergonomic upgrade (typo-tolerant, phonetic for non-experts; default to substring). Standalone, boosts core search. Low interdep impact.
3. **Cache Document Content (Hash invalidation, compression, summary→full trigger)**: Medium (3-5h, extend existing cache with zlib/JSONL). Foundational for efficiency. Makes desc search 2x easier/faster. High value for repeated use.
4. **Search Options: Desc (--search-desc, limit 500) & Full Desc (--search-full, limit 100)**: Medium (6h, hybrid name+desc per memory). Ergonomic discovery (keyword in metadata). Depends on #3 (caching); fuzzy pre-filter reduces fetch load.
5. **Configuration (~/.config/...conf, basic TOML defaults)**: Low-medium (2h, tomllib for mode/thresholds). Ergonomics for prefs (e.g., default fuzzy). Applies to all prior; skip term UI until later.
6. **Cache Everything (Smart summaries/docs caching)**: Medium (3h, overlaps #3; add LRU prune). Builds directly on #3; enables offline/full desc without perf hit.
7. **Browse Mode (Custom pager, fwd/back search, themes)**: High (8-10h, Rich status + custom pager). Ergonomics for large outputs. Depends on #1/#2 (output flex) + #6 (lazy load from cache).
8. **Notes, Favorites, Bookmarks**: Medium-high (5h, JSON storage + CLI add/remove). Nice-to-have; depends on #5 (config) + #6 (cache for quick access).
9. **Term-Based Config UI**: Medium (4h, curses or Rich prompt). Ergonomics for non-file edits; depends on #5 (base config).
10. **UI Frontend**: High (20+h, e.g., Textual/Tkinter). Lowest priority (CLI-first tool); depends on all (full caching/UI elements). Defer unless web/mobile needed.

This order delivers iterative value: Core CLI refined early (1-2), caching enables advanced search (3-4), then UX polish (5-10). Total phases: CLI (1-2: 5h), Search+Cache (3-6: 14h), Advanced UX (7-10: 37h). No major blockers; each builds incrementally without inflating later complexity. If implementing, I'd plan the first phase next.


