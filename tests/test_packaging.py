import re
import unittest
from pathlib import Path

import srtat

ROOT = Path(__file__).resolve().parent.parent


def _pyproject_text() -> str:
    return (ROOT / "pyproject.toml").read_text(encoding="utf-8")


class PackagingTests(unittest.TestCase):
    # The version lives in both pyproject.toml and srtat/__init__.py. Nothing
    # else keeps them in step, and a mismatch only shows up after upload.
    def test_pyproject_version_matches_package_version(self):
        match = re.search(r'^version\s*=\s*"([^"]+)"', _pyproject_text(), re.MULTILINE)
        self.assertIsNotNone(match, "no version line in pyproject.toml")
        self.assertEqual(match.group(1), srtat.__version__)

    def test_version_is_plain_release_number(self):
        self.assertRegex(srtat.__version__, r"^\d+\.\d+\.\d+$")

    def test_py_typed_marker_ships_with_package(self):
        package_dir = Path(srtat.__file__).resolve().parent
        self.assertTrue((package_dir / "py.typed").is_file())
        self.assertIn('srtat = ["py.typed"]', _pyproject_text())

    def test_readme_and_license_exist_for_sdist(self):
        self.assertTrue((ROOT / "README.md").is_file())
        self.assertTrue((ROOT / "LICENSE").is_file())

    def test_console_script_target_is_importable(self):
        match = re.search(r'^srtat\s*=\s*"([\w.]+):(\w+)"', _pyproject_text(), re.MULTILINE)
        self.assertIsNotNone(match, "no srtat console script in pyproject.toml")
        module = __import__(match.group(1), fromlist=[match.group(2)])
        self.assertTrue(callable(getattr(module, match.group(2))))


if __name__ == "__main__":
    unittest.main()
