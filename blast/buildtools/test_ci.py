# Copyright (c) Contributors to the Open 3D Engine Project.
# SPDX-License-Identifier: Apache-2.0 OR MIT

import unittest
from unittest.mock import Mock, patch

import ci


class CrossCompilationTests(unittest.TestCase):
    def test_sdk_relocation_retries_transient_windows_locks(self):
        source = Mock()
        source.rename.side_effect = [PermissionError(), None]
        with patch("ci.os.name", "nt"), patch("ci.time.sleep"):
            ci.relocate_sdk(source, "destination")
        self.assertEqual(source.rename.call_count, 2)

    def test_sdk_relocation_does_not_hide_persistent_errors(self):
        source = Mock()
        source.rename.side_effect = PermissionError()
        with patch("ci.os.name", "nt"), patch("ci.time.sleep"), self.assertRaises(PermissionError):
            ci.relocate_sdk(source, "destination")
        self.assertEqual(source.rename.call_count, 5)

    def test_runtime_requires_matching_host_and_target(self):
        for system, machine, native in [("Windows", "AMD64", "windows-x64"),
                                         ("Linux", "x86_64", "linux-x64"),
                                         ("Darwin", "arm64", "mac-arm")]:
            with self.subTest(host=system), patch("platform.system", return_value=system), patch("platform.machine", return_value=machine):
                for target in ("windows-x64", "windows-arm", "linux-x64", "linux-arm", "mac-arm", "mac-x64",
                               "android-arm", "android-x64", "ios-arm", "ios-simulator-arm", "ios-simulator-x64"):
                    self.assertEqual(ci.native_target(target), target == native)

    def test_apple_sdk_and_architecture_are_independent(self):
        for target, arch, sdk in [("mac-x64", "x86_64", "macosx"), ("mac-arm", "arm64", "macosx"),
                                  ("ios-arm", "arm64", "iphoneos"), ("ios-simulator-arm", "arm64", "iphonesimulator"),
                                  ("ios-simulator-x64", "x86_64", "iphonesimulator")]:
            with self.subTest(target=target):
                args = ci.target_arguments(target)
                self.assertIn("-DCMAKE_OSX_ARCHITECTURES=" + arch, args)
                self.assertIn("-DCMAKE_OSX_SYSROOT=" + sdk, args)


if __name__ == "__main__":
    unittest.main()
