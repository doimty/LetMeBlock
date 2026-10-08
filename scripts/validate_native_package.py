#!/usr/bin/env python3
"""Read-only validator for a real native LetMeBlock deb; never installs/runs it."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import plistlib
import struct
import subprocess
import tarfile

from native_contract import (ARCH, DEPENDS, DYLIB_PATH, FILTER_PATH, LICENSE_PATH,
                             PACKAGE, PROFILE_PATH, SCRIPTS, VERSION,
                             parse_control, require, validate_profile)


def read_tar(blob):
    files, modes = {}, {}
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:") as archive:
        for entry in archive:
            path = PurePosixPath(entry.name)
            require(not path.is_absolute() and ".." not in path.parts, "unsafe archive path")
            require(entry.uid == 0 and entry.gid == 0, "archive entries must be numeric root:root")
            name = str(path)
            if entry.isdir():
                continue
            require(entry.isfile(), f"unexpected non-regular entry: {name}")
            require(name not in files, f"duplicate archive entry: {name}")
            files[name] = archive.extractfile(entry).read()
            modes[name] = entry.mode
    return files, modes


def version_tuple(number):
    return (number >> 16, (number >> 8) & 255, number & 255)


def thin_macho(blob):
    require(len(blob) >= 32 and blob[:4] == b"\xcf\xfa\xed\xfe", "expected little-endian 64-bit Mach-O")
    _, cpu, subtype, kind, count, size, _, _ = struct.unpack_from("<8I", blob)
    require(cpu == 0x100000c and (subtype & 0xffffff) == 2, "native slice must be arm64e")
    require(kind == 6, "expected MH_DYLIB")
    require(32 + size <= len(blob), "truncated load-command area")
    cursor, end = 32, 32 + size
    dependencies, identities, platforms, signatures, symtabs = [], [], [], 0, []
    for _ in range(count):
        require(cursor + 8 <= end, "truncated load command")
        command, length = struct.unpack_from("<II", blob, cursor)
        require(length >= 8 and length % 8 == 0 and cursor + length <= end, "invalid load-command size")
        value = blob[cursor:cursor + length]
        if command in (0xc, 0xd, 0x80000018, 0x8000001f, 0x80000023):
            require(length >= 24, "short dylib command")
            offset = struct.unpack_from("<I", value, 8)[0]
            require(24 <= offset < length and b"\0" in value[offset:], "invalid dylib name")
            name = value[offset:].split(b"\0", 1)[0].decode()
            (identities if command == 0xd else dependencies).append(name)
        elif command == 0x32:
            require(length >= 24, "short build-version command")
            platform, minimum, sdk, tools = struct.unpack_from("<4I", value, 8)
            require(length == 24 + 8 * tools, "invalid build-version tools")
            require(platform == 2, "not the iOS device platform")
            platforms.append((version_tuple(minimum), version_tuple(sdk)))
        elif command == 0x25:
            require(length == 16, "invalid iOS-minimum command")
            minimum, sdk = struct.unpack_from("<II", value, 8)
            platforms.append((version_tuple(minimum), version_tuple(sdk)))
        elif command == 0x2:
            require(length == 24, "invalid symbol-table command")
            symtabs.append(struct.unpack_from("<4I", value, 8))
        elif command == 0x1d:
            require(length == 16, "invalid code-signature command")
            offset, size_signature = struct.unpack_from("<II", value, 8)
            require(size_signature > 0 and offset + size_signature <= len(blob), "missing signature blob")
            signatures += 1
        cursor += length
    require(cursor == end, "load-command count mismatch")
    require(len(platforms) == 1 and platforms[0][0] == (15, 0, 0), "minimum iOS must be 15.0")
    require(platforms[0][1] >= platforms[0][0], "SDK older than deployment target")
    require(identities == ["@loader_path/.jbroot/Library/MobileSubstrate/DynamicLibraries/LetMeBlock.dylib"],
            "unexpected native dylib install name")
    for name in ("libsandy.dylib", "libroothide.dylib", "libsubstrate.dylib"):
        require(f"@loader_path/.jbroot/usr/lib/{name}" in dependencies,
                f"missing native {name} load command")
    require(all("/var/jb" not in name for name in dependencies), "rootless library dependency")
    require(signatures == 1, "expected one embedded code-signature command (not a trust check)")
    require(len(symtabs) == 1, "expected one symbol table")
    symoff, nsyms, stroff, strsize = symtabs[0]
    require(symoff + 16 * nsyms <= len(blob) and stroff + strsize <= len(blob),
            "truncated symbol/string table")
    strings = blob[stroff:stroff + strsize]
    imports = {}
    for index in range(nsyms):
        string, kind, _, description, _ = struct.unpack_from("<IBBHQ", blob, symoff + index * 16)
        if kind & 0xe0 or (kind & 0x0e) != 0 or not kind & 1:
            continue
        require(string < len(strings) and b"\0" in strings[string:], "invalid symbol string")
        name = strings[string:].split(b"\0", 1)[0].decode()
        ordinal = (description >> 8) & 255
        imports[name] = dependencies[ordinal - 1] if 1 <= ordinal <= len(dependencies) else str(ordinal)
    required_imports = {"_libSandy_applyProfile": "libsandy.dylib",
                        "_MSFindSymbol": "libsubstrate.dylib",
                        "_MSGetImageByName": "libsubstrate.dylib",
                        "_MSHookFunction": "libsubstrate.dylib"}
    for symbol, library in required_imports.items():
        require(imports.get(symbol) == f"@loader_path/.jbroot/usr/lib/{library}",
                f"missing/wrong native external symbol binding: {symbol}")
    return {"architecture": "arm64e", "cpu_subtype": hex(subtype),
            "minimum_ios": platforms[0][0], "sdk": platforms[0][1],
            "install_name": identities[0], "dependencies": dependencies,
            "code_signature_commands": signatures,
            "verified_imports": {name: imports[name] for name in required_imports}}


def inspect_macho(blob):
    for forbidden in (b"/var/jb", b"rootless-compat", b"roothidepatch", b"PSHeader"):
        require(forbidden not in blob, f"forbidden native binary marker: {forbidden!r}")
    magic = blob[:4]
    if magic not in (b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"):
        return [thin_macho(blob)]
    require(len(blob) >= 8, "truncated fat header")
    count = struct.unpack_from(">I", blob, 4)[0]
    require(count == 1, "native package must contain only one arm64e slice")
    wide = magic[-1] == 0xbf
    width = 32 if wide else 20
    require(len(blob) >= 8 + width, "truncated fat architecture")
    values = struct.unpack_from(">IIQQII" if wide else ">IIIII", blob, 8)
    cpu, subtype, offset, size = values[:4]
    require(cpu == 0x100000c and (subtype & 0xffffff) == 2, "non-arm64e fat entry")
    require(offset >= 8 + width and offset + size <= len(blob), "invalid fat slice extent")
    return [thin_macho(blob[offset:offset + size])]


def validate_filter(blob):
    expected = {"Filter": {"Executables": ["mDNSResponder", "mDNSResponderHelper"]}}
    try:
        require(plistlib.loads(blob) == expected, "unexpected injection filter")
    except plistlib.InvalidFileException:
        # The source OpenStep form may survive non-FINALPACKAGE builds.
        compact = "".join(blob.decode().split())
        require(compact == '{Filter={Executables=("mDNSResponder","mDNSResponderHelper");};}',
                "unexpected OpenStep injection filter")


def validate_package(deb, project):
    # dpkg-deb emits tar streams; nothing is extracted to disk or executed.
    control_blob = subprocess.check_output(["dpkg-deb", "--ctrl-tarfile", str(deb)])
    data_blob = subprocess.check_output(["dpkg-deb", "--fsys-tarfile", str(deb)])
    control, control_modes = read_tar(control_blob)
    files, _ = read_tar(data_blob)
    require("control" in control, "missing control metadata")
    fields = parse_control(control["control"].decode())
    for key, expected in (("Package", PACKAGE), ("Version", VERSION), ("Architecture", ARCH), ("Depends", DEPENDS)):
        require(fields.get(key) == expected, f"unexpected {key}: {fields.get(key)!r}")
    require(set(control) <= {"control", "md5sums", *SCRIPTS}, "unexpected package maintainer file")
    for name, script in SCRIPTS.items():
        require(control.get(name) == script.encode(), f"unexpected native maintenance script: {name}")
        require(control_modes[name] & 0o111 != 0, f"maintenance script not executable: {name}")
    require(set(files) == {DYLIB_PATH, FILTER_PATH, PROFILE_PATH, LICENSE_PATH},
            "payload paths differ from the exact native allowlist (no hosts files, libraries, or compatibility extras allowed)")
    validate_profile(plistlib.loads(files[PROFILE_PATH]))
    validate_filter(files[FILTER_PATH])
    require(files[LICENSE_PATH] == (project / "LICENSE").read_bytes(), "MIT copyright notice differs from source")
    macho = inspect_macho(files[DYLIB_PATH])
    return {"package": PACKAGE, "version": VERSION, "architecture": ARCH,
            "sha256": hashlib.sha256(deb.read_bytes()).hexdigest(),
            "payload_paths": sorted(files), "mach_o": macho,
            "scope": "Static package validation only; signature trust, injection, sandbox access, DNS behavior and stability are not proven."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("deb", type=Path)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        result = validate_package(args.deb.resolve(), args.project.resolve())
    except (ValueError, OSError, subprocess.CalledProcessError, plistlib.InvalidFileException,
            struct.error, tarfile.TarError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
