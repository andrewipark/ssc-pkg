#!/bin/bash
set -eux
mypy ssc_pkg
mypy test
# for some reason "python" on Windows
python3 -m unittest discover || python -m unittest discover
flake8 --exit-zero ssc_pkg
flake8 --exit-zero test

