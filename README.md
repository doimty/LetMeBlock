# LetMeBlock

## Native RootHide candidate

The `roothide` scheme targets iOS 15+ / arm64e and packages as
`com.ps.letmeblock` **1.3.0-1+native1**, replacing rather than duplicating the
existing package. Managed hosts paths use `jbroot()`; no rootless compatibility
conversion is required. This is an unverified-on-device candidate, not a claim
of successful DNS blocking or unchanged memory behavior on a particular OS.

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
