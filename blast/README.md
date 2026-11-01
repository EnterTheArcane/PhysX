# Blast SDK Repo

Online documentation may be found here: [Blast SDK Documentation](https://nvidia-omniverse.github.io/PhysX/blast/index.html).

## Building the SDK

For the runtime-only SDK, the manual **Build** GitHub workflow has a `blast` SDK option and platform checkboxes.
To run the same build locally with the platform's compiler environment prepared:

```sh
python blast/buildtools/ci.py --host-tools --target windows-x64 --linkage static
python blast/buildtools/ci.py --target windows-x64 --linkage static
```

This builds all four configurations and validates a relocated installed SDK. Cross-target builds require the corresponding toolchain.

### Windows
1. run `build.bat`
2. built sdk location: `_build\windows-x86_64\release\blast-sdk` (release), `_build\windows-x86_64\debug\blast-sdk` (debug) 

### Linux
0. initialize (once): run `./setup.sh`
1. run `./build.sh`
2. built sdk location: `_build/linux-x86_64/release/blast-sdk` (release), `_build/linux-x86_64/debug/blast-sdk` (debug) 
