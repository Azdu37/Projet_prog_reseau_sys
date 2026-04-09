#!/bin/bash
set -e

# 1. Build C process if needed
(cd c_network && make build/network)

# 2. Python will handle starting the C process via subprocess in main.py
# So we just run Python.

python3 p_game/main.py "$@"