#!/usr/bin/env python3
"""Non-Apple regression suite. No package scripts, iOS build or device access."""
import copy
import hashlib
import io
import os
from pathlib import Path
import plistlib
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "scripts"))
from native_contract import (ARCH, DEPENDS, DYLIB_PATH, FILTER_PATH, HOSTS,
                             LICENSE_PATH, PACKAGE, PROFILE_PATH, SCRIPTS,
                             VERSION, native_profile, parse_control,
                             validate_profile)
from stage_native import stage_native
from validate_native_package import inspect_macho, read_tar, validate_package


def run(args, **kwargs):
    try:
        return subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.STDOUT, **kwargs)
    except subprocess.CalledProcessError as error:
        raise AssertionError(f"command failed: {args!r}\n{error.output}") from error


def dylib_command(command, name):
    data = name.encode() + b"\0"
    length = (24 + len(data) + 7) & ~7
    return struct.pack("<6I", command, length, 24, 0, 0, 0) + data.ljust(length - 24, b"\0")


def fake_macho(minimum=15 << 16, subtype=0x80000002, sandy=None):
    commands = [struct.pack("<6I", 0x32, 24, 2, minimum, 18 << 16, 0)]
    commands += [dylib_command(0xd, "@loader_path/.jbroot/" + DYLIB_PATH),
                 dylib_command(0xc, sandy or "@loader_path/.jbroot/usr/lib/libsandy.dylib"),
                 dylib_command(0xc, "@loader_path/.jbroot/usr/lib/libroothide.dylib")]
    data = b"".join(commands)
    return struct.pack("<8I", 0xfeedfacf, 0x100000c, subtype, 6, len(commands), len(data), 0, 0) + data


def fake_tar(files, executable=()):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        for name, data in files.items():
            item = tarfile.TarInfo("./" + name)
            item.size = len(data)
            item.mode = 0o755 if name in executable else 0o644
            archive.addfile(item, io.BytesIO(data))
    return output.getvalue()


class NativeTests(unittest.TestCase):
    def test_actual_fallback_c_and_cpp(self):
        for compiler, language, standard in ((os.environ.get("CC", "cc"), "c", "c11"),
                                               (os.environ.get("CXX", "clang++"), "c++", "c++11")):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as folder:
                binary = str(Path(folder) / "hosts")
                run([compiler, "-x", language, "-std=" + standard, "-Wall", "-Wextra", "-Werror",
                     "-I.", "-Itests/stubs", "-DTHEOS_PACKAGE_SCHEME_ROOTHIDE=1",
                     "tests/hosts_test.c", "-o", binary])
                self.assertIn("passed", run([binary]))

    def test_symbol_helpers_with_and_without_pac(self):
        for pac in (0, 1):
            with self.subTest(pac=pac), tempfile.TemporaryDirectory() as folder:
                binary = str(Path(folder) / "symbols")
                run(["clang", "-std=c11", "-Wall", "-Wextra", "-Werror",
                     "-Wno-builtin-macro-redefined", "-I.", "-Itests/stubs",
                     "-DLMB_TEST_PAC=" + str(pac), "tests/symbols_test.c", "-o", binary])
                self.assertIn("passed", run([binary]))

    def test_exact_native_profile_and_negative_scopes(self):
        validate_profile(native_profile())
        for mutate in (
            lambda p: p["AllowedProcesses"].append("com.apple.mDNSResponderHelper"),
            lambda p: p.update(Conditions=[{"ConditionType": "FileExistance"}]),
            lambda p: p["Extensions"][0].update(path="/etc"),
            lambda p: p["Extensions"][0].update(path="/var/jb/etc/hosts"),
            lambda p: p["Extensions"][0].update(RootHideRelative=True),
            lambda p: p["Extensions"][1].pop("path"),
            lambda p: p["Extensions"].pop(),
            lambda p: p["Extensions"][0].update(extension_class="com.apple.app-sandbox.read-write"),
        ):
            bad = copy.deepcopy(native_profile())
            mutate(bad)
            with self.assertRaises(ValueError):
                validate_profile(bad)

    def test_legacy_metadata_byte_identical(self):
        hashes = {
            PROFILE_PATH: "b9bf6e4b110651a2b6ba6fed9813ff25f1b94e81f30d2720c815e32b6ee0288d",
            "DEBIAN/control": "563430218467b86c85fa4ae519da1118e9aa046c3ba56cc2f331959dd90926fd",
            "DEBIAN/extrainst_": "11072bc4d3d608de1812dbc8237432f4fee336646d19aedde95395fd3498912a",
            "DEBIAN/postrm": "ef2695019ea753575a4966bb7c40077214ef80d0c5e4e9efc186f5a2ff1ce146",
        }
        for name, expected in hashes.items():
            self.assertEqual(hashlib.sha256((ROOT / "layout" / name).read_bytes()).hexdigest(), expected)

    def test_native_staging_isolated_and_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            stage = Path(folder) / "stage"
            shutil.copytree(ROOT / "layout", stage)
            control = stage / "DEBIAN/control"
            # Simulate the control fields generated by Theos, not a package build.
            control.write_text(control.read_text().replace("Version: 1.0.0", "Version: " + VERSION)
                               .replace("Architecture: iphoneos-arm", "Architecture: " + ARCH))
            for _ in range(2):
                stage_native(ROOT, stage, payload=True, control=True)
                validate_profile(plistlib.loads((stage / PROFILE_PATH).read_bytes()))
                self.assertEqual(parse_control(control.read_text())["Depends"], DEPENDS)
                self.assertEqual((stage / LICENSE_PATH).read_bytes(), (ROOT / "LICENSE").read_bytes())
                for name, text in SCRIPTS.items():
                    self.assertEqual((stage / "DEBIAN" / name).read_text(), text)
                    self.assertEqual((stage / "DEBIAN" / name).stat().st_mode & 0o777, 0o755)
            self.assertFalse((stage / "etc/hosts").exists())
        with self.assertRaises(ValueError):
            stage_native(ROOT, ROOT / "layout", payload=True)

    def test_native_preprocessing_and_availability_without_psheader(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            for name in ("Foundation/Foundation.h", "libSandy.h", "HBLog.h", "sys/sysctl.h", "xpc/xpc.h"):
                stub = directory / name
                stub.parent.mkdir(parents=True, exist_ok=True)
                stub.write_text("/* Declaration-free preprocessing stub. */\n")
            flags = ["clang", "-x", "objective-c++", "-I.", "-I" + folder, "-Itests/stubs",
                     "-DTHEOS_PACKAGE_SCHEME_ROOTHIDE=1"]
            output = run(flags + ["-E", "-P", "Tweak.xm"])
            for forbidden in ("/var/jb", "PSHeader", "_PSFindSymbol", "iOS_12_0", "ROOT_PATH("):
                self.assertNotIn(forbidden, output)
            self.assertIn("return jbroot(path)", output)
            self.assertIn('etcHosts = LMBOpenManagedHosts("r", fopen, LMBManagedPath)', output)
            self.assertNotIn("LMBPreopenHosts", output)
            self.assertIn("if (mDNS_StatusCallback)", output)
            self.assertIn("if (os_variant_has_internal_diagnostics)", output)
            glue = directory / "glue.mm"
            glue.write_text('#include "include/LMBNative.h"\nbool available() { if (LMB_IOS12_OR_NEWER) return true; return false; }\n')
            run(flags + ["-std=c++11", "-Wall", "-Werror", "-fsyntax-only", str(glue)])

    def test_actual_fopen_lambda_adapter_compiles(self):
        source = (ROOT / "Tweak.xm").read_text()
        hook = source.split("%hookf(FILE *, fopen, const char *path, const char *mode) {", 1)[1].split("\n%end", 1)[0]
        with tempfile.TemporaryDirectory() as folder:
            source_path = Path(folder) / "adapter.cpp"
            source_path.write_text('#include "include/LMBHosts.h"\nstatic FILE *etcHosts;\n'
                                   'static const char *LMBManagedPath(const char *p) { return p; }\n'
                                   'static FILE *fakeOpen(const char *, const char *) { return 0; }\n'
                                   'FILE *testHook(const char *path, const char *mode) {' + hook.replace("%orig(", "fakeOpen("))
            run(["clang++", "-std=c++11", "-Wall", "-Wextra", "-Werror", "-I.", "-fsyntax-only", str(source_path)])

    def test_makefile_native_and_legacy_configuration(self):
        with tempfile.TemporaryDirectory() as folder:
            theos = Path(folder)
            (theos / "makefiles").mkdir()
            (theos / "makefiles/common.mk").write_text("THEOS_MAKE_PATH := " + folder + "/makefiles\n")
            (theos / "makefiles/tweak.mk").write_text(
                'lmb-test-config:\n\t@echo "$(TARGET)|$(ARCHS)|$(PREFIX)|$(PACKAGE_VERSION)|$(LetMeBlock_LIBRARIES)|$(LetMeBlock_CFLAGS)|$(LetMeBlock_LDFLAGS)"\n')
            def config(scheme):
                return run(["make", "--no-print-directory", "lmb-test-config", "THEOS=" + folder,
                            "THEOS_PACKAGE_SCHEME=" + scheme, "LMB_LIBSANDY_INCLUDE_DIR=/fixture/include",
                            "LMB_LIBSANDY_LIB_DIR=/fixture/lib"]).strip().split("|")
            native = config("roothide")
            self.assertEqual(native[:2], ["iphone:clang:latest:15.0", "arm64e"])
            self.assertNotIn("Xcode11", native[2])
            self.assertEqual(native[3:5], [VERSION, "sandy roothide"])
            self.assertIn("-I/fixture/include", native[5])
            self.assertIn("-L/fixture/lib", native[6])
            self.assertEqual(config("rootless")[:2], ["iphone:clang:latest:14.0", "arm64 arm64e"])
            self.assertEqual(config("")[0], "iphone:clang:14.5:9.0")
            self.assertIn("Xcode11", config("")[2])

    def test_hook_bodies_and_jetsam_preserved(self):
        source = (ROOT / "Tweak.xm").read_text()
        self.assertEqual(source.count("%hookf("), 5)
        self.assertIn("#define JETSAM_MEMORY_LIMIT 512", source)
        self.assertIn("if (mDNS_StatusCallback_allocated)\n        *mDNS_StatusCallback_allocated = 0;\n    %orig(arg1, arg2);", source)
        self.assertIn('if (etcHosts) fclose(etcHosts);', source)
        self.assertIn('libSandy_applyProfile("LetMeBlock");', source)

    def test_macho_metadata_and_negative_cases(self):
        valid = fake_macho()
        self.assertEqual(inspect_macho(valid)[0]["architecture"], "arm64e")
        fat = struct.pack(">7I", 0xcafebabe, 1, 0x100000c, 0x80000002, 32, len(valid), 3) + b"\0" * 4 + valid
        self.assertEqual(inspect_macho(fat)[0]["minimum_ios"], (15, 0, 0))
        for bad in (valid[:15], fake_macho(minimum=14 << 16), fake_macho(subtype=0),
                    fake_macho(sandy="/usr/lib/libsandy.dylib"), valid + b"/var/jb",
                    valid + b"rootless-compat", valid + b"roothidepatch"):
            with self.assertRaises(ValueError):
                inspect_macho(bad)

    def test_fake_package_validation_without_build_or_execution(self):
        fields = f"Package: {PACKAGE}\nVersion: {VERSION}\nArchitecture: {ARCH}\nDepends: {DEPENDS}\n"
        control = {"control": fields.encode(), **{k: v.encode() for k, v in SCRIPTS.items()}}
        data = {DYLIB_PATH: fake_macho(), FILTER_PATH: (ROOT / "LetMeBlock.plist").read_bytes(),
                PROFILE_PATH: plistlib.dumps(native_profile()), LICENSE_PATH: (ROOT / "LICENSE").read_bytes()}
        with tempfile.TemporaryDirectory() as folder:
            placeholder = Path(folder) / "not-a-real-deb"
            placeholder.write_bytes(b"Synthetic test placeholder, not a built package")
            def check(c, d):
                with patch("validate_native_package.subprocess.check_output",
                           side_effect=[fake_tar(c, SCRIPTS), fake_tar(d)]):
                    return validate_package(placeholder, ROOT)
            self.assertEqual(check(control, data)["version"], VERSION)
            with self.assertRaises(ValueError):
                check(control, {**data, "etc/hosts": b"not allowed"})
            with self.assertRaises(ValueError):
                check({**control, "control": fields.replace(VERSION, "1.3.0").encode()}, data)
            with self.assertRaises(ValueError):
                check({**control, "postinst": b"unexpected script"}, data)

    def test_archive_traversal_rejected(self):
        with self.assertRaises(ValueError):
            read_tar(fake_tar({"../etc/hosts": b"x"}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
