# SPDX-License-Identifier: Apache-2.0

import argparse
import os
import platform
import plistlib
import shutil
import struct
import subprocess
from pathlib import Path


def target_options(target, physx_root):
    if target == 'windows-arm':
        return ['-DCMAKE_SYSTEM_NAME=Windows', '-DCMAKE_SYSTEM_PROCESSOR=ARM64']
    if target == 'linux-arm':
        return [f'-DCMAKE_TOOLCHAIN_FILE={physx_root / "buildtools/cmake/linux-aarch64-cross.cmake"}']
    if target.startswith('android-'):
        abi = 'arm64-v8a' if target.endswith('-arm') else 'x86_64'
        return [f'-DCMAKE_TOOLCHAIN_FILE={physx_root / "buildtools/cmake/android-ndk.cmake"}',
                f'-DANDROID_ABI={abi}', '-DANDROID_PLATFORM=android-29']
    if target.startswith(('mac-', 'ios-')):
        arch = 'arm64' if target.endswith('-arm') else 'x86_64'
        options = [f'-DCMAKE_OSX_ARCHITECTURES={arch}', '-DCMAKE_XCODE_ATTRIBUTE_CODE_SIGNING_ALLOWED=NO']
        if target.startswith('ios-'):
            sdk = 'iphonesimulator' if '-simulator-' in target else 'iphoneos'
            options += ['-DCMAKE_SYSTEM_NAME=iOS', f'-DCMAKE_OSX_SYSROOT={sdk}', '-DCMAKE_OSX_DEPLOYMENT_TARGET=14.0']
        else:
            options += ['-DCMAKE_OSX_SYSROOT=macosx', '-DCMAKE_OSX_DEPLOYMENT_TARGET=11.0']
        return options
    return []


def inspect_binary(binary, target):
    with binary.open('rb') as stream:
        header = stream.read(64)
        arm = target.endswith('-arm')
        if target.startswith('windows-'):
            expected = 0xAA64 if arm else 0x8664
            stream.seek(struct.unpack_from('<I', header, 60)[0])
            valid = header[:2] == b'MZ' and stream.read(6) == b'PE\0\0' + struct.pack('<H', expected)
        elif target.startswith(('android-', 'linux-')):
            expected = 183 if arm else 62
            valid = header[:6] == b'\x7fELF\x02\x01' and struct.unpack_from('<H', header, 18)[0] == expected
            dependencies = subprocess.check_output(['readelf', '-d', str(binary)], text=True)
            if binary.name.startswith('libPhysXGpu') and 'libcudart.so' in dependencies:
                raise RuntimeError(f'GPU plugin depends on the CUDA runtime: {binary}')
            print(dependencies, flush=True)
        else:
            expected = 0x0100000C if arm else 0x01000007
            valid = header[:4] == b'\xcf\xfa\xed\xfe' and struct.unpack_from('<I', header, 4)[0] == expected
            sdk = 'MACOS'
            if target.startswith('ios-'):
                sdk = 'IOSSIMULATOR' if '-simulator-' in target else 'IOS'
            metadata = subprocess.check_output(['xcrun', 'vtool', '-show-build', str(binary)], text=True)
            valid = valid and any(line.split() == ['platform', sdk] for line in metadata.splitlines())
            subprocess.run(['otool', '-L', str(binary)], check=True)
    if not valid:
        raise RuntimeError(f'Unexpected {target} binary: {binary}')
    print(f'Verified {target}: {binary}', flush=True)


def verify(target, linkage, gpu, config, output):
    sdk = output / 'install'
    build = output / 'consumer-build'
    source = Path(__file__).resolve().with_name('installed_sdk')
    physx_root = source.parents[2]
    package = next(sdk.glob('lib*/cmake/PhysX/PhysXConfig.cmake')).parent
    subprocess.run([
        'cmake', '-S', str(source), '-B', str(build), '-G', 'Ninja',
        f'-DCMAKE_BUILD_TYPE={config}', '-DCMAKE_DISABLE_FIND_PACKAGE_CUDAToolkit=ON',
        f'-DEXPECT_GPU={int(gpu)}', f'-DEXPECT_STATIC={int(linkage == "static")}',
        f'-DPhysX_DIR={package}', *target_options(target, physx_root),
    ], check=True)
    subprocess.run(['cmake', '--build', str(build), '--parallel', '2'], check=True)

    exe = Path((build / f'exe-{config}.txt').read_text())
    plugin = Path((build / 'gpu-path.txt').read_text()) if gpu else None
    if plugin:
        expected_name = 'PhysXGpu_64.dll' if target.startswith('windows-') else 'libPhysXGpu_64.so'
        if plugin.name != expected_name:
            raise RuntimeError(f'GPU loader expects {expected_name}, SDK installs {plugin.name}')
    inspect_binary(exe, target)
    for pattern in ('*.dll', '*.so', '*.dylib', '*.framework'):
        for library in sdk.rglob(pattern):
            if library.suffix == '.framework':
                version = '.'.join((physx_root / 'version.txt').read_text().strip().split('.')[:3])
                with (library / 'Info.plist').open('rb') as stream:
                    metadata = plistlib.load(stream)
                if any(metadata.get(key) != version for key in ('CFBundleVersion', 'CFBundleShortVersionString')):
                    raise RuntimeError(f'Framework is missing the SDK version {version}: {library}')
                library = library / library.stem
            inspect_binary(library, target)

    host_os = {'Darwin': 'mac', 'Windows': 'windows', 'Linux': 'linux'}.get(platform.system())
    host_arch = {'arm64': 'arm', 'aarch64': 'arm', 'amd64': 'x64', 'x86_64': 'x64'}.get(platform.machine().lower())
    if target != f'{host_os}-{host_arch}':
        return

    if target.startswith('windows-'):
        for dll in (sdk / 'bin').glob('*.dll'):
            shutil.copy2(dll, exe.parent / dll.name)
        if plugin:
            plugin = exe.parent / plugin.name

    env = os.environ.copy()
    cuda = env.get('PM_CUDA_PATH') or env.get('CUDA_PATH')
    if cuda:
        cuda_root = Path(cuda).resolve()
        for variable in ('PATH', 'LD_LIBRARY_PATH'):
            if variable in env:
                env[variable] = os.pathsep.join(p for p in env[variable].split(os.pathsep)
                                                if not Path(p).resolve().is_relative_to(cuda_root))
    subprocess.run([str(exe)], cwd=exe.parent, env=env, check=True, timeout=120)
    if plugin:
        hidden = plugin.with_suffix(plugin.suffix + '.unused')
        plugin.rename(hidden)
        try:
            subprocess.run([str(exe)], cwd=exe.parent, env=env, check=True, timeout=120)
        finally:
            hidden.rename(plugin)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Verify an installed PhysX SDK with a standalone consumer.')
    parser.add_argument('target')
    parser.add_argument('linkage', choices=['static', 'shared'])
    parser.add_argument('config', choices=['debug', 'checked', 'profile', 'release'])
    parser.add_argument('output', type=Path)
    parser.add_argument('--gpu', action='store_true')
    args = parser.parse_args()
    verify(args.target, args.linkage, args.gpu, args.config, args.output.resolve())
