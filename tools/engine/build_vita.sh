#!/bin/bash
# build_vita.sh -- build Dolmexica Infinite (Vita .self) from source/dolmexica-src.
#
# Runs inside WSL Ubuntu with VitaSDK installed at /usr/local/vitasdk:
#     wsl -d Ubuntu -u root -- bash tools/engine/build_vita.sh [--debug] [--heap MB]
#   (run from the repo root as seen from WSL, e.g. /mnt/c/Users/<you>/mugen-trial)
#
#   --debug     log at LOG_TYPE_NORMAL instead of NONE (repo/main.cpp:62-68), so the
#               engine's memory/texture-slab messages are written on the Vita
#   --heap MB   newlib heap size (repo/main.cpp:40, default 96)
#   --stock     don't apply tools/engine/patches/*.patch (plain 1.8 engine)
#
# Steps: copy sources to a Linux-side work dir (case-sensitive, fast, CRLF -> LF),
# build libdrakonsound.a (CaptainDreamcast/VitaSound, branch Feature/LibraryConversion,
# the library Dolmexica 1.8 links as "drakonsound"), apply our engine patches
# (tools/engine/patches/*.patch, in name order), build libprism.a, then the engine.
# Output: build/engine/DolmexicaInfinite.self (+ build-info.txt). Sources are not modified.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$REPO/source/dolmexica-src"
OUT="$REPO/build/engine"
WORK=/root/dolmexica-build
export VITASDK=/usr/local/vitasdk
export PATH="$VITASDK/bin:$PATH"

DEBUG=0
HEAP=96
PATCHES=1
while [ $# -gt 0 ]; do
  case "$1" in
    --debug) DEBUG=1 ;;
    --heap) HEAP="$2"; shift ;;
    --stock) PATCHES=0 ;;
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac
  shift
done

VITASOUND_URL=https://github.com/CaptainDreamcast/VitaSound
VITASOUND_REF=1da3f25cd3b3642ce111dd8663b7dab6f967f94f   # Feature/LibraryConversion
if [ ! -d "$SRC/vitasound" ]; then
  git clone -q -b Feature/LibraryConversion "$VITASOUND_URL" "$SRC/vitasound"
fi

echo "== copy sources -> $WORK"
rm -rf "$WORK"
mkdir -p "$WORK"
for d in repo prism vitasound; do
  tar -C "$SRC" --exclude=.git -cf - "$d" | tar -C "$WORK" -xf -
done
# Makefiles/CMakeLists/sources come with CRLF from Windows checkouts
find "$WORK" -type f \( -name 'Makefile*' -o -name 'CMakeLists.txt' -o -name 'CmakeLists.txt' -o -name '*.cmake' \
  -o -name '*.c' -o -name '*.cpp' -o -name '*.h' \) -exec sed -i 's/\r$//' {} +

APPLIED=""
if [ "$PATCHES" = 1 ]; then
  for patch in "$REPO"/tools/engine/patches/*.patch; do
    [ -e "$patch" ] || continue
    echo "== patch $(basename "$patch")"
    sed 's/\r$//' "$patch" | patch -s -d "$WORK" -p1 --no-backup-if-mismatch
    APPLIED="$APPLIED $(basename "$patch")"
  done
fi

echo "== engine options: heap ${HEAP} MB, debug log ${DEBUG}"
sed -i "s/_newlib_heap_size_user = [0-9]* \* 1024 \* 1024;/_newlib_heap_size_user = ${HEAP} * 1024 * 1024;/" "$WORK/repo/main.cpp"
grep -q "_newlib_heap_size_user = ${HEAP} \* 1024 \* 1024;" "$WORK/repo/main.cpp"
if [ "$DEBUG" = 1 ]; then
  sed -i 's/^\tsetMinimumLogType(LOG_TYPE_NONE);/\tsetMinimumLogType(LOG_TYPE_NORMAL);/' "$WORK/repo/main.cpp"
  grep -q "^	setMinimumLogType(LOG_TYPE_NORMAL);" "$WORK/repo/main.cpp"
fi

JOBS=$(nproc)
echo "== libdrakonsound"
# GCC 14+ made these C diagnostics errors by default; VitaSound predates that
C_COMPAT="-Wno-error=incompatible-pointer-types -Wno-error=int-conversion -Wno-error=implicit-function-declaration"
make -C "$WORK/vitasound" -j"$JOBS" CFLAGS="-Wl,-q -O2 -std=c99 -I./Nogg -I./include $C_COMPAT" >/dev/null 2>"$WORK/vitasound.log" \
  || { tail -30 "$WORK/vitasound.log"; exit 1; }

echo "== libprism"
make -C "$WORK/prism" -f Makefile.vita -j"$JOBS" >/dev/null 2>"$WORK/prism.log" \
  || { grep -E "error" "$WORK/prism.log" | head -30; exit 1; }

echo "== Dolmexica Infinite"
# libgpu_es4_ext_stub_weak is not in current VitaSDK and nothing in the engine calls it
sed -i '/libgpu_es4_ext_stub_weak/d' "$WORK/repo/vita/CmakeLists.txt"
mv "$WORK/repo/vita/CmakeLists.txt" "$WORK/repo/vita/CMakeLists.txt"
# only the .self is needed: drop the vpk step (the project packages its own vpk)
sed -i '/^vita_create_vpk(/,/^)/d' "$WORK/repo/vita/CMakeLists.txt"
# with current VitaSDK the static libs listed after pthread (zstd, drakonsound...) also need it:
# link it again at the end
echo 'target_link_libraries(${PROJECT_NAME} pthread)' >> "$WORK/repo/vita/CMakeLists.txt"
cmake -S "$WORK/repo/vita" -B "$WORK/repo/vita/build" -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 >/dev/null
cmake --build "$WORK/repo/vita/build" -j"$JOBS" >"$WORK/engine.log" 2>&1 \
  || { grep -E "error|undefined reference" "$WORK/engine.log" | sort | uniq -c | sort -rn | head -30; exit 1; }

mkdir -p "$OUT"
cp "$WORK/repo/vita/build/DolmexicaInfinite.self" "$OUT/"
{
  echo "built: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "dolmexica: $(git -C "$SRC/repo" rev-parse --short HEAD 2>/dev/null || echo ?)"
  echo "prism: $(git -C "$SRC/prism" rev-parse --short HEAD 2>/dev/null || echo ?)"
  echo "vitasound: $(git -C "$SRC/vitasound" rev-parse --short HEAD 2>/dev/null || echo ?) (want ${VITASOUND_REF:0:7})"
  echo "vitasdk: $(head -1 "$VITASDK/version_info.txt" 2>/dev/null || echo ?)"
  echo "gcc: $(arm-vita-eabi-gcc --version | head -1)"
  echo "heap_mb: $HEAP"
  echo "debug_log: $DEBUG"
  echo "patches:${APPLIED:- none}"
  echo "self_bytes: $(stat -c %s "$OUT/DolmexicaInfinite.self")"
} > "$OUT/build-info.txt"
cat "$OUT/build-info.txt"
