#!/bin/bash

set -eux

mypy ssc_pkg test
# name of python binary varies thanks to PEP 394 (also see https://lwn.net/Articles/780737/)
# try 'python3' to be completely unambiguous on Unix systems, but windows cygwin only does 'python'.
if command -v python3 > /dev/null 2>&1; then
	python3 -m unittest discover
else
	python -m unittest discover
fi

flake8 --exit-zero ssc_pkg test