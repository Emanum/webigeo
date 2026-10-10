# webgpu_app - iOS Build

How to build `webgpu_app` for iPhone and run it on your own device from a Mac. The WebGPU app has
never been built for mobile before; the Android CI job builds the older OpenGL QML app, and
`ALP_BUILD_WEBGPU_APP` defaults to `OFF` on Apple and Android. Everything below is new.

Status (2026-10-10): runs on an iPhone 17 Pro Max (iOS 27, Xcode 27). The map renders, touch input
works, the avalanche simulation runs on the phone's GPU, and rotation, screenshots and the app
switcher are handled. Rendering is at the point size (1x) for now; see [Open work](#open-work).

## Overview

| Piece | Where it comes from |
|---|---|
| Qt 6.11.1 for iOS | prebuilt, installed with `aqt` into `~/Qt/6.11.1/ios` |
| Dawn (WebGPU) | **built from source** for iOS by `misc/scripts/install_dawn.py --platform ios`, Metal backend, with one patch (see below) |
| SDL2 | built from source by `misc/scripts/install_sdl.py --platform ios`, static |
| App | CMake preset `webgpu_app_ios` (Xcode generator, Qt's iOS toolchain) |

The iOS builds of Dawn and SDL install **next to** the host builds and never replace them:

```
extern/dawn/install/Debug, Release           host (macOS) Dawn, unchanged
extern/dawn/install/ios-Release               iPhone (arm64)
extern/dawn/install/ios-simulator-Release     iOS Simulator (arm64), currently unused
extern/sdl                                    host SDL2
extern/sdl-ios, extern/sdl-ios-simulator      iOS SDL2, static
```

## One-time setup

1. **Xcode** (27.0 here) from the App Store, then:

   ```bash
   sudo xcode-select -s /Applications/Xcode.app
   ```

   ```bash
   sudo xcodebuild -license accept
   ```

   ```bash
   xcodebuild -downloadPlatform iOS
   ```

2. **Qt for iOS.** Qt here was installed with `aqt` (Homebrew's `aqtinstall`), not the Qt
   Maintenance Tool:

   ```bash
   aqt install-qt mac ios 6.11.1 ios -O ~/Qt
   ```

   Cross-building needs the macOS Qt of the same version as host Qt (`~/Qt/6.11.1/macos`).
   The base modules are enough; the WebGPU app only links Qt Core and Network.

3. **Signing.** Xcode → Settings → Accounts: add your Apple ID, then *Manage Certificates* →
   add an *Apple Development* certificate. A free personal team is enough for your own device.
   Your Team ID is the 10-character code shown for the team (not the code in brackets in the
   certificate name). It can also be read on the command line:

   ```bash
   defaults read com.apple.dt.Xcode IDEProvisioningTeamByIdentifier | grep -E "teamID|teamName"
   ```

4. **iPhone.** Connect by cable, tap *Trust*, turn on Settings → Privacy & Security →
   *Developer Mode* (restarts the phone). After the first install, trust the developer once:
   Settings → General → *VPN & Device Management* → your account → *Trust*.

## Dependencies

CMake builds both automatically on the first configure if they are missing. To build them by
hand (Dawn takes 30–40 minutes):

```bash
python3 misc/scripts/install_sdl.py --install-prefix extern/sdl-ios --platform ios
```

```bash
python3 misc/scripts/install_dawn.py --extern-dir extern --dawn-version 20260420.230544 --platform ios --build-types Release
```

The Dawn version must match `ALP_DAWN_VERSION` in `webgpu/base/CMakeLists.txt`. CMake only
accepts an installation that has a matching `.alp_dawn_version` file; a hand-built one needs it
written:

```bash
echo "20260420.230544" > extern/dawn/install/ios-Release/.alp_dawn_version
```

### What the iOS Dawn build changes

`install_dawn.py --platform ios|ios-simulator` differs from the host build in:

- **Metal** backend on, Vulkan off; `CMAKE_SYSTEM_NAME=iOS`, arm64, deployment target iOS 17.0.
- **Tint command-line tools off** (`TINT_BUILD_CMD_TOOLS=OFF`). On iOS every executable becomes an
  app bundle, and Tint's install rules then fail at configure time.
- **Protobuf and tests off** (`DAWN_BUILD_PROTOBUF=OFF`, `DAWN_BUILD_TESTS=OFF`). Protobuf would
  build a host tool (`protoc`) for the phone.
- **A source patch**, `patch_dawn_for_ios()`. Dawn enables the `texture-compression-bc` feature
  on iPhones whose GPU supports it, but `src/dawn/native/metal/UtilsMetal.mm` maps the BC texture
  formats to Metal only under `#if DAWN_PLATFORM_IS(MACOS)` and hits `DAWN_UNREACHABLE()` (an
  abort) on iOS. The cloud renderer creates a BC4 texture, so the app crashed at startup. The
  Metal BC formats exist on iOS 16.4+, so the patch extends the `#if` to iOS. The script fails
  loudly if the pattern is not found, e.g. after a Dawn version bump.
- It works in `extern/dawn/src-<platform>` and installs to `extern/dawn/install/<platform>-<Build>`.
  The host build keeps its old behaviour (it still replaces `extern/dawn`, except `install`).

## Build, install, run

```bash
cmake --preset webgpu_app_ios -DALP_IOS_DEVELOPMENT_TEAM=<your team id>
```

```bash
cmake --build --preset webgpu_app_ios -- -allowProvisioningUpdates
```

The app ends up in `build/webgpu_app_ios/apps/webgpu_app/Release-iphoneos/webgpu_app.app`.
Find the device ID, then install and launch:

```bash
xcrun devicectl list devices
```

```bash
xcrun devicectl device install app --device <device id> build/webgpu_app_ios/apps/webgpu_app/Release-iphoneos/webgpu_app.app
```

```bash
xcrun devicectl device process launch --device <device id> --terminate-existing dev.emanum.webigeo
```

The phone has to be unlocked for the launch. With a free team the signature is valid for 7
days; after that, build and install again. You can also open
`build/webgpu_app_ios/alpine-renderer.xcodeproj` in Xcode and press Run.

Settings (cache variables, all in `apps/webgpu_app/CMakeLists.txt`):

| Variable | Default | Meaning |
|---|---|---|
| `ALP_IOS_DEVELOPMENT_TEAM` | empty | Team ID for signing; required for a device build |
| `ALP_IOS_BUNDLE_IDENTIFIER` | `dev.emanum.webigeo` | must be unique per Apple ID with a free team |
| `ALP_IOS_PLATFORM` | from `CMAKE_OSX_SYSROOT` | `ios` or `ios-simulator`; selects the Dawn/SDL builds |

To check that a build compiles and links without signing:

```bash
cmake --build --preset webgpu_app_ios -- CODE_SIGNING_ALLOWED=NO
```

### Logs

An iOS app has no terminal, and `devicectl --console` showed nothing. For now `main.cpp`
redirects stdout and stderr to `Documents/webigeo.log` in the app's container (marked
`TEMP-IOS-DIAG`). Copy it off the phone with:

```bash
xcrun devicectl device copy from --device <device id> --domain-type appDataContainer --domain-identifier dev.emanum.webigeo --source Documents/webigeo.log --destination webigeo.log
```

Crash reports: list them with `xcrun devicectl device info files --device <device id> --domain-type systemCrashLogs`
and copy one with `copy from --domain-type systemCrashLogs --source <name>.ips`. The `.ips` file
is JSON after its first line; the triggered thread's frames show where it crashed.

## What the app needed for iOS

| Problem | Fix |
|---|---|
| The WebGPU preset must not link Qt GUI (Qt would take over the app's entry point) | already the case: `webgpu_base` turns labels and the avalanche warning layer off, the only users of Qt GUI |
| Qt for iOS still sets `_qt_main_wrapper` (from its GUI plugin) as entry point; link fails | `qt_no_entrypoint TRUE` and `XCODE_ATTRIBUTE_LD_ENTRY_POINT _main` on the app target. SDL owns the lifecycle: `App.h` includes `SDL.h`, so `SDL_main.h` renames our `main()`, and `SDL2main` supplies the real `main()` that starts `UIApplicationMain` |
| **iOS 26+ SDK requires the UIScene lifecycle**; UIKit stops the app at launch (`_UIApplicationEvaluateRuntimeIssueForNoSceneLifecycleAdoption`). SDL2 predates scenes | own `apps/webgpu_app/ios/Info.plist.in` (Qt's template plus a one-window scene manifest, full screen, no status bar) and `ios/IosScene.mm`, which attaches SDL's `UIWindow` to that scene after `SDL_CreateWindow` |
| Xcode enables `-Wshorten-64-to-32`, `nucleus` builds with `-Werror` | `CMAKE_XCODE_ATTRIBUTE_GCC_WARN_64_TO_32_BIT_CONVERSION=NO` in the iOS preset, the same warnings as the desktop build |
| ImGuiFileDialog calls `system()`, which iOS does not have | left out on iOS (`ALP_PLATFORM_IOS`); the file picker returns nothing there |
| The macOS packaging step (macdeployqt, copying dylibs into the bundle, ad-hoc signing) breaks under Xcode | skipped on iOS: everything links statically and Xcode signs |
| Metal layer sized in points, rendering at a third of the resolution | `webgpu_interface.cpp` sets `contentsScale` and a pixel `drawableSize`; the window is fullscreen and the viewport is taken from it |
| BC4 cloud texture aborts in Dawn | the Dawn patch above |
| Killed right after start (`SDL_APP_LOWMEMORY`, then SIGKILL, no crash report) | the cloud atlas is allocated in full at startup: 1 GiB of BC4 at `ATLAS_BITS_Z = 5`. On iOS it is 2 (~146 MiB, 64 instead of 512 cloud tiles), `webgpu/engine/cloud/CloudRenderer.h` |
| Rotation: the hand-made `CAMetalLayer` kept its first frame | the surface uses `SDL_Metal_CreateView` (window created with `SDL_WINDOW_METAL`) |
| GPU work while in the background (a screenshot or the app switcher is enough) | an SDL event watch pauses rendering between `SDL_APP_WILLENTERBACKGROUND` and `SDL_APP_DIDENTERFOREGROUND`; on return the surface is reconfigured |
| Screenshot in landscape: iOS lays the app out in portrait for the snapshot; afterwards SDL still reports portrait and UIKit does not lay SDL2's views out again (half black, then all black after rotating back) | every frame on iOS, `ios::fit_views_to_window()` sets SDL's root view and Metal view to the window's safe area, and the viewport follows the UIKit size (`ios::current_window_size()`) instead of SDL's cached one |
| Map black under a live UI after a resize back to the same size | `App::on_window_resize()` always forces one map repaint: the framebuffer is recreated empty, and the camera only requests a redraw when the viewport changed |
| UI covers the screen; top edge and Dynamic Island take the touches | `ui/UiScale.h`: 0.75 on iOS for fonts, spacing, the sidebar and fixed button widths. The app draws only in the safe area (black bars outside), and `SDL_HINT_IOS_HIDE_HOME_INDICATOR=2` makes edge swipes need a second swipe |

All iOS-specific code is behind `if (IOS)` in CMake or `#ifdef ALP_PLATFORM_IOS` in C++.

## iOS Simulator: not working with the prebuilt Qt

The preset `webgpu_app_ios_simulator` exists and everything compiles, but the final link fails:
Qt's prebuilt iOS kit contains the device as arm64 and the **simulator only as x86_64**, so an
arm64 simulator app cannot link against it. Ways out, none done:

- Build the simulator as x86_64: needs Rosetta (`softwareupdate --install-rosetta`, which Apple
  is phasing out) and x86_64 builds of Dawn and SDL.
- Build Qt from source with an arm64 simulator slice.

## Open work

- Full resolution: report pixel sizes (`SDL_WINDOW_ALLOW_HIGHDPI`, `SDL_GetWindowSizeInPixels`)
  and convert touch coordinates; currently rendering happens at the point size, so text and the
  map are soft.
- Edge-to-edge map: the app is inset to the safe area; drawing the map full screen with only the
  UI inset needs the panels to place themselves inside the safe area.
- Touch: one finger as mouse works through SDL; pinch zoom is missing.
- The iOS workarounds around SDL2's window (scene attachment, view fitting) would go away with
  SDL3, which supports UIScene.
- Replace the `TEMP-IOS-DIAG` log redirect and SDL event logging with a proper option.
- Timestamp queries may be unavailable on iOS; the avalanche panel's pacing then stays manual.
