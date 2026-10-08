# LetMeBlock

## Native RootHide rebuild release

The `roothide` scheme targets iOS 15+ / arm64e and packages as
`com.ps.letmeblock` **1.3.0-2**, upgrading both the original 1.3.0 and the
1.3.0-1+native1 test build. This is doimty's native rebuild of PoomSmart's MIT
LetMeBlock, not an upstream release or a rewrite of its hook behavior. Managed
hosts paths use `jbroot()`; no rootless compatibility conversion is required.
Numeric archive ownership is root:root with unchanged payload/control bytes
and modes. Official libSandy is reused, never rebuilt or bundled.

See [release scope and validation](docs/RELEASE-1.3.0-2.md). A successful cloud
build is not proof of device DNS blocking, sandbox/PAC behavior or energy gains.

See [native build and API contract](docs/native-build.md) and
[scope / success criteria](docs/native-port-plan.md). Local checks:

```sh
python3 tests/test_native.py
```

## Original / legacy behavior

Makes mDNSResponder care about `(/var/jb)/etc/hosts` on iOS 12+, and load **all** entries on iOS 9+

In order to load all entries on iOS 9+, the memory limits defined in `Version4 > Daemon > Override > com.apple.mDNSResponder.reloaded` of the jetsam properties plist **must be increased**. This can be done either by manually editing the plist (and rebooting) or using jetsamctl's API, see [here](https://github.com/conradev/jetsamctl).

If in any cases the tweak does not seem to work, you either
* Reinstall LetMeBlock from your package manager of choice
* Run the command `killall -9 mDNSResponder; killall -9 mDNSResponderHelper` as root

## Compiling

```
make
```

If `xpc.h` isn't found, run:

```
sudo ln -s $(xcode-select -p)/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk/usr/include/xpc $(xcode-select -p)/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS.sdk/usr/include/xpc
sudo ln -s $(xcode-select -p)/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk/usr/include/launch.h  $(xcode-select -p)/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS.sdk/usr/include/launch.h
```
