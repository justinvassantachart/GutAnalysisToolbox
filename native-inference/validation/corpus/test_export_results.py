import copy
from pathlib import Path
import unittest

from export_results import classify, portable, summarize


def sample():
    return {
        "status": "compared", "exact_segmentation_match": True,
        "metrics": {
            "width": 10, "height": 10, "modern_count": 2, "legacy_count": 2,
            "different_label_pixels": 0, "different_canonical_label_pixels": 0,
            "different_foreground_pixels": 0, "pixel_measurements_equal": True,
            "winner_centers_equal": True, "probability_threshold_flips": 0,
            "values_outside_atol_1e_minus_4_rtol_1e_minus_4": 0,
            "max_abs_probability": 1e-6, "max_abs_distance": 1e-5,
        },
    }


class ExportTests(unittest.TestCase):
    def test_id_permutation_is_distinct_from_geometry_change(self):
        row = sample()
        row["metrics"]["different_label_pixels"] = 10
        row["exact_segmentation_match"] = False
        self.assertEqual("label_id_order_only", classify(row))
        row["metrics"]["different_canonical_label_pixels"] = 1
        row["metrics"]["different_foreground_pixels"] = 1
        row["metrics"]["pixel_measurements_equal"] = False
        self.assertEqual("geometry_count_or_measurement_change", classify(row))

    def test_partial_result_cannot_be_marked_complete(self):
        summary = summarize([sample()], 180)
        self.assertFalse(summary["all_expected_cases_terminal"])
        self.assertEqual(1, summary["exact_label_raster_and_measurement_cases"])
        self.assertEqual(100, summary["input_pixels"])

    def test_geometry_equivalence_and_numeric_flags_are_independent(self):
        exact = sample()
        id_only = copy.deepcopy(exact)
        id_only["exact_segmentation_match"] = False
        id_only["metrics"]["different_label_pixels"] = 12
        id_only["metrics"]["probability_threshold_flips"] = 1
        summary = summarize([exact, id_only], 2)
        self.assertEqual(2, summary["equivalent_geometry_count_measurement_cases"])
        self.assertEqual(1, summary["label_id_order_only_cases"])
        self.assertEqual(1, summary["numeric_flag_cases"])
        self.assertTrue(summary["all_expected_cases_terminal"])

    def test_portable_paths_preserve_public_source_urls(self):
        result = portable({"input_path": "/workspace/shared/corpus/inputs/example.bin",
                           "source": "https://zenodo.org/records/15314214",
                           "traceback": "private debugging path",
                           "tool_path": "/tmp/reviewer/Tool.java"}, Path("/workspace/shared/corpus"))
        self.assertEqual("inputs/example.bin", result["input_path"])
        self.assertEqual("https://zenodo.org/records/15314214", result["source"])
        self.assertEqual("Tool.java", result["tool_path"])
        self.assertNotIn("traceback", result)


class ManifestReconciliationTests(unittest.TestCase):
    def fixtures(self):
        from export_results import reconcile_manifest
        manifest = [{"case_id": name, "input_sha256": name * 64, "model": "neuron", "split": "test",
                     "width": "10", "height": "10", "tiles": "4"} for name in ("a", "b")]
        rows = []
        for item in manifest:
            row = sample()
            row["case_id"] = item["case_id"]
            row["metadata"] = copy.deepcopy(item)
            rows.append(row)
        return reconcile_manifest, manifest, rows

    def test_partial_reports_list_missing_ids(self):
        reconcile, manifest, rows = self.fixtures()
        result = reconcile(manifest, rows[:1], 2)
        self.assertEqual(["b"], result["missing_case_ids"])
        self.assertTrue(result["metadata_consistent"])

    def test_equal_counts_do_not_hide_duplicate_or_unknown_cases(self):
        reconcile, manifest, rows = self.fixtures()
        with self.assertRaisesRegex(ValueError, "Duplicate result"):
            reconcile(manifest, [rows[0], copy.deepcopy(rows[0])], 2)
        rows[1]["case_id"] = "unknown"
        with self.assertRaisesRegex(ValueError, "Unknown result"):
            reconcile(manifest, rows, 2)

    def test_hash_model_split_and_shape_mismatches_are_rejected(self):
        for field, value in (("input_sha256", "wrong"), ("model", "subtype"), ("split", "train"), ("width", "20")):
            reconcile, manifest, rows = self.fixtures()
            rows[1]["metadata"][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "inconsistent"):
                reconcile(manifest, rows, 2)
        reconcile, manifest, rows = self.fixtures()
        rows[0]["metrics"]["height"] = 20
        with self.assertRaisesRegex(ValueError, "tensor height"):
            reconcile(manifest, rows, 2)

    def test_manifest_duplicates_and_incorrect_expected_count_are_rejected(self):
        reconcile, manifest, rows = self.fixtures()
        with self.assertRaisesRegex(ValueError, "duplicate manifest"):
            reconcile([manifest[0], manifest[0]], rows, 2)
        with self.assertRaisesRegex(ValueError, "does not match manifest size"):
            reconcile(manifest, rows, 1)


if __name__ == "__main__":
    unittest.main()
