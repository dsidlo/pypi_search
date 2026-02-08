import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
from io import StringIO
from requests.exceptions import RequestException
import re

from src.pypi_search import (
    main,
    get_packages,
    fetch_project_details,
    fetch_all_package_names,
    is_cache_valid,
    load_cached_packages,
    save_packages_to_cache,
    ensure_cache_dir,
    CACHE_FILE,
    CACHE_MAX_AGE_SECONDS,
)


def strip_ansi(text):
    import re
    return re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', text)

@pytest.fixture
def capsys_disabled(capfd):
    """Disable capfd for tests that don't use it."""

    pass

class TestCacheUtils:
    def test_ensure_cache_dir(self):
        from unittest.mock import patch
        mock_mkdir = patch.object(CACHE_DIR, 'mkdir')
        with mock_mkdir as m:
            ensure_cache_dir()
        m.assert_called_once_with(parents=True, exist_ok=True)

    def test_is_cache_valid_no_file(self):
        with patch.object(CACHE_FILE, 'exists', return_value=False):
            assert not is_cache_valid()

    def test_is_cache_valid_recent(self, monkeypatch):
        mock_stat = MagicMock()
        mock_stat.st_mtime = 0
        monkeypatch.setattr('time.time', lambda: 1000)
        monkeypatch.setattr(CACHE_FILE, 'exists', MagicMock(return_value=True))
        monkeypatch.setattr(CACHE_FILE, 'stat', lambda: mock_stat)
        assert is_cache_valid()

    def test_is_cache_valid_old(self, monkeypatch):
        mock_stat = MagicMock()
        mock_stat.st_mtime = 0
        monkeypatch.setattr('time.time', lambda: CACHE_MAX_AGE_SECONDS * 2)
        monkeypatch.setattr(CACHE_FILE, 'exists', MagicMock(return_value=True))
        monkeypatch.setattr(CACHE_FILE, 'stat', lambda: mock_stat)
        assert not is_cache_valid()

    def test_load_cached_packages(self, tmp_path):
        cache_path = tmp_path / "test.cache"
        cache_path.write_text("pkg1\npkg2\n\n\npkg3")
        with patch.object(CACHE_FILE, 'open', lambda *a, **k: open(cache_path)):
            pkgs = load_cached_packages()
        assert pkgs == ["pkg1", "pkg2", "pkg3"]

    def test_save_packages_to_cache(self, tmp_path):
        cache_path = tmp_path / "test.cache"
        with patch.object(CACHE_FILE, 'open', lambda *a, **k: open(cache_path, 'w')):
            save_packages_to_cache(["pkg2", "pkg1", "pkg3"])
        with open(cache_path) as f:
            content = f.read()
        assert content == "pkg1\npkg2\npkg3\n"

class TestFetchAllPackageNames:
    def test_success(self):
        html = '<html><a href="testpkg/">testpkg</a><a href="testpkg2/">testpkg2</a></html>'
        with patch('requests.get', return_value=MagicMock(text=html, status_code=200, raise_for_status=lambda: None)):
            pkgs = fetch_all_package_names()
        assert pkgs == ["testpkg", "testpkg2"]

    def test_network_error(self, caplog):
        with patch('requests.get', side_effect=RequestException("network")):
            with pytest.raises(SystemExit, match="1"):
                fetch_all_package_names()
        assert "Error downloading PyPI index" in caplog.text

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
        assert "**Classifiers:**\\n- License :: OSI Approved" in md
        assert "**Summary:** Test pkg" in md
        assert "**Description:**" in md

    def test_404(self):
        resp = MagicMock(status_code=404)
        with patch('requests.get', return_value=resp):
            assert fetch_project_details("nonexistent") is None

    def test_exception(self):
        with patch('requests.get', side_effect=RequestException()):
            assert fetch_project_details("test") is None

class TestGetPackages:
    def test_cache_valid(self):
        with patch('src.pypi_search.is_cache_valid', return_value=True), patch('src.pypi_search.load_cached_packages', return_value=["pkg1"]):
            pkgs = get_packages(refresh_cache=False)
        assert pkgs == ["pkg1"]

    def test_cache_invalid_refresh(self):
        with patch('src.pypi_search.is_cache_valid', return_value=False), patch('src.pypi_search.fetch_all_package_names', return_value=["pkg1"]), patch('src.pypi_search.save_packages_to_cache'):
            pkgs = get_packages(refresh_cache=True)
        assert pkgs == ["pkg1"]

class TestMain:
    @patch('src.pypi_search.get_packages')
    @patch('sys.exit')
    def test_invalid_regex(self, mock_exit, mock_get_packages, monkeypatch):
        monkeypatch.setattr(sys, 'argv', ['script', r'['])  # invalid regex
        main()
        mock_exit.assert_called_once_with(2)

    @patch('src.pypi_search.get_packages', return_value=[])
    def test_no_matches(self, mock_get, capsys):
        sys.argv = ['script', 'nonexistent']
        main()
        captured = capsys.readouterr()
        assert "No matching packages found." in strip_ansi(captured.out)

    @patch('src.pypi_search.get_packages', return_value=["pkg1", "pkg2"])
    def test_count_only(self, mock_get, capsys):
        sys.argv = ['script', '.', '--count-only']
        main()
        captured = capsys.readouterr()
        assert "Found 2 matching packages." in strip_ansi(captured.out)

    @patch('src.pypi_search.get_packages', return_value=["pkg1", "pkg2"])
    @patch('src.pypi_search.fetch_project_details', return_value="## testpkg\n**Version:** `1.0`")
    def test_list_with_desc(self, mock_details, mock_get, capsys):
        sys.argv = ['script', '.', '--desc']
        main()
        captured = capsys.readouterr()
        assert "pkg1" in captured.out
        assert "pkg2" in captured.out
        assert "**Version:** `1.0`" in strip_ansi(captured.out)
        assert "... and 0 more" not in captured.out  # <10

    @patch('src.pypi_search.get_packages', return_value=["pkg1"] * 15)
    @patch('src.pypi_search.fetch_project_details', return_value="MD")
    def test_list_with_desc_full(self, mock_details, mock_get, capsys):
        sys.argv = ['script', '.', '--desc', '--full-desc']
        main()
        captured = capsys.readouterr()
        assert "pkg1" in captured.out  # all printed
        assert "MD" in captured.out  # top 10
        assert "... and 5 more matches" in strip_ansi(captured.out)

# Run with pytest src/test/test_pypi_search.py --cov=src/pypi_search
