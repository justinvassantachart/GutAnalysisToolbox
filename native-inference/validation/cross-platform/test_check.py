"""Guard against a comparator which only reports failures but lets CI pass."""
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest

import check


class StrictComparisonTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.reference = check.ROOT / "fixtures" / "neuron-hu-1"
        self.actual = Path(self.directory.name) / "actual"
        self.source = check.input_pixels(check.ROOT / "fixtures" / "hu-input.gati")
        for suffix in (".probability.f32be", ".labels.u16be"):
            shutil.copyfile(str(self.reference) + suffix, str(self.actual) + suffix)
        summary = json.loads(Path(str(self.reference) + ".summary.json").read_text())
        nms_keys = ("shape", "probability_threshold", "nms_threshold", "boundary", "candidates", "count", "winner_centers")
        self.nms = {key: summary[key] for key in nms_keys}
        self.write_nms()

    def write_nms(self):
        Path(str(self.actual) + ".nms.json").write_text(json.dumps(self.nms))

    def report(self):
        return check.compare(self.reference, self.actual, self.source)

    def alter_probability(self, value):
        path = Path(str(self.actual) + ".probability.f32be")
        data = bytearray(path.read_bytes())
        struct.pack_into(">f", data, 0, value)
        path.write_bytes(data)

    def test_identical_reference_passes(self):
        self.assertTrue(self.report()["passed"])

    def test_small_probability_roundoff_is_allowed(self):
        path = Path(str(self.actual) + ".probability.f32be")
        original = struct.unpack(">f", path.read_bytes()[:4])[0]
        self.alter_probability(original + 1e-5)
        self.assertTrue(self.report()["passed"])

    def test_probability_outside_fixed_tolerance_fails(self):
        self.alter_probability(0.9)
        self.assertFalse(self.report()["passed"])
        self.assertEqual(1, self.report()["probability_failures"])

    def test_nan_probability_fails(self):
        self.alter_probability(float("nan"))
        report = self.report()
        self.assertFalse(report["passed"])
        self.assertIsNone(report["probability_max_abs_error"])
        self.assertIsNone(report["probability_mean_abs_error"])
        self.assertEqual(report, json.loads(json.dumps(report, allow_nan=False)))

    def test_label_permutation_fails_even_when_shapes_match(self):
        path = Path(str(self.actual) + ".labels.u16be")
        labels = check.read_values(path, "H", len(self.source))
        labels = tuple(2 if x == 1 else 1 if x == 2 else x for x in labels)
        path.write_bytes(struct.pack(f">{len(labels)}H", *labels))
        report = self.report()
        self.assertFalse(report["passed"])
        self.assertGreater(report["raw_label_pixel_differences"], 0)
        self.assertEqual(report["expected_canonical_shape_sha256"], report["actual_canonical_shape_sha256"])

    def test_count_mismatch_fails(self):
        self.nms["count"] += 1
        self.write_nms()
        self.assertIn("count differs", self.report()["failures"])

    def test_measurement_mismatch_fails(self):
        # Unchanged segmentation but different intensities must not pass.
        self.source = tuple(x + 1 for x in self.source)
        self.assertIn("measurements differs", self.report()["failures"])

    def test_truncated_plane_fails(self):
        Path(str(self.actual) + ".probability.f32be").write_bytes(b"\0")
        with self.assertRaises(AssertionError):
            self.report()

    def test_fixture_hash_mismatch_fails(self):
        with self.assertRaises(AssertionError):
            check.verify(Path(str(self.actual) + ".probability.f32be"), "0" * 64)


if __name__ == "__main__":
    unittest.main()
