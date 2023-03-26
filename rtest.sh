#!/bin/bash

set -eux

mypy --exclude build .

# `python3` is unambiguous on Unix systems (blame PEP 394)
# but on Windows, Python 3 answers only to `python`
# NOTE W10 users must disable `python3` -> Windows store alias in settings / apps and features
if command -v python3 > /dev/null 2>&1; then
	PYTHONEXEC=python3
else
	PYTHONEXEC=python
fi

$PYTHONEXEC -W error -m unittest discover

time flake8

if command -v ruff > /dev/null 2>&1; then
	time ruff check .
fi
