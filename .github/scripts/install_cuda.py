import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request
import zipfile


REDIST_URL = "https://developer.download.nvidia.com/compute/cuda/redist/"


def install_package(name, package_platform, package, root, destination, headers_only):
    with tempfile.TemporaryDirectory(dir=root.parent) as directory:
        temporary = Path(directory)
        relative_path = package["relative_path"]
        archive = temporary / Path(relative_path).name
        urllib.request.urlretrieve(REDIST_URL + relative_path, archive)
        with archive.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != package["sha256"]:
            raise RuntimeError(f"CUDA archive checksum mismatch: {name} for {package_platform}")

        extracted = temporary / "extracted"
        if archive.suffix == ".zip":
            with zipfile.ZipFile(archive) as package_archive:
                package_archive.extractall(extracted)
        else:
            with tarfile.open(archive) as package_archive:
                package_archive.extractall(extracted, filter="data")

        directories = list(extracted.iterdir())
        if len(directories) != 1 or not directories[0].is_dir():
            raise RuntimeError(f"Unexpected CUDA archive layout: {name} for {package_platform}")
        source = directories[0]
        license_dir = root / "licenses" / f"{name}-{package_platform}"
        license_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / "LICENSE", license_dir / "LICENSE")
        if headers_only:
            source /= "include"
            destination /= "include"
        shutil.copytree(source, destination, dirs_exist_ok=True, symlinks=True)
    print(f"Installed {name} for {package_platform}", flush=True)


def main():
    version = os.environ["CUDA_VERSION"]
    with urllib.request.urlopen(f"{REDIST_URL}redistrib_{version}.json") as response:
        manifest = json.load(response)

    host = "windows-x86_64" if os.name == "nt" else "linux-x86_64"
    target = "linux-sbsa" if os.environ["TARGET"] == "linux-arm" else host
    root = Path(os.environ["RUNNER_TEMP"]) / "cuda"
    target_root = root / "targets/sbsa-linux" if target != host else root
    packages = [("cuda_nvcc", host, root, False)]
    packages.extend((name, target, target_root, False) for name in ("cuda_cudart", "cuda_profiler_api", "cuda_cccl"))
    if target != host:
        # Keep the x64 compiler on the host and use only the ARM compiler headers.
        packages.append(("cuda_nvcc", target, target_root, True))
    for name, package_platform, destination, headers_only in packages:
        install_package(name, package_platform, manifest[name][package_platform], root, destination, headers_only)

    if host == target == "linux-x86_64" and not (root / "lib64").exists():
        (root / "lib64").symlink_to("lib", target_is_directory=True)
    nvcc = root / "bin" / ("nvcc.exe" if os.name == "nt" else "nvcc")
    with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as output:
        output.write(f"PM_CUDA_PATH={root.as_posix()}\nCUDA_PATH={root.as_posix()}\nCUDACXX={nvcc.as_posix()}\n")
    with open(os.environ["GITHUB_PATH"], "a", encoding="utf-8") as output:
        output.write(f"{root / 'bin'}\n")


if __name__ == "__main__":
    main()
