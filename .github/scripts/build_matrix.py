import json
import os


TARGETS = {
    "android-arm": ("ubuntu-22.04", "android-arm64-v8a"),
    "android-x64": ("ubuntu-22.04", "android-x64"),
    "ios-arm": ("macos-15", "ios64"),
    "ios-simulator-arm": ("macos-15", "ios-simulator-arm64"),
    "ios-simulator-x64": ("macos-15", "ios-simulator-x64"),
    "linux-arm": ("ubuntu-22.04", "linux-aarch64-crosscompile"),
    "linux-x64": ("ubuntu-22.04", "linux-clang"),
    "mac-arm": ("macos-15", "mac-arm64"),
    "mac-x64": ("macos-15", "mac64"),
    "windows-arm": ("windows-2022", "vc17win-arm"),
    "windows-x64": ("windows-2022", "vc17win64"),
}
GPU_TARGETS = {"linux-arm", "linux-x64", "windows-x64"}


if __name__ == "__main__":
    inputs = json.loads(os.environ["INPUTS"])
    jobs = [
        dict(target=target, runner=runner, preset=preset, linkage=linkage, gpu=target in GPU_TARGETS)
        for target, (runner, preset) in TARGETS.items()
        if inputs[target]
        for linkage in ("static", "shared")
    ]
    if not jobs:
        raise SystemExit("Select at least one target platform")
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"matrix={json.dumps({'include': jobs})}\n")
