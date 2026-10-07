#!/usr/bin/env python3
"""Generate native-only staging files. Never run package maintenance scripts."""
import argparse
from pathlib import Path
import plistlib

from native_contract import (ARCH, DEPENDS, LICENSE_PATH, PACKAGE, PROFILE_PATH,
                             SCRIPTS, VERSION, native_profile, parse_control,
                             require)


def write_file(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".native-tmp")
    temporary.write_bytes(data)
    temporary.chmod(mode)
    temporary.replace(path)


def stage_native(project, stage, payload=False, control=False):
    project, stage = project.resolve(), stage.resolve()
    require(stage not in (project, project / "layout") and stage not in project.parents,
            "refusing source/root directory as staging directory")
    require((stage / PROFILE_PATH).is_file(), "stage must already contain the layout profile")
    if payload:
        write_file(stage / PROFILE_PATH,
                   plistlib.dumps(native_profile(), sort_keys=False))
        write_file(stage / LICENSE_PATH, (project / "LICENSE").read_bytes())
        for name, text in SCRIPTS.items():
            write_file(stage / "DEBIAN" / name, text.encode(), 0o755)
    if control:
        path = stage / "DEBIAN/control"
        fields = parse_control(path.read_text())
        require(fields.get("Package") == PACKAGE, "unexpected package identity")
        require(fields.get("Version") == VERSION, "unexpected Theos package version")
        require(fields.get("Architecture") == ARCH, "not a native RootHide package")
        fields["Depends"] = DEPENDS
        write_file(path, "".join(f"{key}: {value}\n" for key, value in fields.items()).encode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--payload", action="store_true")
    parser.add_argument("--control", action="store_true")
    args = parser.parse_args()
    parser.error("choose --payload and/or --control") if not (args.payload or args.control) else None
    stage_native(args.project, args.stage, args.payload, args.control)


if __name__ == "__main__":
    main()
