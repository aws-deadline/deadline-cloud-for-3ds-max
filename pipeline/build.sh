#!/bin/sh
# Set the -e option
set -e

pip install --upgrade pip
pip install --upgrade hatch "click<8.3" "virtualenv<21"
pip install --upgrade twine
hatch run lint
hatch run test
hatch build