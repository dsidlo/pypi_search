#!/usr/bin/env bash

uv sync
uv pip compile pyproject.toml -o requirements.txt
uv sync --dev
uv pip compile pyproject.toml -o requirements-dev.txt

