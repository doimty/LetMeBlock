# Native RootHide build and dependency contract

This is an **unverified-on-device candidate**. Build only with the native RootHide scheme; do not run a rootless conversion or install this package during CI.

## Pinned build inputs

`ci/dependencies.json` fixes the complete URLs/SHA-256 values:

- RootHide Theos `88506b2c22e9e07dd4ed055f23c9e398a117a2c7`, fetched explicitly by SHA, including pinned submodules.
- Theos iPhoneOS16.5.sdk archive, SHA-256 `5e0fd3f01266cce4ce012d4a99b38eb56578fca40d09edc81cd83dee958202fb`. Its internal Mach-O SDK version may be 16.4; this is not evidence of a wrong download. Deployment target is independently fixed to 15.0.
- Official `https://roothide.github.io/` package `com.opa334.libsandy` 1.1.6-4, iphoneos-arm64e, 19562 bytes, SHA-256 `81a1eeb17480b6ee200f8f4bf815892e6f58cc55f5aea6d7abe899db11da4bb5`.
- Unmodified public libSandy header and its license from opa334/libSandy `9c77311172485e92bf0c439391be5a9565c877e4`. No source checkout/build of libSandy.

The dependency deb is downloaded and verified, and only its `usr/lib/libsandy.dylib` data member is copied into the temporary Theos library directory. No dependency scripts run; the library is **not bundled** in the LetMeBlock deb. Its fat arm64+arm64e Mach-O install name is `@loader_path/.jbroot/usr/lib/libsandy.dylib`; linking selects arm64e. Package dependency requires the existing official release >= 1.1.6-4.

## Actual official binary evidence

Read-only disassembly of the pinned package's `usr/local/libexec/sandyd` (thin arm64; SHA-256 `0a2338cca42db6b1514bd6745b1bc04de530117edb218c5bc4c23bb66ae50745`) shows `_issueExtension` at VA `0x100005d2c`. CFString references select `type`, `extension_class`, `file` and `path`: the path CFString at `0x1000083c8` points to string VA `0x100007972`. After dictionary lookup at `0x100005db0`, `0x100005dc0` calls `__Z6jbrootP8NSString`; its result is converted to UTF8String and passed as x1 to `_compat_sandbox_extension_issue_file_to_process` at `0x100005e10`. These are unslid virtual addresses, not device addresses. This directly supports logical paths in the official schema, not an invented field or an assumption based only on current source.

Native profile is exactly:

```json
{
  "AllowedProcesses": ["com.apple.mDNSResponder"],
  "Extensions": [
    {"type": "file", "extension_class": "com.apple.app-sandbox.read", "path": "/etc/hosts"},
    {"type": "file", "extension_class": "com.apple.app-sandbox.read", "path": "/etc/hosts.lmb"}
  ]
}
```

No Conditions/Negated or RootHideRelative. Only this staged profile changes; legacy layout bytes and other profiles/scopes remain untouched. Applying the profile still uses the original public `libSandy_applyProfile("LetMeBlock")` call.

## Build / validation

On a macOS runner with Xcode, Python 3, GNU make, ldid, xz and dpkg:

```sh
export THEOS="$PWD/../theos-native"
python3 tests/test_native.py
python3 ci/prepare.py --theos "$THEOS" --work "$PWD/../native-inputs"
gmake clean package THEOS_PACKAGE_SCHEME=roothide FINALPACKAGE=1
python3 scripts/validate_native_package.py packages/*.deb
```

Use fresh preparation directories. The workflow runs on pushes to `feat/native-roothide` or manual dispatch. It archives the real deb, test/build logs, input hashes and submodules, source commit, Apple compiler version and linked-library/symbol metadata. Local tests include C/C++ fallback tests, mocked PAC helpers, exact profile negative cases, layout hashes, staging, generated configuration, preprocessing, hook lambda compilation, and synthetic validator fixtures. Synthetic fixtures are explicitly not iOS binaries; only the subsequent real-deb check validates the cloud output.

Native staging restricts payload to the tweak dylib, its original executable filter (mDNSResponder and mDNSResponderHelper), one profile and original MIT notice. No bundled library, hosts list or compatibility payload is allowed. Post-removal/upgrade scripts retain upstream daemon restart conditions, expressed as POSIX sh with absolute `/usr/bin/killall`; validation reads but never executes them. Real installation/removal is separately authorized work.

## Semantics and unresolved device risks

Only the exact raw `/etc/hosts` open is intercepted. Managed attempts use `jbroot("/etc/hosts")`, then `jbroot("/etc/hosts.lmb")`; if both opens fail, libc gets raw `/etc/hosts` unchanged. Open mode passes through; content is not validated. Constructor caches **only managed streams**, as upstream did. It never caches raw fallback, so later managed files can be retried. Existing stream-sharing/closing behavior is retained, not redesigned.

Native symbol helpers use Substrate declarations and compiler ptrauth strip/sign (function-pointer key, zero discriminator), with no PSHeader vendoring. Native initialization skips absent callable private symbols, but symbol availability, actual private ABI signatures and PAC at runtime remain device-specific. The five existing hooks, helper flow, allocation counter and 512 MB jetsam policy are preserved. A null guard can avoid a null hook but cannot prove an OS-private function's ABI. No real DNS, sandbox extension consumption, injection, memory/stability, signature trust or device compatibility claim follows from compilation.
