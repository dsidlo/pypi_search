#!/usr/bin/env bash

echo ">>>> Seting up uv dev Environment"
uv sync --dev
if [ $? != 0 ]; then
  echo "*** 'uv sync --dev' failed!"
  exit 1
fi

echo ">>>> Build package..."
uv build
if [ $? != 0 ]; then
  echo "*** 'uv build' failed!"
  exit 1
fi

# Uninstall if exists
echo ">>>> Uninstall package if exists..."
pip uninstall -y pypi-search-caching || true

# Install wheel (glob for latest)
echo ">>>> Looing for $WHEEL_FILE in dist/"
WHEEL_FILE=$(ls dist/pypi_search_caching-*.whl | head -1)
if [ -z "$WHEEL_FILE" ]; then
  echo "*** No wheel found in dist/!"
  exit 1
fi
echo ">>>> Installing wheel: pip install '$WHEEL_FILE'"
uv pip install "$WHEEL_FILE"
if [ $? != 0 ]; then
  echo "*** Uninstall failed!"
  exit 1
fi

# Verify installation (no .pth, proper path)
echo ">>>> Verify installation (no .pth, proper path)"
python -c "
import pypi_search_caching
print('Module installed at:', pypi_search_caching.__file__)
import site
site_packages = site.getsitepackages()
pth_files = [f for f in site_packages if '.pth' in str(f) and 'pypi_search_caching' in str(f).lower()]
print('PTH files found:', pth_files)
if pth_files:
  print('WARNING: .pth files detected - not a clean install!')
  exit(1)
else:
  print('Clean installation confirmed.')
"

# Validate script placement
echo ">>>> Validating script placement"
cmd_path=$(which pypi_search)
if [ ! -f "$cmd_path" ]; then
  echo "*** Console script not found in bin/pypi_search!"
  exit 1
fi
echo "Console script placed correctly at bin/pypi_search"
echo " - $cmd_path"

# Test run (--version)...
echo -n ">>>> Testing Version: $cmd_path --version"
$cmd_path --version
if [ $? != 0 ]; then
  echo "*** Version test failed!"
  exit 1
fi

# Test help (-n)...
echo ">>>> Testing Help: $cmd_path -h"
$cmd_path -h
if [ $? != 0 ]; then
  echo "*** Help test failed!"
  exit 1
fi

echo ">>>> Uninstalling package: uv pip uninstall '$WHEEL_FILE'"
uv pip uninstall "$WHEEL_FILE"
if [ $? != 0 ]; then
  echo "*** Uninstall failed!"
  exit 1
fi

echo "**** Build-Run Test Passed! Proper installation confirmed."

