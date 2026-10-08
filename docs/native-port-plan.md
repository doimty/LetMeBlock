# Native RootHide port plan

Current release follow-up: the user authorized `release/letmeblock-1.3.0-2`
from `3b4057d3`, native rebuild and publication to doimty.github.io. See
`RELEASE-1.3.0-2.md`; the original test scope below is historical. No device
installation or libSandy rebuild is authorized.

## Authorized scope and success criteria

- Base `1d40608c37a52902a4e8d515d37bd5ff4f0dd6bf`; only push `feat/native-roothide` to `doimty/LetMeBlock`. Leave master/default branch unchanged.
- Build only LetMeBlock, using **existing official** RootHide libSandy 1.1.6-4. Never rebuild, edit, install or package libSandy. Pins live in `ci/dependencies.json`.
- Theos RootHide scheme, arm64e, iOS 15+, package `com.ps.letmeblock` version `1.3.0-1+native1`; no compatibility conversion or duplicate identity.
- Intercept only raw `/etc/hosts`. Attempt `jbroot("/etc/hosts")`, `jbroot("/etc/hosts.lmb")`, then raw `/etc/hosts`. Constructor caches only managed files, preserving upstream semantics; raw fallback is not cached. Preserve mode and existing cached-stream ownership; readable does not imply valid DNS content.
- Use official profile schema: only `com.apple.mDNSResponder`, two file/read extensions with logical paths `/etc/hosts` and `/etc/hosts.lmb`; no custom fields or Conditions. Official sandyd itself maps those paths. Require libSandy >= 1.1.6-4.
- No PSHeader code copied; native helpers use Substrate and compiler PAC APIs. Skip null private callable symbols. This prevents null hooks, not private ABI mismatches.
- Keep all five hook bodies/purposes, allocation counter, helper flow, jetsam commands and 512 MB setting. No hosts lists, UI, network feature, new polling, timers, recording or system hosts changes.
- Legacy layout bytes and MIT notice remain unchanged; native-only staging carries the MIT notice and strict profile/dependencies. No new daemon lifecycle operations.
- Run host regression tests, then real macOS/Logos/iOS SDK build, then read-only real-deb validation on CI and Linux. Archive source, hashes and build metadata.

## Evidence boundary

No device connection, installation, package-maintainer script execution or daemon restart is authorized/performed. Mock tests cannot establish real PAC, private symbols, injection, sandbox access, DNS behavior or stability. Cloud success establishes compilation and package structure only. Maintenance scripts retain existing upgrade/remove/abort-install daemon restart behavior if a user separately chooses to install/remove the package.
