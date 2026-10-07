"""Native package contract; build-time data only, never device operations."""

PACKAGE = "com.ps.letmeblock"
VERSION = "1.3.0-1+native1"
ARCH = "iphoneos-arm64e"
SANDY_VERSION = "1.1.6-4"
DEPENDS = ("mobilesubstrate (>= 0.9.5000), firmware (>= 15.0), "
           f"com.opa334.libsandy (>= {SANDY_VERSION})")
PROFILE_PATH = "Library/libSandy/LetMeBlock.plist"
DYLIB_PATH = "Library/MobileSubstrate/DynamicLibraries/LetMeBlock.dylib"
FILTER_PATH = "Library/MobileSubstrate/DynamicLibraries/LetMeBlock.plist"
LICENSE_PATH = "usr/share/doc/com.ps.letmeblock/copyright"
HOSTS = ("/etc/hosts", "/etc/hosts.lmb")


def native_profile():
    return {
        "AllowedProcesses": ["com.apple.mDNSResponder"],
        "Extensions": [
            {"type": "file", "extension_class": "com.apple.app-sandbox.read",
             "path": path}
            for path in HOSTS
        ],
    }


# RootHide bootstrap scripts use jbroot-based interpreter/tool paths (vroot).
# Deliberately do not touch hosts files or add new lifecycle operations.
SCRIPTS = {
    "extrainst_": """#!/bin/sh

if [ "$1" = upgrade ]; then
    /usr/bin/killall -9 mDNSResponder || true
    /usr/bin/killall -9 mDNSResponderHelper || true
fi
""",
    "postrm": """#!/bin/sh

case "$1" in
    remove|abort-install)
        /usr/bin/killall -9 mDNSResponder || true
        /usr/bin/killall -9 mDNSResponderHelper || true
        ;;
esac
""",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def parse_control(text):
    fields = {}
    key = None
    for line in text.splitlines():
        if not line:
            continue
        if line[0].isspace() and key:
            fields[key] += "\n" + line
            continue
        require(":" in line, "invalid control line")
        key, value = line.split(":", 1)
        require(key not in fields, f"duplicate control field: {key}")
        fields[key] = value.strip()
    return fields


def validate_profile(profile):
    require(profile == native_profile(),
            "native profile must have exactly two official logical-path read grants, one process, and no conditions")
