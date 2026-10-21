import unittest
import tempfile
from pathlib import Path

from pinkviewer.model import load_dataset


FIXTURES = Path(__file__).parent / "fixtures"


class MeshIdMappingTests(unittest.TestCase):
    def test_velocity_classification_and_component_mapping(self):
        from pinkviewer.model import classify_ntl, load_ntl_auto

        path = FIXTURES / "velocity_timeseries.ntl"
        classification = classify_ntl(path)
        self.assertEqual((classification.kind, classification.components, classification.steps), ("time_series", 3, 2))
        series = load_ntl_auto(path, {10: 0, 90: 1, 40: 2}).series
        self.assertEqual(series.name, "VELOCITY")
        self.assertEqual(series.components, 3)
        self.assertEqual(series.times, (0.0, 1.0))
        self.assertEqual(series.values.tolist(), [
            [[1, 2, 3], [7, 8, 9], [4, -5, 6]],
            [[10, 20, 30], [70, 80, 90], [40, 50, 60]],
        ])

    def test_velocity_requires_complete_triplets_and_one_step_stays_vector(self):
        from pinkviewer.model import classify_ntl, load_ntl_auto

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "velocity.ntl"
            path.write_text("ProCAST VELOCITY RESULTS\n1 0 0 0 5\nESI\n40 1 2 3 4 5\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "divisible by 3"):
                classify_ntl(path)
            path.write_text("procast velocity results\n1 0 0 0 3\nESI\n40 1 2 3\n", encoding="utf-8")
            classification = classify_ntl(path)
            self.assertEqual((classification.kind, classification.components, classification.steps), ("time_series", 3, 1))
            self.assertEqual(load_ntl_auto(path, {40: 0}).series.values.tolist(), [[[1, 2, 3]]])
            path.write_text("ProCAST VELOCITY MAGNITUDE RESULTS\n1 0 0 0 3\nESI\n40 1 2 3\n", encoding="utf-8")
            classification = classify_ntl(path)
            self.assertEqual((classification.components, classification.steps), (1, 3))

    def test_velocity_rejects_bad_records(self):
        from pinkviewer.model import load_ntl_auto

        cases = (
            ("40 1 2\n", "fewer than 3"),
            ("40 1 2 3 4\n", "unexpected extra"),
            ("99 1 2 3\n", "unknown node ID"),
            ("40 1 2 3oops\n", "invalid NTL value"),
            ("40 1 2 3\n40 4 5 6\n", "duplicate NTL node ID"),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "velocity.ntl"
            for records, message in cases:
                with self.subTest(records=records):
                    ids = {40: 0, 10: 1} if "duplicate" in message else {40: 0}
                    path.write_text(f"ProCAST VELOCITY RESULTS\n{len(ids)} 0 0 0 3\nESI\n{records}", encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, message):
                        load_ntl_auto(path, ids)

    def test_noncontiguous_node_ids_map_connectivity_and_ntl_by_id(self):
        dataset = load_dataset(FIXTURES / "shuffled.inp", [FIXTURES / "shuffled.ntl"])

        self.assertEqual([node.source_id for node in dataset.nodes], [40, 10, 90])
        self.assertEqual(dataset.source_id_to_index, {40: 0, 10: 1, 90: 2})
        self.assertEqual(dataset.elements[0].connectivity, (0, 1, 2))
        self.assertEqual(dataset.fields[0].values, (4.0, 1.0, 3.0))
        self.assertEqual(dataset.fields[0].name, "Temperature")

    def test_ntl_field_name_uses_words_between_prefix_and_suffix(self):
        from pinkviewer.model import _ntl_field_name

        self.assertEqual(_ntl_field_name("ProCAST SHRINKAGE POROSITY RESULTS", "field"), "SHRINKAGE POROSITY")
        self.assertEqual(_ntl_field_name("Temperature", "field"), "Temperature")
        self.assertEqual(_ntl_field_name("", "field"), "field")
        self.assertEqual(_ntl_field_name("Temperature RESULTS", "field"), "Temperature")
        self.assertEqual(_ntl_field_name("ProCAST Temperature", "field"), "Temperature")
        self.assertEqual(_ntl_field_name(" procast  SHRINKAGE POROSITY results ", "field"), "SHRINKAGE POROSITY")
        self.assertEqual(_ntl_field_name("Maximum Principal Stress", "field"), "Maximum Principal Stress")
        self.assertEqual(_ntl_field_name("ProCAST RESULTS", "field"), "field")

    def test_duplicate_node_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate node ID"):
            load_dataset(FIXTURES / "duplicate_node.inp")

    def test_missing_connectivity_reference_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown node ID 99"):
            load_dataset(FIXTURES / "missing_node.inp")

    def test_unknown_element_type_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported element type 'ALIEN'"):
            load_dataset(FIXTURES / "unknown_element.inp")

    def test_time_series_ntl_maps_all_steps_by_source_node_id(self):
        from pinkviewer.model import load_ntl_timeseries

        series = load_ntl_timeseries(FIXTURES / "shuffled_timeseries.ntl", {40: 0, 10: 1, 90: 2})
        self.assertEqual(series.name, "Temperature")
        self.assertEqual(series.times, (0.0, 1.0))
        self.assertEqual(series.values.tolist(), [[4.0, 1.0, 3.0], [40.0, 10.0, 30.0]])

    def test_ntl_width_classifies_single_step_and_time_series(self):
        from pinkviewer.model import classify_ntl

        scalar = classify_ntl(FIXTURES / "shuffled.ntl")
        series = classify_ntl(FIXTURES / "shuffled_timeseries.ntl")
        self.assertEqual((scalar.kind, scalar.components, scalar.steps), ("single_step", 1, 1))
        self.assertEqual((series.kind, series.components, series.steps), ("time_series", 1, 2))

    def test_automatic_ntl_loader_chooses_scalar_or_time_series(self):
        from pinkviewer.model import load_ntl_auto

        id_map = {40: 0, 10: 1, 90: 2}
        scalar = load_ntl_auto(FIXTURES / "shuffled.ntl", id_map)
        series = load_ntl_auto(FIXTURES / "shuffled_timeseries.ntl", id_map)
        self.assertEqual(scalar.kind, "single_step")
        self.assertEqual(scalar.field.values, (4.0, 1.0, 3.0))
        self.assertEqual(series.kind, "time_series")
        self.assertEqual(series.series.values.tolist(), [[4.0, 1.0, 3.0], [40.0, 10.0, 30.0]])

    def test_timeseries_ntl_rejects_truncated_and_extra_tokens(self):
        from pinkviewer.model import load_ntl_auto

        id_map = {40: 0, 10: 1, 90: 2}
        with self.assertRaisesRegex(ValueError, "unknown node ID|fewer than 2 time values"):
            load_ntl_auto(FIXTURES / "truncated_timeseries.ntl", id_map)
        with self.assertRaisesRegex(ValueError, "unexpected extra NTL token"):
            load_ntl_auto(FIXTURES / "extra_timeseries.ntl", id_map)


if __name__ == "__main__":
    unittest.main()
