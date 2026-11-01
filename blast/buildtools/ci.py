# Copyright (c) Contributors to the Open 3D Engine Project.
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""Build and validate an installed Blast runtime SDK in GitHub Actions."""

import argparse
import os
from pathlib import Path
import platform
import plistlib
import struct
import subprocess
import time


ROOT = Path(__file__).resolve().parents[2]
HOST_BUILD = ROOT / "out/blast-host-tools" / (platform.system().lower() + "-" + platform.machine().lower())
CONFIGURATIONS = ("Debug", "Checked", "Profile", "Release")
TARGETS = ("android-arm", "android-x64", "ios-arm", "ios-simulator-arm", "ios-simulator-x64",
           "linux-arm", "linux-x64", "mac-arm", "mac-x64", "windows-arm", "windows-x64")


def relocate_sdk(source, destination):
    # Windows indexers can briefly hold newly installed SDK files open.
    for attempt in range(5):
        try:
            source.rename(destination)
            return
        except PermissionError:
            if os.name != "nt" or attempt == 4:
                raise
            time.sleep(0.2 * (attempt + 1))


def run(command, log):
    log.parent.mkdir(parents=True, exist_ok=True)
    print("Running: " + " ".join(map(str, command)), flush=True)
    with log.open("w") as stream:
        result = subprocess.run(list(map(str, command)), stdout=stream, stderr=subprocess.STDOUT)
    print(log.read_text(errors="replace"), flush=True)
    result.check_returncode()


def target_arguments(target):
    if target == "windows-arm":
        return ["-DCMAKE_SYSTEM_NAME=Windows", "-DCMAKE_SYSTEM_PROCESSOR=ARM64"]
    if target == "linux-arm":
        return ["-DCMAKE_TOOLCHAIN_FILE=" + str(ROOT / "physx/buildtools/cmake/linux-aarch64-cross.cmake")]
    if target.startswith("android-"):
        abi = "arm64-v8a" if target.endswith("arm") else "x86_64"
        ndk = Path(os.environ["ANDROID_NDK_HOME"])
        return ["-DCMAKE_TOOLCHAIN_FILE=" + str(ndk / "build/cmake/android.toolchain.cmake"),
                "-DANDROID_ABI=" + abi, "-DANDROID_PLATFORM=android-29", "-DANDROID_STL=c++_shared"]
    if target.startswith(("mac-", "ios-")):
        arch = "arm64" if target.endswith("arm") else "x86_64"
        sdk = "macosx"
        args = ["-DCMAKE_OSX_ARCHITECTURES=" + arch, "-DCMAKE_XCODE_ATTRIBUTE_CODE_SIGNING_ALLOWED=NO"]
        if target.startswith("ios-"):
            sdk = "iphonesimulator" if "simulator" in target else "iphoneos"
            args += ["-DCMAKE_SYSTEM_NAME=iOS", "-DCMAKE_OSX_DEPLOYMENT_TARGET=14.0"]
        else:
            args += ["-DCMAKE_OSX_DEPLOYMENT_TARGET=11.0"]
        return args + ["-DCMAKE_OSX_SYSROOT=" + sdk]
    return []


def native_target(target):
    machine = platform.machine().lower()
    architecture = {"amd64": "x64", "x86_64": "x64", "aarch64": "arm", "arm64": "arm"}.get(machine)
    system = {"Windows": "windows", "Linux": "linux", "Darwin": "mac"}.get(platform.system())
    return target == f"{system}-{architecture}"


def inspect_binary(binary, target, log):
    data = binary.read_bytes()[:4096]
    arm = target.endswith("arm")
    if target.startswith("windows-"):
        pe = struct.unpack_from("<I", data, 60)[0]
        expected = 0xAA64 if arm else 0x8664
        if data[:2] != b"MZ" or data[pe:pe + 4] != b"PE\0\0" or struct.unpack_from("<H", data, pe + 4)[0] != expected:
            raise RuntimeError("Unexpected PE architecture: " + str(binary))
        log.write_text("Verified PE architecture: " + str(binary) + "\n")
    elif target.startswith(("linux-", "android-")):
        expected = 183 if arm else 62
        if data[:6] != b"\x7fELF\x02\x01" or struct.unpack_from("<H", data, 18)[0] != expected:
            raise RuntimeError("Unexpected ELF architecture: " + str(binary))
        run(["readelf", "-d", binary], log)
    else:
        expected = 0x100000C if arm else 0x1000007
        if data[:4] != b"\xcf\xfa\xed\xfe" or struct.unpack_from("<I", data, 4)[0] != expected:
            raise RuntimeError("Unexpected Mach-O architecture: " + str(binary))
        run(["xcrun", "vtool", "-show-build", binary], log)
        metadata = log.read_text()
        sdk = "MACOS"
        if target.startswith("ios-"):
            sdk = "IOSSIMULATOR" if "simulator" in target else "IOS"
        if not any(line.strip() == "platform " + sdk for line in metadata.splitlines()):
            raise RuntimeError("Unexpected Apple SDK metadata: " + metadata)
        if binary.parent.suffix == ".framework":
            info = plistlib.loads((binary.parent / "Info.plist").read_bytes())
            if not info.get("CFBundleVersion") or not info.get("CFBundleShortVersionString"):
                raise RuntimeError("Missing framework version metadata: " + str(binary))
        run(["otool", "-L", binary], log.with_suffix(".dependencies.log"))


def build_host_tools(output):
    host = HOST_BUILD
    run(["cmake", "-S", ROOT / "blast", "-B", host, "-G", "Ninja",
         "-DBLAST_BUILD_HOST_TOOLS=ON", "-DCMAKE_BUILD_TYPE=Release"], output / "host-configure.log")
    run(["cmake", "--build", host, "--target", "capnp_tool", "capnpc_cpp", "--parallel", "4"], output / "host-build.log")


def build_runtime(target, linkage):
    host = HOST_BUILD
    capnp, plugin = (host / "tools-Release.txt").read_text().splitlines()
    options = target_arguments(target)
    generator = "Xcode" if target.startswith(("mac-", "ios-")) else "Ninja"
    failed = False
    for config in CONFIGURATIONS:
        output = ROOT / "out/blast" / target / linkage / config.lower()
        build, sdk, logs = output / "build", output / "install", output / "logs"
        consumer = output / "consumer"
        try:
            run(["cmake", "-S", ROOT / "blast", "-B", build, "-G", generator, *options,
                 "-DCMAKE_BUILD_TYPE=" + config, "-DCMAKE_INSTALL_PREFIX=" + str(sdk),
                 "-DBUILD_SHARED_LIBS=" + ("ON" if linkage == "shared" else "OFF"),
                 "-DBLAST_CAPNP_EXECUTABLE=" + capnp, "-DBLAST_CAPNPC_CXX_EXECUTABLE=" + plugin,
                 "-DFETCHCONTENT_SOURCE_DIR_CAPNPROTO=" + str(host / "_deps/capnproto-src")], logs / "configure.log")
            run(["cmake", "--build", build, "--config", config, "--parallel", "4"], logs / "build.log")
            run(["cmake", "--install", build, "--config", config], logs / "install.log")
            # Consume a relocated SDK to catch paths back into the source/build tree.
            relocated = output / "relocated-sdk"
            relocate_sdk(sdk, relocated)
            try:
                run(["cmake", "-S", ROOT / "blast/tests/runtime", "-B", consumer, "-G", generator, *options,
                     "-DCMAKE_BUILD_TYPE=" + config, "-DCMAKE_PREFIX_PATH=" + str(relocated)], logs / "consumer-configure.log")
                run(["cmake", "--build", consumer, "--config", config, "--parallel", "4"], logs / "consumer-build.log")
                executable = Path((consumer / f"consumer-{config}.txt").read_text().strip())
                binaries = [executable, *relocated.rglob("*.dll"), *relocated.rglob("*.so"), *relocated.rglob("*.dylib")]
                binaries += [f / f.stem for f in relocated.rglob("*.framework")]
                for i, binary in enumerate(binaries):
                    inspect_binary(binary, target, logs / f"binary-{i}.log")
                if native_target(target):
                    run(["ctest", "--test-dir", consumer, "-C", config, "--output-on-failure",
                         "--output-junit", logs / "runtime.xml"], logs / "runtime.log")
                else:
                    (logs / "runtime.log").write_text("Cross-target consumer linked. Runtime requires a compatible host.\n")
            finally:
                relocate_sdk(relocated, sdk)
        except subprocess.CalledProcessError:
            failed = True
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=TARGETS, required=True)
    parser.add_argument("--linkage", choices=("static", "shared"), required=True)
    parser.add_argument("--host-tools", action="store_true")
    args = parser.parse_args()
    if args.host_tools:
        build_host_tools(ROOT / "out/blast" / args.target / args.linkage / "host/logs")
    else:
        build_runtime(args.target, args.linkage)
