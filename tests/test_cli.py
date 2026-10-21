import subprocess
import sys
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


class CliTests(unittest.TestCase):
    def test_velocity_inspect_and_batch_merge_with_scalar_series(self):
        fixtures = Path(__file__).parent / "fixtures"
        result = subprocess.run(
            [sys.executable, "-m", "pinkviewer", "inspect", str(fixtures / "shuffled.inp"), str(fixtures / "velocity_timeseries.ntl")],
            text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        info = json.loads(result.stdout)["ntl"][0]
        self.assertEqual((info["components"], info["steps"], info["name"]), (3, 2, "VELOCITY"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "jobs.json"
            manifest.write_text(json.dumps([{
                "inp": str((fixtures / "shuffled.inp").resolve()),
                "output": "mixed.xdmf", "format": "xdmf",
                "ntl": [str((fixtures / name).resolve()) for name in ("velocity_timeseries.ntl", "shuffled_timeseries.ntl")],
            }]), encoding="utf-8")
            result = subprocess.run([sys.executable, "-m", "pinkviewer", "batch", str(manifest)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            attribute = ET.parse(root / "mixed.xdmf").find(".//Attribute[@Name='VELOCITY']")
            self.assertEqual(attribute.attrib["AttributeType"], "Vector")
            for fmt in ("vtk", "vtu"):
                rejected = subprocess.run(
                    [sys.executable, "-m", "pinkviewer", "convert", str(fixtures / "shuffled.inp"), str(root / f"velocity.{fmt}"), "--format", fmt, "--ntl", str(fixtures / "velocity_timeseries.ntl")],
                    text=True, capture_output=True,
                )
                self.assertEqual(rejected.returncode, 2, rejected.stderr)
                self.assertIn("requires --format xdmf", rejected.stderr)
                self.assertFalse((root / f"velocity.{fmt}").exists())

    def test_converted_field_names_remove_procast_results(self):
        fixtures = Path(__file__).parent / "fixtures"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for width, formats in ((1, ("vtk", "vtu", "xdmf")), (2, ("xdmf",))):
                ntl = root / f"field_{width}.ntl"
                values = "40 4\n10 1\n90 3\n" if width == 1 else "40 4 40\n10 1 10\n90 3 30\n"
                ntl.write_text(f"ProCAST SHRINKAGE POROSITY RESULTS\n3 0 0 0 {width}\nESI\n{values}", encoding="utf-8")
                for fmt in formats:
                    with self.subTest(width=width, format=fmt):
                        output = root / f"field_{width}.{fmt}"
                        result = subprocess.run(
                            [sys.executable, "-m", "pinkviewer", "convert", str(fixtures / "shuffled.inp"), str(output), "--format", fmt, "--ntl", str(ntl)],
                            text=True, capture_output=True,
                        )
                        self.assertEqual(result.returncode, 0, result.stderr)
                        if fmt == "vtk":
                            self.assertIn("SCALARS SHRINKAGE_POROSITY double 1", output.read_text())
                        else:
                            tree = ET.parse(output)
                            nodes = tree.findall(".//PointData/DataArray") if fmt == "vtu" else tree.findall(".//Attribute")
                            names = [node.attrib["Name"] for node in nodes]
                            self.assertIn("SHRINKAGE POROSITY", names)
                            self.assertFalse(any("ProCAST" in name or "RESULTS" in name for name in names))

    def test_help_lists_all_commands_and_has_no_gui_imports(self):
        result = subprocess.run(
            [sys.executable, "-m", "pinkviewer", "--help"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: grape", result.stdout)
        for command in ("inspect", "validate", "convert", "batch"):
            self.assertIn(command, result.stdout)
        self.assertNotIn("PyQt5", result.stdout + result.stderr)

    def test_batch_processes_manifest_and_rejects_existing_output(self):
        fixtures = Path(__file__).parent / "fixtures"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "mesh.inp").write_bytes((fixtures / "shuffled.inp").read_bytes())
            manifest = root / "jobs.json"
            manifest.write_text(json.dumps([{"inp": "mesh.inp", "output": "mesh.vtu", "format": "vtu"}]), encoding="utf-8")
            success = subprocess.run([sys.executable, "-m", "pinkviewer", "batch", str(manifest)], text=True, capture_output=True)
            self.assertEqual(success.returncode, 0, success.stderr)
            self.assertTrue((root / "mesh.vtu").is_file())
            failure = subprocess.run([sys.executable, "-m", "pinkviewer", "batch", str(manifest)], text=True, capture_output=True)
            self.assertEqual(failure.returncode, 1, failure.stderr)
            self.assertIn("refusing to overwrite", failure.stderr)

    def test_inspect_reports_ntl_classification_from_header_width(self):
        fixtures = Path(__file__).parent / "fixtures"
        result = subprocess.run(
            [sys.executable, "-m", "pinkviewer", "inspect", str(fixtures / "shuffled.inp"), str(fixtures / "shuffled_timeseries.ntl")],
            text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"kind": "time_series"', result.stdout)
        self.assertIn('"components": 1', result.stdout)
        self.assertIn('"steps": 2', result.stdout)

    def test_convert_automatically_selects_time_series_with_ntl(self):
        fixtures = Path(__file__).parent / "fixtures"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "series.xdmf"
            result = subprocess.run(
                [sys.executable, "-m", "pinkviewer", "convert", str(fixtures / "shuffled.inp"), str(output), "--format", "xdmf", "--ntl", str(fixtures / "shuffled_timeseries.ntl")],
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            root = ET.parse(output).getroot()
            collection = root.find(".//Grid[@CollectionType='Temporal']")
            self.assertEqual(len(collection.findall("Grid")), 2)

    def test_timeseries_ntl_rejected_for_vtk_and_multiple_series_merged(self):
        fixtures = Path(__file__).parent / "fixtures"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vtk_result = subprocess.run(
                [sys.executable, "-m", "pinkviewer", "convert", str(fixtures / "shuffled.inp"), str(root / "series.vtk"), "--format", "vtk", "--ntl", str(fixtures / "shuffled_timeseries.ntl")],
                text=True, capture_output=True,
            )
            self.assertEqual(vtk_result.returncode, 2)
            self.assertIn("requires --format xdmf", vtk_result.stderr)
            second_series = root / "second_timeseries.ntl"
            second_series.write_text(
                "VelocityMagnitude\n3 0 0 0 2\nESI\n40 400 4000\n10 100 1000\n90 300 3000\n",
                encoding="utf-8",
            )
            multi_result = subprocess.run(
                [sys.executable, "-m", "pinkviewer", "convert", str(fixtures / "shuffled.inp"), str(root / "series.xdmf"), "--format", "xdmf", "--ntl", str(fixtures / "shuffled_timeseries.ntl"), "--ntl", str(second_series)],
                text=True, capture_output=True,
            )
            self.assertEqual(multi_result.returncode, 0, multi_result.stderr)
            collection = ET.parse(root / "series.xdmf").getroot().find(".//Grid[@CollectionType='Temporal']")
            steps = collection.findall("Grid")
            self.assertEqual(len(steps), 2)
            self.assertEqual([attribute.attrib["Name"] for attribute in steps[0].findall("Attribute")], ["Temperature", "VelocityMagnitude"])
            import h5py
            with h5py.File(root / "series.h5", "r") as h5:
                self.assertEqual(h5["/TimeSeries/Field_0000/Step_0000"][:].tolist(), [4.0, 1.0, 3.0])
                self.assertEqual(h5["/TimeSeries/Field_0001/Step_0001"][:].tolist(), [4000.0, 1000.0, 3000.0])

    def test_time_series_with_different_step_counts_is_rejected(self):
        fixtures = Path(__file__).parent / "fixtures"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shorter = root / "shorter.ntl"
            shorter.write_text("Short\n3 0 0 0 3\nESI\n40 4 40 400\n10 1 10 100\n90 3 30 300\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "pinkviewer", "convert", str(fixtures / "shuffled.inp"), str(root / "bad.xdmf"), "--format", "xdmf", "--ntl", str(fixtures / "shuffled_timeseries.ntl"), "--ntl", str(shorter)],
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("same number of time steps", result.stderr)
            self.assertFalse((root / "bad.xdmf").exists())

    def test_scalar_and_timeseries_ntl_cannot_be_mixed(self):
        fixtures = Path(__file__).parent / "fixtures"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "mixed.xdmf"
            result = subprocess.run(
                [sys.executable, "-m", "pinkviewer", "convert", str(fixtures / "shuffled.inp"), str(output), "--format", "xdmf", "--ntl", str(fixtures / "shuffled.ntl"), "--ntl", str(fixtures / "shuffled_timeseries.ntl")],
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("single-step NTL files cannot be combined", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
