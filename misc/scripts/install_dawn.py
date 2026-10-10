#!/usr/bin/env python3

import argparse
import sys
import os
import tempfile
import shutil

from setup_utils import log, fail, download, extract_zip, run_command

# Cross-compilation targets. "native" is the host build the rest of the build system has
# always used (Vulkan backend, installed to install/<BuildType>, replacing extern/dawn).
# The Apple mobile targets build the Metal backend and install next to it, to
# install/<platform>-<BuildType>, without touching the native installation.
CROSS_PLATFORMS = {
    "ios": ["-DCMAKE_SYSTEM_NAME=iOS", "-DCMAKE_OSX_SYSROOT=iphoneos"],
    "ios-simulator": ["-DCMAKE_SYSTEM_NAME=iOS", "-DCMAKE_OSX_SYSROOT=iphonesimulator"],
}
IOS_DEPLOYMENT_TARGET = "17.0"


def patch_dawn_for_ios(source_dir):
    """Dawn enables the texture-compression-bc feature on iPhones whose GPU supports it, but its
    Metal format table maps the BC formats only on macOS and aborts (DAWN_UNREACHABLE) on iOS.
    The Metal BC pixel formats exist on iOS 16.4+ (we target 17), so map them there as well.
    The cloud renderer needs BC4."""
    path = os.path.join(source_dir, "src", "dawn", "native", "metal", "UtilsMetal.mm")
    with open(path) as f:
        text = f.read()
    old = "#if DAWN_PLATFORM_IS(MACOS)\n        case wgpu::TextureFormat::BC1RGBAUnorm:"
    new = "#if DAWN_PLATFORM_IS(MACOS) || DAWN_PLATFORM_IS(IOS)\n        case wgpu::TextureFormat::BC1RGBAUnorm:"
    if text.count(old) != 1:
        fail(f"Cannot apply the iOS BC format patch to {path}; the Dawn source changed")
    with open(path, "w") as f:
        f.write(text.replace(old, new))
    log("Patched Dawn: BC texture formats mapped on iOS")


def main():
    parser = argparse.ArgumentParser(description="Install Dawn WebGPU library from source")
    parser.add_argument("--extern-dir", required=True, help="External dependencies directory")
    parser.add_argument("--dawn-version", required=True, help="Dawn version to install")
    parser.add_argument("--cmake-path", default="cmake", help="Path to CMake executable")
    parser.add_argument("--ninja-path", default="ninja", help="Path to Ninja executable")
    parser.add_argument("--platform", default="native", choices=["native", *CROSS_PLATFORMS],
                        help="Target platform (default: the host)")
    parser.add_argument("--build-types", default="Debug,Release", help="Comma-separated build types")
    args = parser.parse_args()

    extern_dir = os.path.abspath(args.extern_dir)
    dawn_dir = os.path.join(extern_dir, "dawn")
    cross = args.platform != "native"
    # Cross builds keep their sources and build trees in a subdirectory of their own, so the
    # native installation in extern/dawn survives.
    work_dir = os.path.join(dawn_dir, f"src-{args.platform}") if cross else dawn_dir

    tmp_dir = tempfile.mkdtemp(prefix="installdawn_")
    zip_name = f"v{args.dawn_version}.zip"
    zip_path = os.path.join(tmp_dir, zip_name)
    url = f"https://github.com/google/dawn/archive/refs/tags/{zip_name}"

    try:
        download(url, zip_path)
        extract_zip(zip_path, extern_dir)
        os.unlink(zip_path)

        extracted_dir = None
        for entry in os.listdir(extern_dir):
            full = os.path.join(extern_dir, entry)
            if os.path.isdir(full) and entry.startswith("dawn-"):
                extracted_dir = full
                break

        if not extracted_dir:
            fail("Cannot find extracted dawn-* directory")

        if os.path.exists(work_dir):
            log(f"Removing existing Dawn directory: {work_dir}")
            shutil.rmtree(work_dir)

        log(f"Moving extracted Dawn to {work_dir}")
        os.makedirs(os.path.dirname(work_dir), exist_ok=True)
        shutil.move(extracted_dir, work_dir)

        if cross:
            patch_dawn_for_ios(work_dir)

        for build_type in args.build_types.split(","):
            log(f"Building Dawn ({args.platform}, {build_type} configuration)")

            out_dir = os.path.join(work_dir, "out", build_type)
            install_name = f"{args.platform}-{build_type}" if cross else build_type
            install_prefix = os.path.join(dawn_dir, "install", install_name)
            os.makedirs(out_dir, exist_ok=True)

            cmake_args = [
                args.cmake_path,
                "-G", "Ninja",
                work_dir,
                "-B", out_dir,
                "-DDAWN_BUILD_MONOLITHIC_LIBRARY=STATIC",
                "-DDAWN_FORCE_SYSTEM_COMPONENT_LOAD=ON",
                "-DDAWN_FETCH_DEPENDENCIES=ON",
                "-DDAWN_ENABLE_INSTALL=ON",
                f"-DCMAKE_BUILD_TYPE={build_type}",
                "-DTINT_BUILD_SPV_READER=OFF",
                "-DTINT_BUILD_TESTS=OFF",
                "-DTINT_BUILD_FUZZERS=OFF",
                "-DTINT_BUILD_BENCHMARKS=OFF",
                "-DTINT_BUILD_AS_OTHER_OS=OFF",
                "-DDAWN_BUILD_SAMPLES=OFF",
                "-DDAWN_ENABLE_D3D11=OFF",
                "-DDAWN_ENABLE_D3D12=OFF",
                f"-DDAWN_ENABLE_METAL={'ON' if cross else 'OFF'}",
                "-DDAWN_ENABLE_NULL=OFF",
                "-DDAWN_ENABLE_DESKTOP_GL=OFF",
                "-DDAWN_ENABLE_OPENGLES=OFF",
                f"-DDAWN_ENABLE_VULKAN={'OFF' if cross else 'ON'}",
                "-DDAWN_USE_WINDOWS_UI=OFF",
                "-DDAWN_USE_GLFW=OFF"
            ]
            if cross:
                # Executables become app bundles on iOS, which Tint's install rules do not
                # handle, and protobuf would build a host tool for the target. The library
                # needs neither.
                cmake_args += CROSS_PLATFORMS[args.platform] + [
                    "-DCMAKE_OSX_ARCHITECTURES=arm64",
                    f"-DCMAKE_OSX_DEPLOYMENT_TARGET={IOS_DEPLOYMENT_TARGET}",
                    "-DTINT_BUILD_CMD_TOOLS=OFF",
                    "-DDAWN_BUILD_PROTOBUF=OFF",
                    "-DDAWN_BUILD_TESTS=OFF",
                ]

            run_command(
                cmake_args,
                description=f"Configuring Dawn ({build_type})"
            )

            run_command(
                [args.cmake_path, "--build", out_dir],
                description=f"Building Dawn ({build_type})"
            )

            run_command(
                [args.cmake_path, "--install", out_dir, "--prefix", install_prefix],
                description=f"Installing Dawn ({build_type})"
            )

        log("Cleaning up Dawn build files and sources")
        if cross:
            shutil.rmtree(work_dir, ignore_errors=True)
        else:
            for entry in os.listdir(dawn_dir):
                if entry != "install":
                    full_path = os.path.join(dawn_dir, entry)
                    if os.path.isdir(full_path):
                        shutil.rmtree(full_path, ignore_errors=True)
                    else:
                        os.remove(full_path)

        log(f"Successfully installed Dawn to {dawn_dir}/install")
        return 0

    except Exception as e:
        log(f"Installation failed: {e}")
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)
        sys.exit(1)

    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
