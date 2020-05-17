#!/bin/bash

set -eux

mypy .

# `python3` is unambiguous on Unix systems (blame PEP 394)
# but on Windows, Python 3 answers only to `python`
# NOTE W10 users must disable `python3` -> Windows store alias in settings / apps and features
if command -v python3 > /dev/null 2>&1; then
	PYTHONEXEC=python3
else
	PYTHONEXEC=python
fi

$PYTHONEXEC -W error -m unittest discover

flake8 --exit-zero
