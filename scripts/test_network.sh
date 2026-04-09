#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== Build C IPC test =="
make -C "$ROOT_DIR/c_network"

echo "== Cleanup old IPC objects =="
"$ROOT_DIR/c_network/mbai_ipc_test" cleanup || true
python3 "$ROOT_DIR/p_game/network_bridge.py" cleanup || true

echo "== Test 1: C -> Python =="
"$ROOT_DIR/c_network/mbai_ipc_test" write-demo
python3 "$ROOT_DIR/p_game/network_bridge.py" read

echo "== Test 2: Python -> C =="
python3 "$ROOT_DIR/p_game/network_bridge.py" write-demo
"$ROOT_DIR/c_network/mbai_ipc_test" read

echo "== Final cleanup =="
"$ROOT_DIR/c_network/mbai_ipc_test" cleanup || true

echo "All IPC tests completed."
