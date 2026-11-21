"""
Automated unit tests for Lateralus package registry MVP tooling.
"""

import os
import shutil
import unittest
from pathlib import Path
from tools.registry.registry import publish_package, add_package, compute_sha256


class TestPackageRegistry(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("tools/registry/tests/scratch")
        self.test_dir.mkdir(parents=True, exist_ok=True)

        self.proj_dir = self.test_dir / "sample_pkg"
        self.proj_dir.mkdir(parents=True, exist_ok=True)
        (self.proj_dir / "lateralus.toml").write_text(
            "[package]\nname = \"sample-pkg\"\nversion = \"0.1.0\"\n", encoding="utf-8"
        )
        (self.proj_dir / "lib.ltl").write_text("fn sample() {} \n", encoding="utf-8")

        self.registry_dir = self.test_dir / "registry"
        self.workspace_dir = self.test_dir / "workspace"
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_publish_and_add(self):
        digest = publish_package(str(self.proj_dir), str(self.registry_dir))
        self.assertTrue(digest)
        self.assertTrue((self.registry_dir / "index.json").exists())

        add_package("sample-pkg", "0.1.0", str(self.registry_dir), str(self.workspace_dir))

        vendor_file = self.workspace_dir / "vendor" / "sample-pkg" / "lib.ltl"
        self.assertTrue(vendor_file.exists())
        self.assertEqual(vendor_file.read_text(encoding="utf-8"), "fn sample() {} \n")

        lock_file = self.workspace_dir / "lateralus-lock.json"
        self.assertTrue(lock_file.exists())


if __name__ == "__main__":
    unittest.main()
