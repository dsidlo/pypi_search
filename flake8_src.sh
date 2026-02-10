#!/usr/bin/env bash

echo "=========================="
echo "Loading uv dev Environment"
echo "=========================="
uv sync --dev
echo

# Scan for critical errors...
echo "================================"
echo "Scan for Critical Errors..."
echo "================================"
echo -n "Critical Errors: "
.venv/bin/flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics
err=$?
if [ $err != 0 ]; then
  echo "flake8 Found Critical Errors. Exiting."
  exit 1
else
  echo
  echo "================================"
  echo "flake8 Found No Critical Errors."
  echo "================================"
  echo
fi

echo "================================"
echo "Standards and Complexity Report"
echo "================================"
# Examine Code Complexity and simply report it...
.venv/bin/flake8 src --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

