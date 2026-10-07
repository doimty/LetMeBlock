#!/usr/bin/env python3
"""Prepare pinned build inputs. Extract data only; never install/run a deb."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    subprocess.run(args, check=True)


def download(url, digest, path):
    run("curl", "--fail", "--location", "--silent", "--show-error", "--retry", "3",
        url, "--output", str(path))
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError(f"SHA-256 mismatch: {path.name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theos", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    theos, work = args.theos.resolve(), args.work.resolve()
    manifest = json.loads((ROOT / "ci/dependencies.json").read_text())
    work.mkdir(parents=True, exist_ok=True)
    # The required historical SHA need not be reachable in a default shallow clone.
    run("git", "init", str(theos))
    run("git", "-C", str(theos), "remote", "add", "origin", manifest["theos"]["repository"])
    run("git", "-C", str(theos), "fetch", "--depth=1", "origin", manifest["theos"]["commit"])
    run("git", "-C", str(theos), "checkout", "--detach", "FETCH_HEAD")
    actual = subprocess.check_output(["git", "-C", str(theos), "rev-parse", "HEAD"], text=True).strip()
    if actual != manifest["theos"]["commit"]:
        raise ValueError("Theos revision mismatch")
    run("git", "-C", str(theos), "submodule", "update", "--init", "--recursive", "--depth=1")

    sdk = work / "iPhoneOS16.5.sdk.tar.xz"
    download(manifest["sdk"]["url"], manifest["sdk"]["sha256"], sdk)
    (theos / "sdks").mkdir(exist_ok=True)
    run("tar", "-xJf", str(sdk), "-C", str(theos / "sdks"))

    sandy = manifest["libsandy"]
    deb = work / "libsandy.deb"
    download(sandy["url"], sandy["sha256"], deb)
    if deb.stat().st_size != sandy["size"]:
        raise ValueError("libSandy archive size mismatch")
    for field, key in (("Package", "package"), ("Version", "version"), ("Architecture", "architecture")):
        value = subprocess.check_output(["dpkg-deb", "-f", str(deb), field], text=True).strip()
        if value != sandy[key]:
            raise ValueError(f"libSandy {field} mismatch")
    # Read one regular file directly from data.tar: no control extraction or scripts.
    data = subprocess.check_output(["dpkg-deb", "--fsys-tarfile", str(deb)])
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        matches = [m for m in archive if m.name in ("./usr/lib/libsandy.dylib", "usr/lib/libsandy.dylib")]
        if len(matches) != 1 or not matches[0].isfile():
            raise ValueError("missing/ambiguous prebuilt libSandy library")
        library = archive.extractfile(matches[0]).read()
    libdir = theos / "lib/iphone/roothide"
    libdir.mkdir(parents=True, exist_ok=True)
    (libdir / "libsandy.dylib").write_bytes(library)
    download(sandy["header_url"], sandy["header_sha256"], theos / "include/libSandy.h")
    download(sandy["license_url"], sandy["license_sha256"], work / "libSandy.LICENSE")
    manifest["libsandy"]["dylib_sha256"] = hashlib.sha256(library).hexdigest()
    manifest["theos"]["submodules"] = subprocess.check_output(
        ["git", "-C", str(theos), "submodule", "status", "--recursive"], text=True).splitlines()
    (work / "build-inputs.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
