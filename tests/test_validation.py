import tempfile
import unittest
from pathlib import Path

from pinkviewer.model import load_dataset


class ValidationTests(unittest.TestCase):
    def test_nonpositive_node_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.inp"
            path.write_text("*NODE\n0, 0, 0, 0\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid node ID 0"):
                load_dataset(path)

    def test_ntl_duplicate_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inp = root / "mesh.inp"
            inp.write_text("*NODE\n10, 0, 0, 0\n", encoding="utf-8")
            ntl = root / "field.ntl"
            ntl.write_text("Scalar\n1 0 0 0 1\nsource\n10 1.0\n10 2.0\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate NTL node ID 10"):
                load_dataset(inp, [ntl])

    def test_ntl_missing_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inp = root / "mesh.inp"
            inp.write_text("*NODE\n10, 0, 0, 0\n20, 1, 0, 0\n", encoding="utf-8")
            ntl = root / "field.ntl"
            ntl.write_text("Scalar\n2 0 0 0 1\nsource\n10 1.0\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, r"missing \[20\]"):
                load_dataset(inp, [ntl])


if __name__ == "__main__":
    unittest.main()
