"""Synthetic verifier tests only: generated TIFFs are NOT inference evidence."""

import copy
import gzip
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import numpy as np
from PIL import Image
import tifffile


SPEC = importlib.util.spec_from_file_location("ganglia_parity", Path(__file__).with_name("compare_ganglia_parity.py"))
parity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(parity)


def synthetic_fixture(directory):
    """Persist deliberately tiny, explicitly synthetic verifier input files."""
    directory.mkdir(parents=True, exist_ok=True)
    reports = {}
    for variant in parity.VARIANTS:
        rows = []
        for sample_id in parity.SAMPLES:
            prefix = f"{variant}-{sample_id}"
            hu = (np.arange(64).reshape(8, 8) * 4).astype("u1")
            hu[0, 1], hu[0, 2] = 3, 127  # Expose FloatProcessor single-precision rounding.
            ganglia = 255 - hu
            rgb = np.stack((hu, ganglia, hu), axis=-1)
            pixels = np.moveaxis(rgb, -1, 0).astype(np.float32)
            prepared = (pixels if variant == "control" else pixels * np.float32(1.0 / 255.0)).astype(">f4")
            labels = np.zeros((8, 8), dtype="u2")
            labels[1:3, 1:3] = 1
            labels[5:7, 5:7] = 2
            if variant == "control":
                labels[2, 3] = 1
            mask = ((labels > 0) * 255).astype("u1")
            channels, ganglia_channel, cell_channel = parity.SAMPLE_CHANNELS[sample_id]
            params = {"rdf_threshold": .6, "gat_threshold": .6, "open_iterations": 1,
                      "minimum_area_um2": 1.0, "minimum_area_px": 4}
            row = {
                "id": sample_id, "width": 8, "height": 8,
                "source_channels": channels, "source_bit_depth": 8,
                "ganglia_channel": ganglia_channel, "cell_channel": cell_channel,
                "source_sha256": parity.sha256(b"synthetic source " + sample_id.encode()),
                "source_unchanged": True, "calibration_preserved": True,
                "pixel_width_um": .5, "pixel_height_um": .75,
                "calibration": {"pixel_width_um": .5, "pixel_height_um": .75},
                "input_contract": {"channels": 3, "axes": "cyx", "mapping": "R=cell,G=ganglia,B=cell", "encoding": "float32-big-endian"},
                "input_axes": "cyx", "params": params, **params,
                "input_float_file": prefix + "-input.f32be.gz",
                "input_float_sha256": parity.sha256(prepared.tobytes()),
                "input_min": float(prepared.min()), "input_max": float(prepared.max()),
                "mask_file": prefix + "-mask.tif", "labels_file": prefix + "-labels.tif",
                "mask_pixels_uint8_row_major_sha256": parity.sha256(mask.tobytes()),
                "labels_pixels_uint16_be_sha256": parity.sha256(labels.astype(">u2").tobytes()),
                "foreground_pixels": int(np.count_nonzero(mask)), "ganglion_count": 2,
                "areas_um2": [0.0, float(np.count_nonzero(labels == 1)) * .25, 1.0],
                "rgb_file": prefix + "-rgb.png",
                "test_fixture_kind": "synthetic verifier-only raster; not model inference",
            }
            if sample_id == "distal_hu_gfap":
                assignments = [{"neuron_id": n, "ganglion_id": n % 3} for n in range(1, 84)]
                row.update({"assignment_neuron_source": "SYNTHETIC verifier-only assignment fixture; not historical image evidence",
                            "assignment_neuron_roi_sha256": parity.sha256(b"synthetic roi set"),
                            "assignments": assignments,
                            "neurons_per_ganglion": [0, 28, 28]})
            (directory / row["input_float_file"]).write_bytes(gzip.compress(prepared.tobytes()))
            tifffile.imwrite(directory / row["mask_file"], mask)
            # Different TIFF endian/container metadata must not change the raw
            # uint16-big-endian canonical pixel digest or equality decision.
            tifffile.imwrite(directory / row["labels_file"], labels, byteorder=">" if variant == "fork" else "<")
            Image.fromarray(rgb).save(directory / row["rgb_file"])
            rows.append(row)
        reports[variant] = {"status": "PASS", "mode": "parity", "metrics": {"samples": rows}}
    return reports


class SyntheticGangliaParityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        # Tiny fixture geometry and fake ROI bytes are allowed only inside these
        # explicitly synthetic verifier tests, never through the production CLI.
        geometry = patch.object(parity, "SAMPLE_GEOMETRY", {sample: (8, 8, 8) for sample in parity.SAMPLES})
        roi_digest = patch.object(parity, "HISTORICAL_ROI_SHA256", parity.sha256(b"synthetic roi set"))
        geometry.start()
        roi_digest.start()
        self.addCleanup(geometry.stop)
        self.addCleanup(roi_digest.stop)
        self.reports = synthetic_fixture(self.root)
        self.save_reports()

    def tearDown(self):
        self.temp.cleanup()

    def save_reports(self):
        for variant, report in self.reports.items():
            (self.root / f"{variant}_parity.json").write_text(json.dumps(report))

    def row(self, variant="fork", sample="model_public"):
        return next(row for row in self.reports[variant]["metrics"]["samples"] if row["id"] == sample)

    def compare(self, plots=False):
        self.save_reports()
        return parity.compare_directory(self.root, make_plots=plots)

    def assert_failed(self, result, reason):
        self.assertEqual("FAIL", result["status"])
        self.assertIn(reason, "\n".join(result["errors"]))

    def update_labels_and_mask(self, row, labels):
        mask = ((labels > 0) * 255).astype("u1")
        tifffile.imwrite(self.root / row["mask_file"], mask)
        tifffile.imwrite(self.root / row["labels_file"], labels.astype("u2"))
        row["mask_pixels_uint8_row_major_sha256"] = parity.sha256(mask.tobytes())
        row["labels_pixels_uint16_be_sha256"] = parity.sha256(labels.astype(">u2").tobytes())
        row["foreground_pixels"] = int(np.count_nonzero(mask))
        row["ganglion_count"] = len(np.unique(labels[labels > 0]))
        row["areas_um2"] = [0.0] + [float(np.count_nonzero(labels == n)) * .25 for n in range(1, int(labels.max()) + 1)]

    def test_synthetic_exact_parity_passes_and_control_divergence_is_recorded(self):
        result = self.compare()
        self.assertEqual("PASS", result["status"], result["errors"])
        self.assertEqual(list(parity.SAMPLES), result["positive_control"]["samples_with_input_and_mask_divergence"])
        for row in result["samples"]:
            self.assertEqual(0, row["original_vs_fork"]["mask_changed_pixels"])
            self.assertTrue(row["original_vs_fork"]["input_bytes_equal"])
            self.assertEqual(1, row["original_vs_control"]["mask_changed_pixels"])

    def test_synthetic_cli_writes_json_and_three_readable_pngs(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(0, parity.main(["--directory", str(self.root)]))
        result = json.loads((self.root / parity.SUMMARY_FILE).read_text())
        self.assertEqual("PASS", result["status"])
        self.assertEqual(3, len(result["plots"]))
        for filename in result["plots"]:
            with Image.open(self.root / filename) as image:
                self.assertEqual((1800, 1362), image.size)
                image.verify()

    def test_missing_report_fails_even_if_other_reports_pass(self):
        (self.root / "control_parity.json").unlink()
        self.assert_failed(parity.compare_directory(self.root), "Missing report: control_parity.json")

    def test_nonpassing_and_missing_statuses_fail(self):
        for status in ("FAIL", "BLOCKED", "RUNNING", "pass", None):
            with self.subTest(status=status):
                self.reports["original"]["status"] = status
                self.assert_failed(self.compare(), "status must be PASS")

    def test_wrong_probe_mode_fails(self):
        self.reports["fork"]["mode"] = "ganglia"
        self.assert_failed(self.compare(), "expected parity probe mode")

    def test_sample_set_missing_extra_or_duplicate_fails(self):
        rows = copy.deepcopy(self.reports["fork"]["metrics"]["samples"])
        for changed in (rows[:-1], rows + [rows[0]], [rows[0], rows[1], rows[0]]):
            with self.subTest(ids=[row["id"] for row in changed]):
                self.reports["fork"]["metrics"]["samples"] = changed
                self.assert_failed(self.compare(), "require exactly one of each expected sample")

    def test_unknown_sample_fails(self):
        self.row()["id"] = "unknown"
        self.assert_failed(self.compare(), "require exactly one of each expected sample")

    def test_nonfinite_json_and_duplicate_keys_fail(self):
        for bad_json, reason in (("{\"status\":NaN}", "Non-finite JSON"),
                                 ("{\"status\":\"PASS\",\"status\":\"FAIL\"}", "Duplicate JSON key")):
            with self.subTest(reason=reason):
                (self.root / "fork_parity.json").write_text(bad_json)
                self.assert_failed(parity.compare_directory(self.root), reason)

    def test_missing_schema_contract_field_fails(self):
        del self.row()["params"]
        self.assert_failed(self.compare(), "Missing sample contract field: params")

    def test_changed_source_and_calibration_flags_fail(self):
        for field in ("source_unchanged", "calibration_preserved"):
            with self.subTest(field=field):
                self.row()[field] = False
                self.assertEqual("FAIL", self.compare()["status"])
                self.row()[field] = True

    def test_source_digest_difference_fails(self):
        self.row()["source_sha256"] = "0" * 64
        self.assert_failed(self.compare(), "changed sample contract/parameter source_sha256")

    def test_changed_parameter_on_all_variants_still_fails(self):
        for variant in parity.VARIANTS:
            self.row(variant)["gat_threshold"] = .7
        self.assert_failed(self.compare(), "Changed fixed parameter: gat_threshold")

    def test_changed_channel_contract_fails(self):
        self.row()["ganglia_channel"] = 1
        self.assert_failed(self.compare(), "Sample channel contract differs")

    def test_actual_float_bytes_are_verified_not_just_json_hash_equality(self):
        row = self.row()
        path = self.root / row["input_float_file"]
        raw = bytearray(gzip.decompress(path.read_bytes()))
        raw[3] ^= 1
        path.write_bytes(gzip.compress(raw))
        self.assert_failed(self.compare(), "Prepared float pixels do not match reported SHA-256")

    def test_equal_but_unnormalized_original_and_fork_fail(self):
        control = self.row("control")
        for variant in ("original", "fork"):
            row = self.row(variant)
            for field in ("input_float_file", "input_float_sha256", "input_min", "input_max"):
                row[field] = control[field]
        self.assert_failed(self.compare(), "violate the original once-normalized RGB contract")

    def test_floatprocessor_rounding_is_float32_multiply_not_float64_then_cast(self):
        # Byte 3 is the concrete one-ULP regression: FloatProcessor rounds the
        # multiplier to float BEFORE multiplying, as the Java probe does.
        correct = np.float32(3) * np.float32(1.0 / 255.0)
        wrong = np.float32(3 * (1.0 / 255.0))
        self.assertNotEqual(correct.tobytes(), wrong.tobytes())
        for variant in ("original", "fork"):
            row = self.row(variant)
            rgb = np.array(Image.open(self.root / row["rgb_file"]))
            prepared = (np.moveaxis(rgb, -1, 0).astype(np.float64) * (1.0 / 255.0)).astype(">f4")
            raw = prepared.tobytes()
            (self.root / row["input_float_file"]).write_bytes(gzip.compress(raw))
            row["input_float_sha256"] = parity.sha256(raw)
            row["input_min"], row["input_max"] = float(prepared.min()), float(prepared.max())
        self.assert_failed(self.compare(), "violate the original once-normalized RGB contract")

    def test_input_wrong_length_and_nonfinite_values_fail(self):
        row = self.row()
        path = self.root / row["input_float_file"]
        raw = gzip.decompress(path.read_bytes())
        path.write_bytes(gzip.compress(raw + b"x"))
        self.assert_failed(self.compare(), "wrong decompressed byte length")
        array = np.frombuffer(raw, dtype=">f4").copy()
        array[0] = np.nan
        path.write_bytes(gzip.compress(array.tobytes()))
        row["input_float_sha256"] = parity.sha256(array.tobytes())
        self.assert_failed(self.compare(), "contains non-finite floats")

    def test_input_reported_minimum_must_match_saved_values(self):
        self.row()["input_min"] = .01
        self.assert_failed(self.compare(), "input_min: does not match saved prepared input")

    def test_masks_are_read_and_hashed_in_row_major_pixel_order(self):
        row = self.row()
        mask = tifffile.imread(self.root / row["mask_file"])
        mask[0, 0] = 255
        tifffile.imwrite(self.root / row["mask_file"], mask)
        self.assert_failed(self.compare(), "mask: saved pixels do not match reported SHA-256")

    def test_same_counts_and_areas_with_different_pixels_fail(self):
        row = self.row()
        labels = tifffile.imread(self.root / row["labels_file"])
        labels[1, 1], labels[1, 3] = 0, 1
        self.update_labels_and_mask(row, labels)
        result = self.compare()
        self.assert_failed(result, "mask_pixels_equal")
        self.assertTrue(result["samples"][0]["original_vs_fork"]["areas_equal"])
        self.assertTrue(result["samples"][0]["original_vs_fork"]["ganglion_count_equal"])

    def test_reordered_label_ids_fail_even_when_binary_mask_is_identical(self):
        row = self.row()
        labels = tifffile.imread(self.root / row["labels_file"])
        swapped = labels.copy()
        swapped[labels == 1], swapped[labels == 2] = 2, 1
        self.update_labels_and_mask(row, swapped)
        result = self.compare()
        self.assert_failed(result, "labels_equal")
        self.assertTrue(result["samples"][0]["original_vs_fork"]["mask_pixels_equal"])

    def test_incorrect_label_hash_endianness_fails(self):
        row = self.row()
        labels = tifffile.imread(self.root / row["labels_file"])
        row["labels_pixels_uint16_be_sha256"] = parity.sha256(labels.astype("<u2").tobytes())
        self.assert_failed(self.compare(), "labels: saved pixels do not match reported SHA-256")

    def test_wrong_raster_dtype_or_geometry_fails(self):
        row = self.row()
        path = self.root / row["mask_file"]
        original = tifffile.imread(path)
        for raster, reason in ((original.astype("u2"), "expected u1 unsigned raster"),
                               (original[:-1], "expected shape")):
            tifffile.imwrite(path, raster)
            self.assert_failed(self.compare(), reason)

    def test_mask_must_be_binary_and_match_labels(self):
        row = self.row()
        path = self.root / row["mask_file"]
        mask = tifffile.imread(path)
        for value, reason in ((127, "Mask contains nonbinary pixels"), (255, "Label support differs")):
            mask[0, 0] = value
            tifffile.imwrite(path, mask)
            row["mask_pixels_uint8_row_major_sha256"] = parity.sha256(mask.tobytes())
            row["foreground_pixels"] = int(np.count_nonzero(mask))
            self.assert_failed(self.compare(), reason)

    def test_area_uses_actual_gat_width_squared_for_non_square_calibration(self):
        self.assertEqual("PASS", self.compare()["status"])
        self.row()["areas_um2"] = [0, 1.5, 1.5]
        self.assert_failed(self.compare(), "Area values differ from labels")

    def test_background_area_and_foreground_counts_are_validated(self):
        row = self.row()
        row["areas_um2"][0] = 1
        self.assert_failed(self.compare(), "Area values differ")
        row["areas_um2"][0] = 0
        row["foreground_pixels"] += 1
        self.assert_failed(self.compare(), "Foreground count differs")

    def test_assignment_changes_fail_even_if_counts_stay_equal(self):
        row = self.row(sample="distal_hu_gfap")
        row["assignments"][0]["ganglion_id"], row["assignments"][1]["ganglion_id"] = 2, 1
        result = self.compare()
        self.assert_failed(result, "assignments_equal")
        self.assertEqual(2, result["samples"][1]["original_vs_fork"]["assignments_changed"])

    def test_assignment_order_does_not_change_semantic_equality(self):
        self.row(sample="distal_hu_gfap")["assignments"].reverse()
        self.assertEqual("PASS", self.compare()["status"])

    def test_assignment_counts_and_neuron_set_are_verified(self):
        row = self.row(sample="distal_hu_gfap")
        row["neurons_per_ganglion"][1] += 1
        self.assert_failed(self.compare(), "neurons_per_ganglion differs")
        row["neurons_per_ganglion"][1] -= 1
        row["assignments"][-1]["neuron_id"] = 1
        self.assert_failed(self.compare(), "Duplicate neuron assignment")

    def test_historical_neurons_cannot_be_applied_to_unmatched_samples(self):
        for sample in ("model_public", "proximal_hu_chat"):
            with self.subTest(sample=sample):
                self.row(sample=sample)["assignments"] = []
                self.assert_failed(self.compare(), "belong only to distal_hu_gfap")
                del self.row(sample=sample)["assignments"]

    def test_historical_assignment_provenance_must_match(self):
        self.row(sample="distal_hu_gfap")["assignment_neuron_roi_sha256"] = "0" * 64
        self.assert_failed(self.compare(), "ROI SHA-256 differs from the pinned 83-ROI set")

    def test_actual_fixture_geometry_is_pinned_outside_synthetic_tests(self):
        with patch.object(parity, "SAMPLE_GEOMETRY", {sample: (1024, 1024, 8) for sample in parity.SAMPLES}):
            self.assert_failed(self.compare(), "geometry/bit depth differs from the pinned public fixture")

    def test_duplicate_calibration_and_parameter_values_must_agree(self):
        self.row()["calibration"]["pixel_width_um"] = .6
        self.assert_failed(self.compare(), "Calibration contract does not match top-level")
        self.row()["calibration"]["pixel_width_um"] = .5
        self.row()["params"]["open_iterations"] = 2
        self.assert_failed(self.compare(), "Parameter contract does not match top-level")

    def test_real_divergence_still_produces_failure_visuals(self):
        row = self.row()
        labels = tifffile.imread(self.root / row["labels_file"])
        labels[1, 1], labels[1, 3] = 0, 1
        self.update_labels_and_mask(row, labels)
        result = self.compare(plots=True)
        self.assert_failed(result, "mask_pixels_equal")
        self.assertEqual(3, len(result["plots"]))
        self.assertTrue((self.root / "parity-model_public.png").is_file())

    def test_control_need_not_diverge_on_every_image(self):
        for sample_id in parity.SAMPLES[1:]:
            row = self.row("control", sample_id)
            self.reports["control"]["metrics"]["samples"].remove(row)
            self.reports["control"]["metrics"]["samples"].append(copy.deepcopy(self.row("original", sample_id)))
        result = self.compare()
        self.assertEqual("PASS", result["status"], result["errors"])
        self.assertEqual(["model_public"], result["positive_control"]["samples_with_input_and_mask_divergence"])

    def test_no_diverging_control_fails(self):
        self.reports["control"] = copy.deepcopy(self.reports["original"])
        self.assert_failed(self.compare(), "Positive control requires")

    def test_input_divergence_without_mask_divergence_is_not_positive_control(self):
        for sample_id in parity.SAMPLES:
            control, original = self.row("control", sample_id), self.row("original", sample_id)
            for field in ("mask_file", "mask_pixels_uint8_row_major_sha256", "labels_file", "labels_pixels_uint16_be_sha256", "areas_um2", "foreground_pixels"):
                control[field] = original[field]
        self.assert_failed(self.compare(), "Positive control requires")

    def test_missing_and_escaping_evidence_files_fail(self):
        row = self.row()
        for filename, reason in (("missing.tif", "missing evidence file"), ("../elsewhere.tif", "must stay in its results directory"),
                                 ("/tmp/elsewhere.tif", "must stay in its results directory")):
            with self.subTest(filename=filename):
                row["mask_file"] = filename
                self.assert_failed(self.compare(), reason)

    def test_symlink_escape_fails(self):
        (self.root / "escape.tif").symlink_to(self.root.parent / "outside.tif")
        self.row()["mask_file"] = "escape.tif"
        self.assert_failed(self.compare(), "evidence path escapes")

    def test_optional_file_hash_is_checked_separately_from_pixel_hash(self):
        self.row()["mask_tiff_sha256"] = "0" * 64
        self.assert_failed(self.compare(), "TIFF file SHA-256 mismatch")

    def test_missing_evidence_cli_fails_and_clears_stale_plots(self):
        for sample in parity.SAMPLES:
            (self.root / f"parity-{sample}.png").write_bytes(b"stale")
        (self.root / "fork_parity.json").unlink()
        with redirect_stdout(io.StringIO()):
            self.assertEqual(2, parity.main(["--directory", str(self.root)]))
        result = json.loads((self.root / parity.SUMMARY_FILE).read_text())
        self.assertEqual("FAIL", result["status"])
        self.assertEqual([], list(self.root.glob("parity-*.png")))

    def test_boundaries_do_not_wrap_image_edges(self):
        mask = np.full((5, 5), 255, dtype="u1")
        outline = parity.boundary(mask)
        self.assertEqual(16, int(np.count_nonzero(outline)))
        self.assertFalse(outline[2, 2])
        self.assertTrue(outline[0, 0])


if __name__ == "__main__":
    unittest.main()
