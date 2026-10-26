"""
fetch_sources.py -- download and unpack everything the build needs that is NOT in the repo
(the repo is public; third-party files are fetched locally instead of committed).

    python tools/fetch_sources.py

Gets, into downloads/ then engine/ and source/:
  - Dolmexica Infinite 1.8 (itch.io, MIT)          -> engine/Dolmexica Infinite 1.8
  - TBM Last Beta demo (MediaFire, 719 MB)        -> source/demo
  - TBM 1.1 screenpack (MediaFire, 97 MB)         -> source/screenpack
  - Dolmexica + prism source (GitHub)             -> source/dolmexica-src (reference only)
Windows executables/libraries inside the TBM archives are never extracted.
Re-running skips anything already present.
"""

import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
import http.cookiejar
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DL = os.path.join(ROOT, "downloads")
UA = {"User-Agent": "Mozilla/5.0"}
TAR = r"C:\Windows\System32\tar.exe"
SKIP = (".exe", ".dll", ".bat", ".scr", ".vbs", ".ps1")  # .cmd is a MUGEN command file: keep

MEDIAFIRE = {
    "TBM_demo.7z": "https://www.mediafire.com/file/gvbx2eevvk5ahgj/TBM_Last_Beta(Screenpack).7z/file",
    "TBM_screenpack.rar": "https://www.mediafire.com/file/2xz0qqzq4h31zfx/TBM_1.1_2020.rar/file",
}


def get(url, opener=None, data=None):
    req = urllib.request.Request(url, data=data, headers=UA)
    return (opener or urllib.request.build_opener()).open(req)


def save(resp, path):
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        while chunk := resp.read(1 << 20):
            f.write(chunk)
    os.replace(tmp, path)


def fetch_dolmexica():
    out = os.path.join(DL, "Dolmexica_Infinite_1.8.zip")
    if not os.path.exists(out):
        jar = http.cookiejar.CookieJar()
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        page = get("https://captaindreamcast.itch.io/dolmexica-infinite", op).read().decode("utf-8", "replace")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
        upload = re.search(r'data-upload_id="(\d+)"', page).group(1)
        body = urllib.parse.urlencode({"csrf_token": csrf}).encode()
        url = json.load(get(f"https://captaindreamcast.itch.io/dolmexica-infinite/file/{upload}?source=view_game&as_props=1", op, body))["url"]
        print("downloading Dolmexica Infinite 1.8 ...")
        save(get(url), out)
    dst = os.path.join(ROOT, "engine")
    if not os.path.isdir(os.path.join(dst, "Dolmexica Infinite 1.8")):
        zipfile.ZipFile(out).extractall(dst)


def fetch_mediafire(name, page_url):
    out = os.path.join(DL, name)
    if os.path.exists(out):
        return out
    page = get(page_url).read().decode("utf-8", "replace")
    direct = re.search(r'href="(https://download\d*\.mediafire\.com/[^"]+)"', page).group(1)
    print(f"downloading {name} ...")
    save(get(direct), out)
    return out


def extract_7z(src, dst):
    import py7zr
    with py7zr.SevenZipFile(src) as z:
        names = [n for n in z.getnames() if not n.lower().endswith(SKIP)]
    with py7zr.SevenZipFile(src) as z:
        z.extract(path=dst, targets=names)


def main():
    os.makedirs(DL, exist_ok=True)
    fetch_dolmexica()
    demo = fetch_mediafire("TBM_demo.7z", MEDIAFIRE["TBM_demo.7z"])
    sp = fetch_mediafire("TBM_screenpack.rar", MEDIAFIRE["TBM_screenpack.rar"])
    if not os.path.isdir(os.path.join(ROOT, "source", "demo")):
        print("extracting demo ...")
        extract_7z(demo, os.path.join(ROOT, "source", "demo"))
    spd = os.path.join(ROOT, "source", "screenpack")
    if not os.path.isdir(spd):
        os.makedirs(spd)
        excl = sum([["--exclude", f"*{e}"] for e in SKIP], [])
        subprocess.run([TAR, "-xf", sp] + excl, cwd=spd, check=True)
    src = os.path.join(ROOT, "source", "dolmexica-src")
    os.makedirs(src, exist_ok=True)
    for name, repo in (("repo", "CaptainDreamcast/DolmexicaInfinite"), ("prism", "CaptainDreamcast/prism")):
        if not os.path.isdir(os.path.join(src, name)):
            subprocess.run(["git", "clone", "-q", "--depth", "1", f"https://github.com/{repo}", name], cwd=src, check=True)
    print("sources ready")


if __name__ == "__main__":
    sys.exit(main())
