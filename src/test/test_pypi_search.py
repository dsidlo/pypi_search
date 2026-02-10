import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
from io import StringIO
from requests.exceptions import RequestException
import re
import time
import os
from textwrap import dedent

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
    CACHE_DIR,
    CACHE_MAX_AGE_SECONDS,
    convert_rst_table,
    parse_simple_rst_list_table,
    rich_table_to_markdown,
    extract_raw_html_blocks,
    convert_rst_code_blocks,
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

class TestCacheUtils:
    def test_ensure_cache_dir(self, tmp_path, monkeypatch):
        test_cache_dir = tmp_path / ".cache" / "p"
        monkeypatch.setattr('src.pypi_search.CACHE_DIR', test_cache_dir)
        assert not test_cache_dir.exists()
        ensure_cache_dir()
        assert test_cache_dir.exists()

    def test_is_cache_valid_no_file(self, tmp_path, monkeypatch):
        test_cache_file = tmp_path / "test.cache"
        monkeypatch.setattr('src.pypi_search.CACHE_FILE', test_cache_file)
        # no write, so not exists
        assert not is_cache_valid()

    def test_is_cache_valid_recent(self, tmp_path, monkeypatch):
        test_cache_file = tmp_path / "test.cache"
        monkeypatch.setattr('src.pypi_search.CACHE_FILE', test_cache_file)
        now = time.time()
        monkeypatch.setattr('time.time', lambda: now)
        test_cache_file.write_text('')
        os.utime(str(test_cache_file), (now - 100, now - 100))
        assert is_cache_valid()

    def test_is_cache_valid_old(self, tmp_path, monkeypatch):
        test_cache_file = tmp_path / "test.cache"
        monkeypatch.setattr('src.pypi_search.CACHE_FILE', test_cache_file)
        now = time.time()
        monkeypatch.setattr('time.time', lambda: now)
        test_cache_file.write_text('')
        os.utime(str(test_cache_file), (now - CACHE_MAX_AGE_SECONDS * 2, now - CACHE_MAX_AGE_SECONDS * 2))
        assert not is_cache_valid()

    def test_load_cached_packages(self, tmp_path, monkeypatch):
        test_cache_file = tmp_path / "test.cache"
        monkeypatch.setattr('src.pypi_search.CACHE_FILE', test_cache_file)
        test_cache_file.write_text("pkg1\npkg2\n\n\npkg3")
        pkgs = load_cached_packages()
        assert pkgs == ["pkg1", "pkg2", "pkg3"]

    def test_save_packages_to_cache(self, tmp_path, monkeypatch):
        test_cache_file = tmp_path / "test.cache"
        monkeypatch.setattr('src.pypi_search.CACHE_FILE', test_cache_file)
        save_packages_to_cache(["pkg2", "pkg1", "pkg3"])
        assert test_cache_file.read_text() == "pkg1\npkg2\npkg3\n"

class TestFetchAllPackageNames:
    def test_success(self):
        html = '<html><a href="testpkg/">testpkg</a><a href="testpkg2/">testpkg2</a></html>'
        with patch('requests.get', return_value=MagicMock(text=html, status_code=200, raise_for_status=lambda: None)):
            pkgs = fetch_all_package_names()
        assert pkgs == ["testpkg", "testpkg2"]

    def test_network_error(self, capfd):
        with patch('requests.get', side_effect=RequestException("network")):
            with pytest.raises(SystemExit, match="1"):
                fetch_all_package_names()
        captured = capfd.readouterr()
        assert "Error downloading PyPI index" in captured.err

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

    @patch('src.pypi_search.get_packages', return_value=["pkg1", "pkg1"])
    def test_count_only(self, mock_get, capsys):
        sys.argv = ['script', 'pkg1', '--count-only']
        main()
        captured = capsys.readouterr()
        assert "Found 2 matching packages." in strip_ansi(captured.out)

    @patch('src.pypi_search.get_packages', return_value=["pkg1", "pkg1"])
    @patch('src.pypi_search.fetch_project_details', return_value="## testpkg\n**Version:** `1.0`")
    def test_list_with_desc(self, mock_details, mock_get, capsys):
        sys.argv = ['script', 'pkg1', '--desc']
        main()
        captured = capsys.readouterr()
        assert "pkg1" in captured.out
        assert "Version: 1.0" in strip_ansi(captured.out)
        assert "... and 0 more" not in captured.out  # <10

    @patch('src.pypi_search.get_packages', return_value=["pkg"] * 15)
    @patch('src.pypi_search.fetch_project_details', return_value="MD")
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
        with patch('tomllib.load') as mock_toml:
            mock_toml.return_value = {'project': {'name': 'pypi_search_caching', 'version': '0.0.2-Beta'}}
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 0
            captured = capsys.readouterr()
            assert captured.out.strip() == 'pypi_search_caching 0.0.2-Beta'

    def test_version_file_missing(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, 'argv', ['prog', '--version'])
        def mock_exit(code):
            raise SystemExit(code)
        monkeypatch.setattr('sys.exit', mock_exit)
        with patch('pathlib.Path.open', side_effect=FileNotFoundError):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 1
            captured = capsys.readouterr()
            assert 'pyproject.toml not found' in captured.err


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

# Run with pytest src/test/test_p.py --cov=src/p



