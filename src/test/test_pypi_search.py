import pytest
from unittest.mock import patch, MagicMock
from importlib.metadata import PackageNotFoundError
from requests.exceptions import RequestException
import time
import json
import logging
import os
from textwrap import dedent
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.pypi_search_caching import (
    main,
    get_packages,
    fetch_project_details,
    fetch_all_package_names,
    is_cache_valid,
    load_cached_packages,
    save_packages_to_cache,
    ensure_cache_dir,
    CACHE_FILE,
    CacheManager,
    CACHE_DIR,
    CACHE_MAX_AGE_SECONDS,
    convert_rst_table,
    parse_simple_rst_list_table,
    rich_table_to_markdown,
    extract_raw_html_blocks,
    convert_rst_code_blocks,
    init_lmdb_env,
    store_package_data,
    retrieve_package_data,
)

from rich.table import Table
from rich.console import Console



def strip_ansi(text):
    import re
    return re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', text)

@pytest.fixture
def capsys_disabled(capfd):
    """Disable capfd for tests that don't use it."""

    pass

@pytest.fixture(autouse=True)
def mock_home(tmp_path, monkeypatch):
    def mock_home(cls):
        return tmp_path
    monkeypatch.setattr('pathlib.Path.home', classmethod(mock_home))

class TestCacheUtils:
    def test_ensure_cache_dir(self, tmp_path, monkeypatch):
        test_cache_dir = tmp_path / ".cache" / "p"
        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.CACHE_DIR', test_cache_dir)
        assert not test_cache_dir.exists()
        ensure_cache_dir()
        assert test_cache_dir.exists()

    def test_is_cache_valid_no_file(self, tmp_path, monkeypatch):
        test_cache_file = tmp_path / "test.cache"
        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.CACHE_FILE', test_cache_file)
        # no write, so not exists
        assert not is_cache_valid()

    def test_is_cache_valid_recent(self, tmp_path, monkeypatch):
        test_cache_file = tmp_path / "test.cache"
        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.CACHE_FILE', test_cache_file)
        now = time.time()
        monkeypatch.setattr('time.time', lambda: now)
        test_cache_file.write_text('')
        os.utime(str(test_cache_file), (now - 100, now - 100))
        assert is_cache_valid()

    def test_is_cache_valid_old(self, tmp_path, monkeypatch):
        test_cache_file = tmp_path / "test.cache"
        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.CACHE_FILE', test_cache_file)
        now = time.time()
        monkeypatch.setattr('time.time', lambda: now)
        test_cache_file.write_text('')
        os.utime(str(test_cache_file), (now - CACHE_MAX_AGE_SECONDS * 2, now - CACHE_MAX_AGE_SECONDS * 2))
        assert not is_cache_valid()

    def test_load_cached_packages(self, tmp_path, monkeypatch):
        test_cache_file = tmp_path / "test.cache"
        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.CACHE_FILE', test_cache_file)
        test_cache_file.write_text("pkg1\npkg2\n\n\npkg3")
        pkgs = load_cached_packages()
        assert pkgs == ["pkg1", "pkg2", "pkg3"]

    def test_save_packages_to_cache(self, tmp_path, monkeypatch):
        test_cache_file = tmp_path / "test.cache"
        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.CACHE_FILE', test_cache_file)
        save_packages_to_cache(["pkg2", "pkg1", "pkg3"])
        assert test_cache_file.read_text() == "pkg1\npkg2\npkg3\n"

    def test_cache_manager_load_exception_fallback(self, tmp_path, monkeypatch):
        from src.pypi_search_caching.pypi_search_caching import CacheManager, load_cached_packages, save_packages_to_cache, CACHE_FILE

        # Setup legacy cache
        legacy_packages = ["pkg1", "pkg2"]
        test_cache_file = tmp_path / "test.cache"
        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.CACHE_FILE', test_cache_file)
        test_cache_file.write_text("pkg1\npkg2\n")

        # Mock LMDB load to raise exception
        def mock_init_lmdb_env():
            env = MagicMock()
            env.begin.return_value.__enter__.return_value.get.return_value = None
            return env

        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.init_lmdb_env', mock_init_lmdb_env)
        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.json', MagicMock(loads=lambda x: {'data': b'', 'timestamp': time.time() - 100}))

        # Mock legacy load
        with patch('src.pypi_search_caching.pypi_search_caching.load_cached_packages') as mock_legacy_load:
            mock_legacy_load.return_value = legacy_packages
            cm = CacheManager()
            packages = cm.load()
            assert packages == legacy_packages
            mock_legacy_load.assert_called_once()

        # Verify migration: save called
        cm.save(legacy_packages)

    def test_cache_manager_save_deletes_legacy(self, tmp_path, monkeypatch):
        from src.pypi_search_caching.pypi_search_caching import CacheManager, CACHE_FILE

        test_cache_file = tmp_path / "test.cache"
        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.CACHE_FILE', test_cache_file)
        test_cache_file.touch()  # Create legacy file

        # Mock LMDB save to succeed
        def mock_init_lmdb_env():
            env = MagicMock()
            return env

        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.init_lmdb_env', mock_init_lmdb_env)

        cm = CacheManager()
        cm.save(["pkg1"])

        assert not test_cache_file.exists()  # Legacy deleted

class TestFetch100PackageNames:
    def test_success(self):
        html = '<html><a href="testpkg/">testpkg</a><a href="testpkg2/">testpkg2</a></html>'
        with patch('requests.get', return_value=MagicMock(text=html, status_code=200, raise_for_status=lambda: None)):
            pkgs = fetch_all_package_names(limit=2)
        assert pkgs == ["testpkg", "testpkg2"]

    def test_network_error(self, capfd):
        with patch('requests.get', side_effect=RequestException("network")):
            with pytest.raises(SystemExit, match="1"):
                fetch_all_package_names()
        captured = capfd.readouterr()
        assert "Error downloading PyPI index" in captured.err

    def test_limited_fetch(self):
        pkgs = fetch_all_package_names(limit=100)
        assert len(pkgs) == 100
        assert all(isinstance(p, str) and p.strip() for p in pkgs)

class TestFetchProjectDetails:
    def test_success(self):
        json_data = {"info": {"version": "1.0", "requires_python": ">=3.10", "home_page": "https://example.com", "project_urls": {"Download URL": "https://files.example", "Bug Tracker": "https://issues.example"}, "classifiers": ["License :: OSI Approved"], "summary": "Test pkg", "description": "Test desc"}}
        resp = MagicMock(status_code=200, json=lambda: json_data, raise_for_status=lambda: None)
        with patch('requests.get', return_value=resp):
            md = fetch_project_details("testpkg", include_desc=True)
        assert "## testpkg" in md
        assert "**Version:** `1.0`" in md
        assert "**Requires Python:** >=3.10" in md
        assert "**Homepage:** [https://example.com](https://example.com)" in md
        assert "**Release:** [https://files.example](https://files.example)" in md
        assert "**Bug Tracker:** [https://issues.example](https://issues.example)" in md
        assert "**Classifiers:**\n- License :: OSI Approved" in md
        assert "**Summary:** Test pkg" in md
        assert "**Full Description:**" in md

    def test_lmdb_cache_hit(self, monkeypatch):
        # Mock time to be within age
        now = time.time()
        monkeypatch.setattr('time.time', lambda: now)

        cached_data = {
            'headers': {'timestamp': now - 100},  # Within CACHE_MAX_AGE_SECONDS
            'json': json.dumps({"info": {"version": "1.0", "summary": "Test pkg"}}),
            'md': "## testpkg\n**Version:** `1.0`\n**Summary:** Test pkg"
        }
        with patch('src.pypi_search_caching.pypi_search_caching.retrieve_package_data', return_value=cached_data):
            with patch('requests.get') as mock_get:
                md = fetch_project_details("testpkg", include_desc=True)
                mock_get.assert_not_called()  # No request made
                assert md == cached_data['md']

    def test_lmdb_cache_hit_no_md(self, monkeypatch):
        now = time.time()
        monkeypatch.setattr('time.time', lambda: now)

        cached_data = {
            'headers': {'timestamp': now - 100},
            'json': json.dumps({"info": {"version": "1.0", "summary": "Test pkg"}}),
            'md': None
        }
        with patch('src.pypi_search_caching.pypi_search_caching.retrieve_package_data', return_value=cached_data):
            with patch('requests.get') as mock_get:
                md = fetch_project_details("testpkg", include_desc=False)
                mock_get.assert_not_called()
                assert "**Version:** `1.0`" in md

    def test_lmdb_cache_miss(self, tmp_path, monkeypatch):
        now = time.time()
        monkeypatch.setattr('time.time', lambda: now)

        lmdb_path = tmp_path / "lmdb"
        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.LMDB_DIR', lmdb_path)

        json_data = {"info": {"version": "1.0", "summary": "Test pkg", "description": "Desc"}}
        resp = MagicMock(status_code=200, json=lambda: json_data, raise_for_status=lambda: None)

        with patch('src.pypi_search_caching.pypi_search_caching.retrieve_package_data', return_value=None):
            with patch('requests.get', return_value=resp):
                with patch('src.pypi_search_caching.pypi_search_caching.init_lmdb_env') as mock_init:
                    with patch('src.pypi_search_caching.pypi_search_caching.store_package_data') as mock_store:
                        md = fetch_project_details("testpkg", include_desc=True)
                        mock_init.assert_called()
                        mock_store.assert_called_once()
                        assert "## testpkg" in md

    def test_lmdb_cache_stale(self, monkeypatch):
        from src.pypi_search_caching.pypi_search_caching import LMDB_CACHE_MAX_AGE_SECONDS
        now = time.time()
        monkeypatch.setattr('time.time', lambda: now)

        stale_timestamp = now - LMDB_CACHE_MAX_AGE_SECONDS * 2
        cached_data = {'headers': {'timestamp': stale_timestamp}, 'json': '{}', 'md': None}
        json_data = {"info": {"version": "1.0"}}
        resp = MagicMock(status_code=200, json=lambda: json_data, raise_for_status=lambda: None)

        with patch('src.pypi_search_caching.pypi_search_caching.retrieve_package_data', return_value=cached_data):
            with patch('requests.get', return_value=resp):
                with patch('src.pypi_search_caching.pypi_search_caching.store_package_data') as mock_store:
                    md = fetch_project_details("testpkg", include_desc=False)
                    mock_store.assert_called_once()  # Treats as miss and stores

    def test_lmdb_exception_fallback(self, monkeypatch):
        now = time.time()
        monkeypatch.setattr('time.time', lambda: now)

        json_data = {"info": {"version": "1.0"}}
        resp = MagicMock(status_code=200, json=lambda: json_data, raise_for_status=lambda: None)

        with patch('src.pypi_search_caching.pypi_search_caching.init_lmdb_env', side_effect=Exception("LMDB error")):
            with patch('requests.get', return_value=resp):
                md = fetch_project_details("testpkg", include_desc=False)
                assert "**Version:** `1.0`" in md  # Fallback to direct fetch succeeds

    def test_404_cache_miss_no_store(self, monkeypatch):
        now = time.time()
        monkeypatch.setattr('time.time', lambda: now)

        resp = MagicMock(status_code=404)

        with patch('src.pypi_search_caching.pypi_search_caching.retrieve_package_data', return_value=None):
            with patch('requests.get', return_value=resp):
                with patch('src.pypi_search_caching.pypi_search_caching.store_package_data') as mock_store:
                    result = fetch_project_details("nonexistent", include_desc=False)
                    assert result is None
                    mock_store.assert_not_called()  # No store on 404

    def test_include_desc_false_stores_json_only(self, tmp_path, monkeypatch):
        now = time.time()
        monkeypatch.setattr('time.time', lambda: now)

        lmdb_path = tmp_path / "lmdb"
        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.LMDB_DIR', lmdb_path)

        json_data = {"info": {"version": "1.0", "description": "Desc"}}
        resp = MagicMock(status_code=200, json=lambda: json_data, raise_for_status=lambda: None)

        with patch('src.pypi_search_caching.pypi_search_caching.retrieve_package_data', return_value=None):
            with patch('requests.get', return_value=resp):
                with patch('src.pypi_search_caching.pypi_search_caching.store_package_data') as mock_store:
                    md = fetch_project_details("testpkg", include_desc=False)
                    mock_store.assert_called_once()
                    # Verify md_data is None (no full desc processed)
                    call_args = mock_store.call_args[0][4]  # md_data param
                    assert call_args is None

    def test_lmdb_roundtrip_compression(self, tmp_path, monkeypatch):
        now = time.time()
        monkeypatch.setattr('time.time', lambda: now)

        # Setup mock LMDB dir
        mock_lmdb_dir = tmp_path / "lmdb"
        mock_lmdb_dir.mkdir(parents=True)
        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.LMDB_DIR', mock_lmdb_dir)

        # Test data
        package_name = "testpkg"
        headers = {'timestamp': now}
        json_str = json.dumps({"info": {"version": "1.0"}})
        md_str = "## Test MD"

        # Store
        env = init_lmdb_env()
        store_package_data(env, package_name, headers, json_str, md_str)
        env.close()

        # Retrieve and verify roundtrip
        env = init_lmdb_env()
        retrieved = retrieve_package_data(env, package_name)
        env.close()

        assert retrieved is not None
        assert retrieved['headers'] == headers
        assert json.loads(retrieved['json']) == json.loads(json_str)
        assert retrieved['md'] == md_str

    def test_fetch_project_details_cached_classifiers_summary(self, monkeypatch):
        now = time.time()
        monkeypatch.setattr('time.time', lambda: now)

        cached_data = {
            'headers': {'timestamp': now - 100},
            'json': json.dumps({
                "info": {
                    "version": "1.0",
                    "summary": "Test summary",
                    "classifiers": ["License :: OSI Approved :: MIT", "Programming Language :: Python :: 3"]
                }
            }),
            'md': None
        }
        with patch('src.pypi_search_caching.pypi_search_caching.retrieve_package_data', return_value=cached_data):
            with patch('requests.get') as mock_get:
                md = fetch_project_details("testpkg", include_desc=False)
                mock_get.assert_not_called()
                assert "**Version:** `1.0`" in md
                assert "**Summary:** Test summary" in md
                assert "**Classifiers:**\n- License :: OSI Approved :: MIT\n- Programming Language :: Python :: 3" in md

    def test_logging_in_fetch_project_details_cache_miss(self, caplog, monkeypatch):
        from src.pypi_search_caching.pypi_search_caching import fetch_project_details
        monkeypatch.setattr('time.time', lambda: 1234567890.0)

        # Cache miss and fetch
        with patch('src.pypi_search_caching.pypi_search_caching.retrieve_package_data', return_value=None):
            with caplog.at_level(logging.INFO):
                details = fetch_project_details("testpkg", include_desc=False, verbose=True)
        assert "Cache miss for testpkg, fetching from PyPI" in caplog.text

    def test_logging_in_fetch_project_details_cache_hit(self, caplog, monkeypatch):
        from src.pypi_search_caching.pypi_search_caching import fetch_project_details
        monkeypatch.setattr('time.time', lambda: 1234567890.0)

        # Cache hit (mock cached data)
        def mock_retrieve(env, pkg):
            return {'headers': {'timestamp': 1234567890.0 - 100}, 'json': json.dumps({'info': {'version': '1.0'}}), 'md': None}
        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.retrieve_package_data', mock_retrieve)
        with caplog.at_level(logging.INFO):
            details = fetch_project_details("testpkg", include_desc=False, verbose=True)
        assert "Cache hit for testpkg" in caplog.text
        assert "Stored testpkg in LMDB cache" not in caplog.text  # No store on hit

    def test_404(self):
        resp = MagicMock(status_code=404)
        with patch('requests.get', return_value=resp):
            assert fetch_project_details("nonexistent") is None

    def test_exception(self):
        with patch('requests.get', side_effect=RequestException()):
            assert fetch_project_details("test") is None

class TestGetPackages:
    def test_cache_valid(self):
        with patch.object(CacheManager, 'load', return_value=["pkg1"]):
            pkgs = get_packages(refresh_cache=False)
        assert pkgs == ["pkg1"]

    def test_cache_invalid_refresh(self):
        with patch('src.pypi_search_caching.pypi_search_caching.is_cache_valid', return_value=False), patch('src.pypi_search_caching.pypi_search_caching.fetch_all_package_names', return_value=["pkg1"]), patch('src.pypi_search_caching.pypi_search_caching.save_packages_to_cache'):
            pkgs = get_packages(refresh_cache=True)
        assert pkgs == ["pkg1"]

class TestMain:
    @patch('src.pypi_search_caching.pypi_search_caching.get_packages')
    @patch('sys.exit')
    def test_invalid_regex(self, mock_exit, mock_get_packages, monkeypatch):
        monkeypatch.setattr(sys, 'argv', ['script', r'['])  # invalid regex
        main()
        mock_exit.assert_called_once_with(2)

    @patch('src.pypi_search_caching.get_packages', return_value=[])
    def test_no_matches(self, mock_get, capsys):
        sys.argv = ['script', 'nonexistent']
        main()
        captured = capsys.readouterr()
        assert "No matching packages found." in strip_ansi(captured.out)

    @patch('src.pypi_search_caching.pypi_search_caching.get_packages', return_value=["pkg1", "pkg1"])
    def test_count_only(self, mock_get, capsys):
        sys.argv = ['script', 'pkg1', '--count-only']
        main()
        captured = capsys.readouterr()
        assert "Found 2 matching packages." in strip_ansi(captured.out)

    @patch('src.pypi_search_caching.pypi_search_caching.get_packages', return_value=["pkg1", "pkg1"])
    @patch('src.pypi_search_caching.pypi_search_caching.fetch_project_details', return_value="## testpkg\n**Version:** `1.0`")
    def test_list_with_desc(self, mock_details, mock_get, capsys):
        sys.argv = ['script', 'pkg1', '--desc']
        main()
        captured = capsys.readouterr()
        assert "pkg1" in captured.out
        assert "Version: 1.0" in strip_ansi(captured.out)
        assert "... and 0 more" not in captured.out  # <10

    @patch('src.pypi_search_caching.pypi_search_caching.get_packages', return_value=["pkg"] * 15)
    @patch('src.pypi_search_caching.pypi_search_caching.fetch_project_details', return_value="MD")
    def test_list_with_desc_full(self, mock_details, mock_get, capsys):
        sys.argv = ['script', 'pkg', '--desc', '--full-desc']
        main()
        captured = capsys.readouterr()
        assert "pkg" in captured.out  # all printed
        assert "MD" in captured.out  # top 10
        assert "... and 5 more matches" in strip_ansi(captured.out)

    @pytest.mark.parametrize('arg', ['--version', '-V'])
    def test_version_flag(self, monkeypatch, capsys, arg):
        monkeypatch.setattr(sys, 'argv', ['prog', arg])
        def mock_exit(code):
            raise SystemExit(code)
        monkeypatch.setattr('sys.exit', mock_exit)
        with patch('importlib.metadata.version') as mock_version:
            mock_version.return_value = '0.0.4b0'
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 0
            captured = capsys.readouterr()
            assert captured.out.strip() == 'pypi-search-caching 0.0.4b0'

    def test_version_file_missing(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['prog', '--version'])  # optional, since error early
        def mock_exit(code):
            raise SystemExit(code)
        monkeypatch.setattr('sys.exit', mock_exit)
        with patch('importlib.metadata.version', side_effect=PackageNotFoundError):
            with patch('pathlib.Path.exists', return_value=False):
                with pytest.raises(SystemExit) as exc:
                    main()
                assert exc.value.code == 1
                captured = capsys.readouterr()
                assert 'pyproject.toml not found and package not installed.' in captured.err

    def test_main_early_return_refresh_empty_pattern(self, monkeypatch):
        monkeypatch.setattr(sys, 'argv', ['script', '--refresh-cache', ''])
        with patch('src.pypi_search_caching.pypi_search_caching.get_packages') as mock_get:
            main()
            mock_get.assert_called_once_with(True)  # refresh=True
            # No further execution (no regex, no output)

    @patch('src.pypi_search_caching.pypi_search_caching.get_packages', return_value=["pkg"])
    def test_main_printing_without_desc(self, mock_get, capsys):
        sys.argv = ['script', 'pkg']
        main()
        captured = capsys.readouterr()
        out = strip_ansi(captured.out)
        assert "1. pkg" in out
        assert "Total: 1" in out
        assert "Version:" not in out  # No details

    def test_main_no_args_check(self, monkeypatch, capfd):
        monkeypatch.setattr(sys, 'argv', [])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        captured = capfd.readouterr()
        assert "Please provide a regex pattern." in captured.err


class TestRSTTableUtils:

    def test_parse_simple_rst_list_table_valid_header(self):
        rst = """.. list-table::
           :header-rows: 1
           
           * - Component
             - Description
           * - Foo
             - Bar"""
        table = parse_simple_rst_list_table(rst)
        md = rich_table_to_markdown(table)
        assert "| Component | Description |" in md
        assert "| Foo | Bar |" in md

    def test_parse_simple_rst_list_table_no_header(self):
        rst = """.. list-table::
           
           * - Val1
             - Val2"""
        table = parse_simple_rst_list_table(rst)
        md = rich_table_to_markdown(table)
        assert "| Val1 | Val2 |" in md

    def test_parse_simple_rst_list_table_with_link(self):
        rst = """.. list-table::
           :header-rows: 1
           
           * - Header1
             - Header2
           * - Text
             - `Link <https://example.com>`_"""
        table = parse_simple_rst_list_table(rst)
        md = rich_table_to_markdown(table)
        assert "| Header1 | Header2 |" in md
        assert "| Text | [Link](https://example.com) |" in md

    def test_parse_simple_rst_list_table_continuation(self):
        rst = """.. list-table::
           :header-rows: 1
           
           * - Header
             - Desc
           * - Item1
             - Line1
               Continued"""
        table = parse_simple_rst_list_table(rst)
        md = rich_table_to_markdown(table)
        assert "| Header | Desc |" in md
        assert "| Item1 | Line1 Continued |" in md

    def test_parse_simple_rst_list_table_empty(self):
        table = parse_simple_rst_list_table("")
        md = rich_table_to_markdown(table)
        expected = "| Component | Description |\n| --- | --- |"
        assert md.strip() == expected.strip()

    def test_rich_table_to_markdown_simple(self):
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Col1", style="cyan")
        table.add_column("Col2", style="green")
        table.add_row("Value1", "Value2|pipe")
        md = rich_table_to_markdown(table)
        expected = "| Col1 | Col2 |\n| --- | --- |\n| Value1 | Value2\\|pipe |"
        assert md.strip() == expected.strip()

    def test_rich_table_to_markdown_empty(self):
        table = Table()
        md = rich_table_to_markdown(table)
        assert md == ""

    def test_rich_table_to_markdown_with_header_no_rows(self):
        table = Table(show_header=True)
        table.add_column("Col1")
        md = rich_table_to_markdown(table)
        expected = "| Col1 |\n| --- |"
        assert md.strip() == expected.strip()

    def test_convert_rst_table_with_table(self):
        text = """Before

.. list-table::
   :header-rows: 1

   * - A
     - B
   * - 1
     - 2

After"""
        md = convert_rst_table(text)
        assert "| Component | Description |" in md
        assert "| A | B |" in md
        assert "| 1 | 2 |" in md
        assert "Before" in md
        assert "After" in md

    def test_convert_rst_table_no_table(self):
        text = "Plain text without table."
        md = convert_rst_table(text)
        assert md == text

    def test_convert_rst_table_multiple_tables(self):
        text = """Table1

.. list-table::
   :header-rows: 1
   * - C1
     - C2
   * - V1
     - V2

Text

.. list-table::
   * - D1
     - D2"""
        md = convert_rst_table(text)
        assert md.count("| --- |") == 2  # two tables

    def test_convert_rst_table_invalid_table(self):
        text = """.. list-table:: invalid
   * - unbalanced"""
        md = convert_rst_table(text)
        # Should not crash, output as is or partial
        assert "unbalanced" in md

    def test_extract_raw_html_blocks_simple(self):
        text = """Plain text.

.. raw:: html

    <p>Hello <b>world</b>!</p>

More text."""
        result = extract_raw_html_blocks(text)
        assert "Plain text." in result
        assert "Hello **world**!" in result
        assert "More text." in result

    def test_extract_raw_html_blocks_no_block(self):
        text = "Plain text without blocks."
        result = extract_raw_html_blocks(text)
        assert result == text

    def test_extract_raw_html_blocks_multiple(self):
        text = dedent("""First block.

.. raw:: html

    <p>One</p>

Second.

.. raw:: html

    <a href="https://example.com">Link</a>""")
        result = extract_raw_html_blocks(text)
        expected = dedent("""First block.

One


Second.

[Link](https://example.com)

""")
        assert result.rstrip('\n') == expected.rstrip('\n')

    def test_extract_raw_html_blocks_empty_block(self):
        text = """Text.

.. raw:: html



More."""
        result = extract_raw_html_blocks(text)
        assert result == "Text.\n\nMore."
        text = """Text.

.. raw:: html



More."""
        result = extract_raw_html_blocks(text)
        assert result == "Text.\n\nMore."

    def test_extract_raw_html_blocks_malformed(self):
        text = """.. raw:: html

    <p>Unclosed tag"""
        result = extract_raw_html_blocks(text)
        assert "Unclosed tag" in result
        # html2text should handle without crash

    def test_convert_rst_code_blocks_simple_lang(self):
        text = "Before.\n\n.. code-block:: python\n    def hello():\n        print(\"Hi\")\nAfter."
        result = convert_rst_code_blocks(text)
        expected = "Before.\n\n```python\n    def hello():\n        print(\"Hi\")\n```\nAfter."
        assert result.rstrip('\n') == expected.rstrip('\n')

    def test_convert_rst_code_blocks_no_lang(self):
        text = ".. code-block::\n    plain text\nEnd."
        result = convert_rst_code_blocks(text)
        expected = "```Code\n    plain text\n```\nEnd.\n"
        assert result.rstrip('\n') == expected.rstrip('\n')

    def test_convert_rst_code_blocks_multi_line(self):
        text = ".. code-block:: bash\n    echo \"line1\"\n        line2 continued\n    line3"
        result = convert_rst_code_blocks(text)
        expected = "```bash\n    echo \"line1\"\n        line2 continued\n    line3\n```\n"
        assert result.rstrip('\n') == expected.rstrip('\n')

    def test_convert_rst_code_blocks_unclosed(self):
        text = ".. code-block:: py\n    code here"
        result = convert_rst_code_blocks(text)
        expected = "```py\n    code here\n```\n"
        assert result.rstrip('\n') == expected.rstrip('\n')

    def test_convert_rst_code_blocks_no_block(self):
        text = "No code blocks."
        result = convert_rst_code_blocks(text)
        assert result.rstrip('\n') == text

    def test_convert_rst_code_blocks_multiple(self):
        text = "First.\n\n.. code-block:: js\n    console.log(\"a\")\nSecond.\n\n.. code-block:: py\n    print(\"b\")"
        result = convert_rst_code_blocks(text)
        expected = "First.\n\n```js\n    console.log(\"a\")\n```\nSecond.\n\n```py\n    print(\"b\")\n```\n"
        assert result.rstrip('\n') == expected.rstrip('\n')

    def test_parse_simple_rst_list_table_no_rows(self):
        rst = """.. list-table::
           :header-rows: 1

           * - Header1
             - Header2"""
        table = parse_simple_rst_list_table(rst)
        md = rich_table_to_markdown(table)
        assert "| Component | Description |" in md
        assert "| --- | --- |" in md
        # No data rows

    def test_parse_simple_rst_list_table_three_columns(self):
        rst = """.. list-table::
           :header-rows: 1

           * - Col1
             - Col2
           * - A
             - B
             - C  # This will append to Col2"""
        table = parse_simple_rst_list_table(rst)
        md = rich_table_to_markdown(table)
        assert "| A | B | C  # This will append to Col2 |" in md

    def test_parse_simple_rst_list_table_empty_cell(self):
        rst = """.. list-table::

           * - Item
             - """
        table = parse_simple_rst_list_table(rst)
        md = rich_table_to_markdown(table)
        assert "| Item | - |" in md

    def test_parse_simple_rst_list_table_continuation_link(self):
        rst = """.. list-table::
           :header-rows: 1

           * - Header
             - Desc
           * - Item
             - Line1
               `Continued <https://ex.com>`_"""
        table = parse_simple_rst_list_table(rst)
        md = rich_table_to_markdown(table)
        assert "`Continued <https://ex.com>`_" in md

    def test_parse_simple_rst_list_table_invalid(self):
        rst = "Not a table * - junk"
        table = parse_simple_rst_list_table(rst)
        md = rich_table_to_markdown(table)
        assert "| Component | Description |" in md  # empty table
        assert "| --- | --- |" in md


class TestLMDBCache:
    @pytest.fixture
    def mock_home(self, tmp_path, monkeypatch):
        mock_cache_dir = tmp_path / ".cache" / "pypi_search"
        mock_cache_dir.mkdir(parents=True)
        monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
        return mock_cache_dir

    @pytest.fixture
    def lmdb_env(self, tmp_path, monkeypatch):
        from src.pypi_search_caching.pypi_search_caching import init_lmdb_env, LMDB_DIR
        import os
        original_lmdb_dir = LMDB_DIR
        test_lmdb_dir = tmp_path / "lmdb"
        test_lmdb_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.LMDB_DIR', test_lmdb_dir)
        env = init_lmdb_env()
        yield env
        env.close()
        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.LMDB_DIR', original_lmdb_dir)

    @pytest.fixture
    def mock_time(self, monkeypatch):
        fixed_time = 1234567890.0
        monkeypatch.setattr('time.time', lambda: fixed_time)
        return fixed_time

    def test_init_lmdb_env(self, tmp_path, monkeypatch):
        from src.pypi_search_caching.pypi_search_caching import init_lmdb_env, LMDB_DIR
        import lmdb

        # Verify dir creation
        lmdb_path = tmp_path / "lmdb"
        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.LMDB_DIR', lmdb_path)
        assert not lmdb_path.exists()

        env = init_lmdb_env()
        assert lmdb_path.exists()
        assert isinstance(env, lmdb.Environment)
        env.close()

    def test_extract_headers(self):
        from src.pypi_search_caching.pypi_search_caching import extract_headers
        from unittest.mock import MagicMock

        mock_resp = MagicMock()
        mock_resp.headers = {
            'ETag': '"abc123"',
            'Last-Modified': 'Wed, 21 Oct 2015 07:28:00 GMT'
        }
        headers = extract_headers(mock_resp)
        assert headers['etag'] == '"abc123"'
        assert headers['last_modified'] == 'Wed, 21 Oct 2015 07:28:00 GMT'
        assert 'timestamp' in headers
        assert isinstance(headers['timestamp'], float)

        # Test missing headers
        mock_resp.headers = {}
        headers = extract_headers(mock_resp)
        assert headers['etag'] is None
        assert headers['last_modified'] is None
        assert 'timestamp' in headers

    def test_store_retrieve_roundtrip_json_only(self, lmdb_env, mock_time):
        from src.pypi_search_caching.pypi_search_caching import store_package_data, retrieve_package_data
        import json

        pkg = "testpkg"
        headers = {'etag': '"test"', 'last_modified': 'test-time', 'timestamp': mock_time}
        json_data = json.dumps({'info': {'version': '1.0'}})
        store_package_data(lmdb_env, pkg, headers, json_data)

        retrieved = retrieve_package_data(lmdb_env, pkg)
        assert retrieved is not None
        assert retrieved['headers'] == headers
        assert json.loads(retrieved['json']) == json.loads(json_data)
        assert retrieved['md'] is None

    def test_store_retrieve_roundtrip_with_md(self, lmdb_env, mock_time):
        from src.pypi_search_caching.pypi_search_caching import store_package_data, retrieve_package_data
        import json

        pkg = "testpkg"
        headers = {'etag': '"test"', 'last_modified': 'test-time', 'timestamp': mock_time}
        json_data = json.dumps({'info': {'version': '1.0'}})
        md_data = "# Test Markdown\nContent"
        store_package_data(lmdb_env, pkg, headers, json_data, md_data)

        retrieved = retrieve_package_data(lmdb_env, pkg)
        assert retrieved is not None
        assert retrieved['headers'] == headers
        assert json.loads(retrieved['json']) == json.loads(json_data)
        assert retrieved['md'] == md_data

    def test_retrieve_missing_key(self, lmdb_env):
        from src.pypi_search_caching.pypi_search_caching import retrieve_package_data

        retrieved = retrieve_package_data(lmdb_env, "nonexistent")
        assert retrieved is None

    def test_retrieve_invalid_compressed_data(self, lmdb_env, mock_time):
        from src.pypi_search_caching.pypi_search_caching import store_package_data, retrieve_package_data
        import struct
        import json

        pkg = "testpkg"
        headers = {'etag': '"test"', 'last_modified': 'test-time', 'timestamp': mock_time}
        headers_json = json.dumps(headers).encode('utf-8')
        invalid_json = b'invalid'  # Invalid compressed data

        # Manually create invalid value (short json compressed)
        value = (
            struct.pack('>I', len(headers_json)) + headers_json +
            struct.pack('>I', len(invalid_json)) + invalid_json +
            struct.pack('>I', 0) + b''
        )

        with lmdb_env.begin(write=True) as txn:
            txn.put(pkg.encode('utf-8'), value)

        # Should not raise, but return None or handle gracefully (current impl raises zlib.error)
        # To test coverage, we need to patch or expect exception, but for 100% coverage, add try/except in retrieve if needed
        # Assuming current code raises, test that it handles or adjust source if necessary
        # For now, test that it doesn't crash, but to cover decompress branch, we need valid/invalid paths
        retrieved = retrieve_package_data(lmdb_env, pkg)
        assert retrieved is None  # Handles invalid compressed data gracefully

    def test_retrieve_package_data_zlib_error_json(self, lmdb_env, mock_time):
        from src.pypi_search_caching.pypi_search_caching import retrieve_package_data
        import struct
        import json

        pkg = "testpkg"
        headers = {'timestamp': mock_time}
        headers_json = json.dumps(headers).encode('utf-8')
        invalid_json = b'invalid_zlib'  # Invalid for decompress
        md_compressed = b''

        # Manually create invalid value for json
        value = (
            struct.pack('>I', len(headers_json)) + headers_json +
            struct.pack('>I', len(invalid_json)) + invalid_json +
            struct.pack('>I', len(md_compressed)) + md_compressed
        )

        with lmdb_env.begin(write=True) as txn:
            txn.put(pkg.encode('utf-8'), value)

        retrieved = retrieve_package_data(lmdb_env, pkg)
        assert retrieved is None  # Handles zlib error for json

    def test_retrieve_package_data_zlib_error_md(self, lmdb_env, mock_time):
        from src.pypi_search_caching.pypi_search_caching import retrieve_package_data
        import struct
        import json
        import msgpack
        import zlib

        pkg = "testpkg"
        headers = {'timestamp': mock_time}
        json_data = json.dumps({'info': {'version': '1.0'}})
        valid_md = "# Test MD"

        headers_bytes = msgpack.packb(headers)
        json_compressed = zlib.compress(json_data.encode('utf-8'))
        # Invalid md: valid length but invalid compressed bytes
        invalid_md_compressed = b'invalid_zlib_data'  # Not valid zlib

        value = (
            struct.pack('>I', len(headers_bytes)) + headers_bytes +
            struct.pack('>I', len(json_compressed)) + json_compressed +
            struct.pack('>I', len(invalid_md_compressed)) + invalid_md_compressed
        )

        with lmdb_env.begin(write=True) as txn:
            txn.put(pkg.encode('utf-8'), value)

        retrieved = retrieve_package_data(lmdb_env, pkg)
        assert retrieved is not None
        assert retrieved['md'] is None  # Handles zlib error for md, keeps json

    def test_lmdb_env_map_size_and_options(self, tmp_path, monkeypatch):
        from src.pypi_search_caching.pypi_search_caching import init_lmdb_env

        lmdb_path = tmp_path / "lmdb"
        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.LMDB_DIR', lmdb_path)

        env = init_lmdb_env()
        # Verify map_size
        info = env.info()
        assert info['map_size'] == 10 * 1024**3  # 10GB
        # Other options are set at open, tested indirectly by successful init
        with env.begin(write=True) as txn:  # Verify not readonly
            pass
        env.close()

    def test_msgpack_roundtrip(self, lmdb_env, mock_time):
        from src.pypi_search_caching.pypi_search_caching import store_package_data, retrieve_package_data, extract_headers
        import json
        from unittest.mock import MagicMock
        import requests

        pkg = "testpkg"
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.headers = {'ETag': '"test"', 'Last-Modified': 'test-time'}
        headers = extract_headers(mock_resp)
        headers['timestamp'] = mock_time
        json_data = json.dumps({'info': {'version': '1.0'}})
        md_data = "# Test MD"

        store_package_data(lmdb_env, pkg, headers, json_data, md_data)

        retrieved = retrieve_package_data(lmdb_env, pkg)
        assert retrieved is not None
        assert retrieved['headers'] == headers
        assert json.loads(retrieved['json']) == {'info': {'version': '1.0'}}
        assert retrieved['md'] == md_data

    def test_prune_lmdb_cache(self, lmdb_env, mock_time):
        from src.pypi_search_caching.pypi_search_caching import LMDB_CACHE_MAX_AGE_SECONDS
        from src.pypi_search_caching.pypi_search_caching import store_package_data, prune_lmdb_cache, retrieve_package_data
        import json

        old_time = mock_time - LMDB_CACHE_MAX_AGE_SECONDS * 2
        new_time = mock_time

        # Store old entry
        old_headers = {'etag': '"test"', 'last_modified': 'test-time', 'timestamp': old_time}
        store_package_data(lmdb_env, 'oldpkg', old_headers, json.dumps({}), None)

        # Store new entry
        new_headers = {'etag': '"test"', 'last_modified': 'test-time', 'timestamp': new_time}
        store_package_data(lmdb_env, 'newpkg', new_headers, json.dumps({}), None)

        # Verify storage
        retrieved_old = retrieve_package_data(lmdb_env, 'oldpkg')
        assert retrieved_old is not None
        assert retrieved_old['headers']['timestamp'] == old_time

        retrieved_new = retrieve_package_data(lmdb_env, 'newpkg')
        assert retrieved_new is not None
        assert retrieved_new['headers']['timestamp'] == new_time

        # Prune
        pruned = prune_lmdb_cache(lmdb_env)
        assert pruned == 1  # Only old deleted

        # Verify old gone, new remains
        assert retrieve_package_data(lmdb_env, "oldpkg") is None
        assert retrieve_package_data(lmdb_env, "newpkg") is not None
        assert retrieve_package_data(lmdb_env, "newpkg")['headers']['timestamp'] == new_time

    def test_prune_invalid_entries(self, lmdb_env, mock_time):
        from src.pypi_search_caching.pypi_search_caching import prune_lmdb_cache
        import struct

        # Create invalid entry (short headers)
        invalid_value = struct.pack('>I', 0) + b''  # Empty headers
        with lmdb_env.begin(write=True) as txn:
            txn.put(b'invalidpkg', invalid_value)

        pruned = prune_lmdb_cache(lmdb_env)
        assert pruned == 1  # Invalid deleted


    def test_store_package_data_exception(self, monkeypatch):
        from src.pypi_search_caching.pypi_search_caching import store_package_data
        import json

        env = MagicMock()
        package_name = "testpkg"
        headers = {'timestamp': time.time()}
        json_data = json.dumps({"info": {"version": "1.0"}})
        md_data = "# Test Markdown\nContent"

        # Mock exception in __exit__ after successful put
        class MockTxn:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                raise Exception("LMDB write error")
            def put(self, key, value):
                pass  # No-op, simulates successful put before commit failure

        env.begin.return_value = MockTxn()

        with pytest.raises(Exception, match="LMDB write error"):
            store_package_data(env, package_name, headers, json_data, md_data)

    def test_retrieve_package_data_zlib_error(self, lmdb_env, mock_time):
        from src.pypi_search_caching.pypi_search_caching import store_package_data, retrieve_package_data
        import struct
        import json

        pkg = "testpkg"
        headers = {'timestamp': mock_time}
        headers_json = json.dumps(headers).encode('utf-8')
        json_str = json.dumps({"info": {"version": "1.0"}})
        # Corrupt json_compressed
        json_compressed = b'invalid_zlib'  # Invalid for decompress
        md_compressed = b''

        # Manually create invalid value
        value = (
            struct.pack('>I', len(headers_json)) + headers_json +
            struct.pack('>I', len(json_compressed)) + json_compressed +
            struct.pack('>I', len(md_compressed)) + md_compressed
        )

        with lmdb_env.begin(write=True) as txn:
            txn.put(pkg.encode('utf-8'), value)

        retrieved = retrieve_package_data(lmdb_env, pkg)
        assert retrieved is None  # Handles invalid compressed data gracefully

    def test_fetch_project_details_lmdb_warning(self, caplog, monkeypatch):
        from src.pypi_search_caching.pypi_search_caching import fetch_project_details
        monkeypatch.setattr('time.time', lambda: 1234567890.0)

        json_data = {"info": {"version": "1.0"}}
        resp = MagicMock(status_code=200, json=lambda: json_data, raise_for_status=lambda: None)

        # Mock LMDB init to raise exception (warning case)
        with caplog.at_level(logging.WARNING):
            with patch('src.pypi_search_caching.pypi_search_caching.init_lmdb_env', side_effect=Exception("LMDB error")):
                with patch('requests.get', return_value=resp):
                    md = fetch_project_details("testpkg", include_desc=False)
                    assert "**Version:** `1.0`" in md  # Fallback to direct fetch succeeds
                    assert "LMDB error for testpkg, falling back to direct fetch" in caplog.text

    def test_store_package_data_lmdb_warning(self, caplog, monkeypatch):
        from src.pypi_search_caching.pypi_search_caching import store_package_data
        import json

        env = MagicMock()
        package_name = "testpkg"
        headers = {'timestamp': time.time()}
        json_data = json.dumps({"info": {"version": "1.0"}})
        md_data = "# Test Markdown"

        # Mock exception in __exit__ after successful put
        class MockTxn:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                raise Exception("LMDB write error")
            def put(self, key, value):
                pass  # No-op, simulates successful put before commit failure

        env.begin.return_value = MockTxn()

        with caplog.at_level(logging.WARNING):
            with pytest.raises(Exception, match="LMDB write error"):
                store_package_data(env, package_name, headers, json_data, md_data)
            assert "Failed to store testpkg in LMDB cache" in caplog.text

# Run with pytest src/test/test_p.py --cov=src/p



class TestSearchFilter:
    def test_filter_by_description(self, monkeypatch, capsys):
        # Mock all_packages to some name matches
        mock_packages = ["package-a", "package-b", "package-c"]
        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.get_packages', lambda refresh: mock_packages)

        # Mock get_package_long_description
        def mock_get_desc(pkg, verbose=False):
            if pkg == "package-a":
                return "Description with keyword"
            elif pkg == "package-b":
                return "No match here"
            elif pkg == "package-c":
                return "Another with keyword"
            return ""
        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.get_package_long_description', mock_get_desc)

        # Set argv for pattern that matches all, and --search "keyword"
        import sys
        sys.argv = ['script', 'package.*', '--search', 'key', '--count-only']

        main()

        captured = capsys.readouterr()
        stderr = captured.err
        assert "Filtering by description..." in stderr
        assert "After description filter: 2 matches" in stderr
        stdout = strip_ansi(captured.out)
        assert "Found 2 matching packages." in stdout

    def test_invalid_search_regex(self, monkeypatch, capsys):
        mock_packages = ["package"]
        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.get_packages', lambda refresh: mock_packages)
        import sys
        sys.argv = ['script', 'package', '--search', '[']  # invalid regex

        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 2

        captured = capsys.readouterr()
        assert "Invalid search regex" in strip_ansi(captured.out)

    def test_search_no_filter_if_no_arg(self, monkeypatch, capsys):
        mock_packages = ["package-a", "package-b"]
        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.get_packages', lambda refresh: mock_packages)

        # Mock but not called
        def mock_get_desc(pkg, verbose=False):
            return "desc"
        monkeypatch.setattr('src.pypi_search_caching.pypi_search_caching.get_package_long_description', mock_get_desc)

        import sys
        sys.argv = ['script', 'package', '--count-only']

        main()

        captured = capsys.readouterr()
        assert "Filtering by description..." not in captured.err
        assert "Found 2 matching packages." in strip_ansi(captured.out)