#!/usr/bin/env python3.10
"""
pip-search

Search PyPI package names by regex, with optional detailed description fetching.
Caches the repos module names every 23 hrs.

Usage:
    python pypi_search "pattern"
    python pypi_search "^aio" -d          # with details for first 10 matches
    python pypi_search "flask|django" --desc|-d --refresh-cache|-r

Installation:
    pip install pypi_search

Command installs to:
    <.venv|python_env_path>/bin

Cache dir:
    ~/.cache/pypi_search/pypi_search.cache
"""


import sys
import re
import argparse
import requests
import time
import os
from rich.console import Console
from rich.markdown import Markdown
from pathlib import Path
from bs4 import BeautifulSoup
from rich.theme import Theme
from rich.table import Table


os.environ['PAGER'] = 'less -R'

PYPI_SIMPLE_URL = "https://pypi.org/simple"
PYPI_JSON_URL = "https://pypi.org/pypi/{package_name}/json"
CACHE_DIR = Path.home() / ".cache" / "pypi_search"
CACHE_FILE = CACHE_DIR / "pypi_search.cache"
CACHE_MAX_AGE_SECONDS = 23 * 3600  # 23 hours

from pygments.style import Style
from pygments.token import Token

custom_theme = Theme({
    "markdown.code": "blue1 on #2d2d2d",
    "markdown.code_block": "on #2d2d2d",
})

class BrightBlueStyle(Style):
    """Custom Pygments style with light blue code on dark grey."""

    background_color = "#2d2d2d"  # dark grey background

    styles = {
        Token: '#87ceeb',  # light blue (sky blue) for default text
        Token.Keyword: 'bold #87ceeb',
        Token.Name: '#87ceeb',
        Token.String: '#add8e6',  # lighter blue for strings
        Token.Number: '#87ceeb',
        Token.Operator: '#87ceeb',
        Token.Comment: 'italic #6495ed',  # cornflower blue for comments
        Token.Punctuation: '#87ceeb',
    }


import html2text


def extract_raw_html_blocks(text):
    """Extract and convert raw:: html blocks to markdown."""
    pattern = r'\.\.\s+raw::\s+html\s*\n\s*\n((?:[ \t]+[^\n]*\n?)*)'

    def convert_html_block(match):
        html_content = match.group(1)
        lines = [line.lstrip() for line in html_content.split('\n') if line.strip()]
        html_content = '\n'.join(lines)

        if html_content.strip():
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.body_width = 0
            md_content = h.handle(html_content).strip()
            return f'{md_content}\n\n'
        return ''

    return re.sub(pattern, convert_html_block, text, flags=re.MULTILINE)


def convert_rst_code_blocks(text: str):
    re_lang = re.compile(r'^.. code-block::\s+(\S+)', flags=re.IGNORECASE)
    re_end_code_block = re.compile(r'^\S+')
    lines = ''
    in_cb = False  # In CodeBlock
    # For logic that stops generating an additional line at the top of a code-block
    cb_lns = 0
    for ln in text.splitlines():
        ln = ln.rstrip()
        if ln.startswith('.. code-block::'):
            lang = None
            if re_lang.match(ln):
                lang = re_lang.match(ln).group(1)
            if lang is None:
                lang = 'Code'
            ln = f"```{lang}"
            in_cb = True  # In CodeBlock
        elif re_end_code_block.match(ln) and in_cb:
            ln = f'```\n{ln}'
            in_cb = False # Out of CodeBlock
            cb_lns = 0
        if in_cb and cb_lns == 0:
            lines += ln + '\n'
            cb_lns += 1
        else:
            lines += ln + '\n'
    if in_cb:
        lines += '```\n'
    return lines


def convert_rst_table(text: str, console: Console = None) -> str:
    re_table = re.compile(r'^.. list-table::', flags=re.IGNORECASE | re.MULTILINE)
    lines_out = []
    i = 0
    text_lines = text.splitlines()
    while i < len(text_lines):
        ln = text_lines[i]
        if re_table.match(ln):
            # Start collecting table block
            table_block = [ln]
            i += 1
            while i < len(text_lines):
                next_ln = text_lines[i]
                stripped = next_ln.lstrip()
                if stripped.startswith(':header-rows:'):
                    table_block.append(next_ln)
                    i += 1
                    continue
                if stripped and not stripped.startswith('*') and next_ln.strip() and not next_ln.startswith('  '):
                    break
                table_block.append(next_ln)
                i += 1
            # Parse the table block
            table_text = '\n'.join(table_block)
            md_table = parse_simple_rst_list_table(table_text)
            lines_out.append(rich_table_to_markdown(md_table, console=console))
        else:
            lines_out.append(ln)
            i += 1
    return '\n'.join(lines_out)




def parse_simple_rst_list_table(text: str) -> Table:
    lines = text.splitlines()

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan", no_wrap=False)
    table.add_column("Description", style="green")

    current_row = []

    for line in lines:
        stripped = line.lstrip()
        if not stripped:
            continue
        if stripped.startswith("* -"):
            if current_row:
                table.add_row(*current_row)
            current_row = []
            content = stripped[3:].lstrip().strip()
            # Link conversion
            if content.startswith("`") and "<" in content and ">`_" in content:
                parts = content.strip("`").rsplit("<", 1)
                if len(parts) == 2:
                    text_part = parts[0].strip()
                    url = parts[1].rstrip(">`_").strip()
                    content = f"[{text_part}]({url})"
            current_row.append(content)
        elif stripped.startswith("-"):
            content = stripped[1:].lstrip().strip()
            # Link conversion
            if content.startswith("`") and "<" in content and ">`_" in content:
                parts = content.strip("`").rsplit("<", 1)
                if len(parts) == 2:
                    text_part = parts[0].strip()
                    url = parts[1].rstrip(">`_").strip()
                    content = f"[{text_part}]({url})"
            current_row.append(content)
        elif current_row:
            # Multi-line cell continuation
            current_row[-1] += " " + stripped
    if current_row:
        table.add_row(*current_row)

    return table


def rich_table_to_markdown(table: Table, console: Console = None) -> str:
    if console is None:
        console = Console()  # fallback – better to pass your real console

    if not table.columns:
        return ""

    # Headers (using public .header)
    headers = []
    for col in table.columns:
        header_text = console.render_str(str(col.header)).plain.strip()
        headers.append(header_text)

    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")

    # Consume generators into lists
    cells_by_col = [list(col.cells) for col in table.columns]
    n_rows = min(len(cells) for cells in cells_by_col) if cells_by_col else 0

    for row_idx in range(n_rows):
        row_cells = []
        for j, col in enumerate(table.columns):
            cell = cells_by_col[j][row_idx]
            plain = console.render_str(str(cell)).plain.strip()
            plain = plain.replace("|", "\\|")  # escape markdown pipes
            row_cells.append(plain or "-")
        lines.append("| " + " | ".join(row_cells) + " |")

    return "\n".join(lines)


def ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def is_cache_valid():
    if not CACHE_FILE.exists():
        return False
    mtime = CACHE_FILE.stat().st_mtime
    age = time.time() - mtime
    return age < CACHE_MAX_AGE_SECONDS


def load_cached_packages():
    with CACHE_FILE.open("r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def save_packages_to_cache(packages):
    with CACHE_FILE.open("w", encoding="utf-8") as f:
        for pkg in sorted(packages):
            f.write(pkg + "\n")


def fetch_all_package_names():
    url = PYPI_SIMPLE_URL
    print("Fetching fresh PyPI package index... (may take a few seconds)", file=sys.stderr)

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Error downloading PyPI index: {e}", file=sys.stderr)
        sys.exit(1)

    soup = BeautifulSoup(resp.text, "html.parser")
    packages = []

    for link in soup.find_all("a"):
        name = link.get_text(strip=True).rstrip("/")
        if name:
            packages.append(name)

    print(f"Found {len(packages):,} package names.", file=sys.stderr)
    return packages


def get_packages(refresh_cache):
    ensure_cache_dir()
    if is_cache_valid() and not refresh_cache:
        packages = load_cached_packages()
        print(f"Using cache: {len(packages):,} pkgs (age < 23h)", file=sys.stderr)
        return packages
    else:
        packages = fetch_all_package_names()
        save_packages_to_cache(packages)
        print(f"Cache updated: {len(packages):,} pkgs.", file=sys.stderr)
        return packages


def fetch_project_details(package_name, console=None, include_desc=False):
    url = PYPI_JSON_URL
    # Use a regexp to change '{package_name}' to the value in package_name.
    url = re.sub(r'\{package_name\}', package_name, url)
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return None

    info = data.get('info', {})
    md_parts = [f"## {package_name}"]
    md_parts.append(f"**Version:** `{info.get('version', 'N/A')}`")
    md_parts.append(f"**Requires Python:** {info.get('requires_python', 'N/A')}")
    homepage = info.get('home_page')
    if homepage:
        md_parts.append(f"**Homepage:** [{homepage}]({homepage})")
    project_urls = info.get('project_urls', {})
    release_url = info.get('release_url') or project_urls.get('Download URL') or project_urls.get('Source')
    if release_url:
        md_parts.append(f"**Release:** [{release_url}]({release_url})")
    bug_tracker = None
    if project_urls:
        bug_tracker = project_urls.get('Bug Tracker')
    if bug_tracker:
        md_parts.append(f"**Bug Tracker:** [{bug_tracker}]({bug_tracker})")
    classifiers = info.get('classifiers', [])
    if classifiers:
        clf_md = '\n'.join([f'- {c}' for c in classifiers[:15]])
        md_parts.append(f"**Classifiers:**\n{clf_md}")
    summary = info.get('summary', '')
    if summary:
        md_parts.append(f"**Summary:** {summary}")
    if include_desc:
        long_desc = info.get('description', '')
        if long_desc:
            long_desc = convert_rst_table(long_desc, console)
            long_desc = extract_raw_html_blocks(long_desc)
            md_parts.append(f"**Full Description:**\n{long_desc}...")
    return '\n\n'.join(md_parts)


def main():
    parser = argparse.ArgumentParser(description="Search PyPI packages by regex")
    parser.add_argument("pattern", help="Regular expression to match package names")
    parser.add_argument("-i", "--ignore-case", action="store_true", default=False,
                        help="Case-insensitive matching (default: on)")
    parser.add_argument("--desc", "-d", action="store_true",
                        help="Fetch and show detailed info for first 10 matches")
    parser.add_argument("--count-only", action="store_true",
                        help="Only show count of matches")
    parser.add_argument("--refresh-cache", "-r", action="store_true",
                        help="Refresh the PyPi cache now. Happens before search.")
    parser.add_argument("--full-desc", "-f", action="store_true",
                        help="Include full description in details (with -d)")

    # Max number of descriptions fetched...
    max_desc = 10

    args = parser.parse_args()
    # console = Console(force_terminal=True, theme=custom_theme)
    console = Console(force_terminal=True, theme=custom_theme, color_system="truecolor")

    with console.pager(styles=True):

        # Validate the incoming regexp
        try:
            flags = re.IGNORECASE if args.ignore_case else 0
            # Strip '"' & '"' from args.pattern
            args.pattern = args.pattern.strip('"').strip("'")
            regex = re.compile(f"^{args.pattern}$", flags)
        except re.error as e:
            console.print(f"[red][bold]\nThe Regular Expression Pattern is Invalid:[/bold][/red]\n" +
                          f"  [yellow]- {e}[/yellow]\n")
            sys.exit(2)

        all_packages = get_packages(args.refresh_cache)

        if args.refresh_cache and args.pattern == "":
            return

        matches = [pkg for pkg in all_packages if regex.search(pkg)]

        if args.count_only:
            console.print(f"Found {len(matches):,} matching packages.")
            return

        if not matches:
            console.print("No matching packages found.")
            return

        console.print(f"[bold cyan]Found {len(matches):,} matches![/bold cyan]\n")

        for i, pkg in enumerate(matches, 1):
            if len(pkg) > 50:
                # Snip junk files...
                pkg = pkg[:50] + "..."
            if i > max_desc and args.desc:
                console.print(f"[red] *** Max Descriptions Reached. *** [/red]")
                break
            if args.desc:
                # String of i space padded to 4 digits
                console.rule(f"[cyan]{i}.[/] [bold]{pkg}[/bold]")
                details_md = fetch_project_details(pkg, console=console, include_desc=args.full_desc)
                if details_md:
                    # Filter out '.. image::' from details_md
                    details_md = '\n'.join([line for line in details_md.split('\n')
                                            if not (line.startswith('.. image::')     or
                                                    line.startswith('   :height: ')   or
                                                    line.startswith('   :width: ')    or
                                                    line.startswith('   :alt: ')      or
                                                    line.startswith(':raw-html-m2r:') or
                                                    line.startswith('   :target: ')   or
                                                    line == '|')])
                    details_md = re.sub(
                        r'\\?\s*:raw-html-m2r:\s*(`[^`]+`)\\?\s*',
                        r'\1',
                        details_md,
                        flags=re.MULTILINE
                    )
                    details_md = re.sub(r'`<br>`', r'\n\n', details_md, flags=re.MULTILINE)
                    details_md = re.sub(r'#.', r'*', details_md, flags=re.MULTILINE)
                    details_md = re.sub(r'\\ ', r' ', details_md, flags=re.MULTILINE)
                    details_md = re.sub(r'(^\.\.\s+([^:]+\:)\s+(https?://[^\s]+))', r' - \2 `\3`', details_md, flags=re.MULTILINE)
                    details_md = re.sub(r'<#', r'<\#', details_md, flags=re.MULTILINE)
                    details_md = re.sub(r'>_', r'>', details_md, flags=re.MULTILINE)
                    details_md = re.sub(r'>`_', r'>`', details_md, flags=re.MULTILINE)
                    details_md = re.sub(r"` (?=\W)", r"`", details_md, flags=re.MULTILINE)
                    md = Markdown(details_md, code_theme=BrightBlueStyle)
                    console.print(md)
            else:
                console.print(f"[cyan]{i:>6}.[/] [bold]{pkg}[/bold]")

        if len(matches) > max_desc and args.desc:
            console.print(f"... and {len(matches) - max_desc} more matches")

        console.print(f"\n[bold]Total: {len(matches):,}[/bold]")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please provide a regex pattern.", file=sys.stderr)
        sys.exit(1)
    main()
