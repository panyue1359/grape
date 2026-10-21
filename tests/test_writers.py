import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from pinkviewer.model import load_dataset, load_ntl_timeseries
from pinkviewer.writers import write_dataset, write_xdmf_timeseries


FIXTURES = Path(__file__).parent / "fixtures"


class WriterTests(unittest.TestCase):
    def test_velocity_and_scalar_series_write_vectors_with_exact_values(self):
        dataset = load_dataset(FIXTURES / "shuffled.inp")
        velocity = load_ntl_timeseries(FIXTURES / "velocity_timeseries.ntl", dataset.source_id_to_index)
        scalar = load_ntl_timeseries(FIXTURES / "shuffled_timeseries.ntl", dataset.source_id_to_index)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "mixed.xdmf"
            write_xdmf_timeseries(dataset, [velocity, scalar], output)
            steps = ET.parse(output).findall(".//Grid[@GridType='Uniform']")
            self.assertEqual(len(steps), 2)
            for step in steps:
                vector = step.find("Attribute[@Name='VELOCITY']")
                self.assertEqual(vector.attrib["AttributeType"], "Vector")
                self.assertEqual(vector.find("DataItem").attrib["Dimensions"], "3 3")
                self.assertEqual(step.find("Attribute[@Name='Temperature']").attrib["AttributeType"], "Scalar")
            import h5py
            with h5py.File(output.with_suffix(".h5"), "r") as h5:
                self.assertEqual(h5["/TimeSeries/Field_0000/Step_0000"][:].tolist(), [[4, -5, 6], [1, 2, 3], [7, 8, 9]])
                self.assertEqual(h5["/TimeSeries/Field_0000/Step_0001"][:].tolist(), [[40, 50, 60], [10, 20, 30], [70, 80, 90]])
                self.assertEqual(h5["/TimeSeries/Field_0001/Step_0001"][:].tolist(), [40, 10, 30])

    def test_xdmf_time_series_writes_step_values_and_temporal_collection(self):
        dataset = load_dataset(FIXTURES / "shuffled.inp")
        series = load_ntl_timeseries(FIXTURES / "shuffled_timeseries.ntl", dataset.source_id_to_index)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "series.xdmf"
            write_xdmf_timeseries(dataset, series, output)
            root = ET.parse(output).getroot()
            collection = root.find(".//Grid[@CollectionType='Temporal']")
            steps = collection.findall("Grid")
            self.assertEqual([step.find("Time").attrib["Value"] for step in steps], ["0", "1"])
            self.assertEqual([step.find("Attribute").attrib["Name"] for step in steps], ["Temperature", "Temperature"])
            import h5py
            with h5py.File(output.with_suffix(".h5"), "r") as h5:
                self.assertEqual(h5["/TimeSeries/Step_0000"][:].tolist(), [4.0, 1.0, 3.0])
                self.assertEqual(h5["/TimeSeries/Step_0001"][:].tolist(), [40.0, 10.0, 30.0])

    def test_vtk_and_vtu_write_mapped_connectivity(self):
        dataset = load_dataset(FIXTURES / "shuffled.inp")
        with tempfile.TemporaryDirectory() as directory:
            vtk = Path(directory) / "mesh.vtk"
            vtu = Path(directory) / "mesh.vtu"
            write_dataset(dataset, vtk, "vtk")
            write_dataset(dataset, vtu, "vtu")
            vtk_text = vtk.read_text(encoding="utf-8")
            self.assertIn("3 0 1 2", vtk_text)
            self.assertIn("SCALARS source_element_id long 1", vtk_text)
            self.assertIn("700\n", vtk_text)
            root = ET.parse(vtu).getroot()
            connectivity = root.findtext(".//Cells/DataArray[@Name='connectivity']")
            self.assertEqual(connectivity.split(), ["0", "1", "2"])
            source_ids = root.findtext(".//PointData/DataArray[@Name='source_node_id']")
            self.assertEqual(source_ids.split(), ["40", "10", "90"])

    def test_writer_refuses_to_overwrite_existing_output(self):
        dataset = load_dataset(FIXTURES / "shuffled.inp")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "mesh.vtk"
            output.write_text("user data", encoding="utf-8")
            with self.assertRaisesRegex(FileExistsError, "refusing to overwrite"):
                write_dataset(dataset, output, "vtk")
            self.assertEqual(output.read_text(encoding="utf-8"), "user data")
            source_ids = root.findtext(".//PointData/DataArray[@Name='source_node_id']")
            self.assertEqual(source_ids.split(), ["40", "10", "90"])

    def test_writer_refuses_to_overwrite_existing_output(self):
        dataset = load_dataset(FIXTURES / "shuffled.inp")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "mesh.vtk"
            output.write_text("user data", encoding="utf-8")
            with self.assertRaisesRegex(FileExistsError, "refusing to overwrite"):
                write_dataset(dataset, output, "vtk")
            self.assertEqual(output.read_text(encoding="utf-8"), "user data")

    def test_xdmf_reports_missing_hdf5_dependency(self):
        dataset = load_dataset(FIXTURES / "shuffled.inp")
        with tempfile.TemporaryDirectory() as directory:
            try:
                import h5py
            except ImportError:
                with self.assertRaisesRegex(RuntimeError, "requires h5py and numpy"):
                    write_dataset(dataset, Path(directory) / "mesh.xdmf", "xdmf")
                return
            output = Path(directory) / "mesh.xdmf"
            dataset = load_dataset(FIXTURES / "shuffled.inp", [FIXTURES / "shuffled.ntl"])
            write_dataset(dataset, output, "xdmf")
            xml = ET.parse(output).getroot()
            self.assertEqual(xml.find(".//Topology").attrib["TopologyType"], "Triangle")
            with h5py.File(output.with_suffix(".h5"), "r") as h5:
                self.assertEqual(h5["/Mesh/Connectivity"][:].tolist(), [[0, 1, 2]])
                self.assertEqual(h5["/Mesh/SourceNodeIds"][:].tolist(), [40, 10, 90])
                self.assertEqual(h5["/Fields/0"][:].tolist(), [4.0, 1.0, 3.0])


if __name__ == "__main__":
    unittest.main()
