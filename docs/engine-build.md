# Building the engine from source

The kit's prebuilt `DolmexicaInfinite.self` can't be changed (patching a SELF breaks it,
`handoff/CLAUDE.md` rule 9). `tools/engine/build_vita.sh` rebuilds it from
`source/dolmexica-src` (fetched by `tools/fetch_sources.py`, 1.8 release commits) and applies
our changes from `tools/engine/patches/` on top. The source tree itself is never edited.

## One-time setup (Windows, ~2.5 GB)

```bash
wsl --install -d Ubuntu --no-launch
wsl -d Ubuntu -u root -- bash -c "apt-get update && apt-get install -y make git cmake python3 curl wget bzip2 xz-utils build-essential"
wsl -d Ubuntu -u root -- bash -c "git clone --depth 1 https://github.com/vitasdk/vdpm /opt/vdpm && cd /opt/vdpm && ./bootstrap-vitasdk.sh"
wsl -d Ubuntu -u root -- bash -lc "export VITASDK=/usr/local/vitasdk PATH=/usr/local/vitasdk/bin:\$PATH; vdpm install libvita2d libmikmod libvorbis libogg libpng libjpeg-turbo libwebp flac zlib zstd taihen libmathneon libtremor"
```

`vdpm`'s `install-all.sh` fails with "package client is not executable: …/bin/pacman" on the
2026.08 SDK; installing the packages above by name works.

## Build

From the repo root (as seen from WSL):

```bash
wsl -d Ubuntu -u root -- bash -c "cd /mnt/c/Users/<you>/mugen-trial && bash tools/engine/build_vita.sh"
#   --debug     engine log on (needed to read memory/texture messages on the Vita)
#   --heap 144  newlib heap in MB (T6), default 96
#   --stock     plain 1.8 engine, no patches
```

The output is `build/engine/DolmexicaInfinite.self` plus `build-info.txt`, which lists the commits,
the SDK, the options and the patches applied. A full build takes about a minute. Package it with:

```bash
.venv/Scripts/python.exe tools/make_vpk.py --self build/engine/DolmexicaInfinite.self
```

## Things the script works around (current VitaSDK vs. the 2026-09 release)

| Problem | Fix in `build_vita.sh` |
|---|---|
| `drakonsound` isn't a VitaSDK package | It's CaptainDreamcast/VitaSound, branch `Feature/LibraryConversion` (`1da3f25`), per the engine author. Cloned into `source/dolmexica-src/vitasound` |
| GCC 15 turns VitaSound's pointer-type warnings into errors | `-Wno-error=incompatible-pointer-types` (and two more) for that library only |
| CMake 4 rejects `cmake_minimum_required(2.8)` | `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| `libgpu_es4_ext_stub_weak` no longer exists | Dropped from the link. Nothing in the engine calls it |
| `pthread_*` undefined | Static libs listed after `pthread` need it too; it's linked again at the end |

## Patches

| Patch | What |
|---|---|
| `0001-vita-p8-per-sprite-palettes.patch` | 8-bit sprites with their own palette stay `P8` textures (1 B/px) with a shared, reference-counted per-sprite palette, instead of being expanded to ARGB32 (4 B/px). Fix A in `reports/vita-memory.md`: about 4× less texture memory for the AK1 characters. Colours go through the same `setPaletteFrom*` functions as the engine's normal palettes. |
