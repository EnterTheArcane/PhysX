import os
from pathlib import Path
import platform
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
CONFIGURATIONS = ("debug", "checked", "profile", "release")


def configure_environment(target):
    if target.startswith(("mac-", "ios-")):
        if platform.machine() != "arm64":
            raise SystemExit("Apple builds require an ARM64 host")
        os.environ["DEVELOPER_DIR"] = subprocess.check_output(["xcode-select", "--print-path"], text=True).strip()
        subprocess.run(["xcodebuild", "-version"], check=True)
    elif target.startswith("android-"):
        ndk = Path(os.environ.get("ANDROID_NDK_LATEST_HOME") or os.environ.get("ANDROID_NDK_HOME", ""))
        if not (ndk / "build/cmake/android.toolchain.cmake").is_file():
            raise SystemExit("Set ANDROID_NDK_HOME to an installed Android NDK")
        os.environ["ANDROID_NDK_HOME"] = str(ndk)
        print((ndk / "source.properties").read_text(encoding="utf-8"), flush=True)
    elif target.startswith("linux-"):
        os.environ.update(CC="clang", CXX="clang++")


def build_configuration(target, preset, linkage, gpu, config):
    output = ROOT / "out" / target / linkage / config
    build = output / "build"
    logs = output / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    generator = "Xcode" if target.startswith(("mac-", "ios-")) else "Ninja"
    options = {
        "PHYSX_PRESET": preset,
        "CMAKE_BUILD_TYPE": config,
        "CMAKE_INSTALL_PREFIX": output / "install",
        "PX_OUTPUT_LIB_DIR": build,
        "PX_OUTPUT_BIN_DIR": build,
        "PX_OUTPUT_DLL_DIR": build,
        "PX_GENERATE_STATIC_LIBRARIES": "ON" if linkage == "static" else "OFF",
        "PX_BUILDPVDRUNTIME": "ON" if target.startswith(("windows-", "linux-")) else "OFF",
        "PX_BUILDSNIPPETS": "OFF",
        "PX_GENERATE_GPU_PROJECTS": "ON" if gpu else "OFF",
        "PX_GENERATE_GPU_PROJECTS_ONLY": "OFF",
        "PX_GENERATE_GPU_STATIC_LIBRARIES": "OFF",
        "NV_USE_STATIC_WINCRT": "OFF",
        "NV_USE_DEBUG_WINCRT": "ON",
        "CMAKE_XCODE_ATTRIBUTE_CODE_SIGNING_ALLOWED": "NO",
    }
    verify = [sys.executable, ROOT / "physx/buildtools/tests/verify_installed_sdk.py", target, linkage, config, output]
    if gpu:
        verify.append("--gpu")
    commands = {
        "configure": ["cmake", "-S", ROOT / "physx", "-B", build, "-G", generator,
                      *(f"-D{name}={value}" for name, value in options.items())],
        "build": ["cmake", "--build", build, "--config", config, "--parallel", "4"],
        "install": ["cmake", "--install", build, "--config", config],
        "consumer": verify,
    }

    for step, command in commands.items():
        print(f"{target} {linkage} {config}: {step}", flush=True)
        log = logs / f"{step}.log"
        with log.open("w") as stream:
            result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode:
            print(log.read_text(errors="replace"), flush=True)
            return False
    return True


def main():
    target = os.environ["TARGET"]
    preset = os.environ["PRESET"]
    linkage = os.environ["LINKAGE"]
    gpu = os.environ["GPU"] == "true"
    configure_environment(target)
    failed = False
    for config in CONFIGURATIONS:
        if not build_configuration(target, preset, linkage, gpu, config):
            failed = True
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
