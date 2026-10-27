#!/bin/bash
# run.sh -- build and run the Legends rules tests. Run from the repo root (WSL or any shell with g++):
#     python tools/legends/make_legends.py --no-art && bash tools/legends/tests/run.sh
set -euo pipefail
OUT=build/legends-tests
mkdir -p "$OUT"
g++ -std=c++17 -O1 -Wall -Wextra -o "$OUT/test_legendscore" tools/legends/tests/test_legendscore.cpp tools/legends/engine/legendscore.cpp
"$OUT/test_legendscore"
