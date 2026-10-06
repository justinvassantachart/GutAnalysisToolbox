import gzip
import json
from pathlib import Path
import struct
import tempfile
import unittest

import check


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.pixels = [1.0, 2.0, 3.0, 4.0]

    def tearDown(self):
        self.temporary.cleanup()

    def fixture(self, name, labels=(1, 0, 0, 0), probabilities=(0.8, 0.1, 0.1, 0.1), center=(0.5, 0.5), vertex_delta=0):
        prefix = self.root/name
        Path(str(prefix)+'.labels.u16be').write_bytes(struct.pack('>4H', *labels))
        Path(str(prefix)+'.probability.f32be').write_bytes(struct.pack('>4f', *probabilities))
        summary = {'shape': [2, 2, 97], 'probability_threshold': 0.5, 'nms_threshold': 0.3,
                   'boundary': 2, 'candidates': 1, 'count': 1, 'winner_centers': [list(center)]}
        Path(str(prefix)+'.nms.json').write_text(json.dumps(summary))
        summary.update(check.measurements(labels, self.pixels, 2, 2))
        Path(str(prefix)+'.summary.json').write_text(json.dumps(summary))
        raw = struct.pack('>5i', 0x47415450, 1, 2, 2, 1)+struct.pack('>ffi', *center, 96)
        raw += struct.pack('>192f', *([vertex_delta, 0.0]+[0.0]*190))
        Path(str(prefix)+'.polygons.gz').write_bytes(gzip.compress(raw, mtime=0))
        return prefix

    def compare(self, first, second):
        return check.compare(first, second, self.pixels, 2, 2, affected_label=1)

    def test_identical_reference_is_exact(self):
        result = self.compare(self.fixture('reference'), self.fixture('actual'))
        self.assertTrue(result['exact_raster_centers_measurements_match'])
        self.assertTrue(result['outline_comparison']['strict_quantized_outlines_equal'])
        self.assertEqual(result['probability_values_outside_tolerance'], 0)
        self.assertEqual(result['affected_cell']['iou'], 1)

    def test_boundary_change_is_not_hidden_by_same_count(self):
        result = self.compare(self.fixture('reference'), self.fixture('actual', labels=(1, 1, 0, 0)))
        self.assertTrue(result['counts_equal'])
        self.assertEqual(result['foreground_pixels_differing'], 1)
        self.assertFalse(result['measurements_equal'])
        self.assertEqual(result['affected_cell']['iou'], 0.5)
        self.assertFalse(result['exact_raster_centers_measurements_match'])

    def test_numeric_tolerance_is_reported_separately_from_masks(self):
        result = self.compare(self.fixture('reference'), self.fixture('actual', probabilities=(0.81, 0.1, 0.1, 0.1)))
        self.assertTrue(result['exact_raster_centers_measurements_match'])
        self.assertEqual(result['probability_values_outside_tolerance'], 1)
        self.assertFalse(result['probability_maps_exact'])

    def test_nonfinite_probability_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'Invalid probability'):
            self.compare(self.fixture('reference'), self.fixture('actual', probabilities=(float('nan'), 0.1, 0.1, 0.1)))

    def test_subpixel_outline_change_is_not_hidden_by_exact_masks(self):
        result = self.compare(self.fixture('reference'), self.fixture('actual', vertex_delta=0.01))
        self.assertTrue(result['exact_raster_centers_measurements_match'])
        self.assertFalse(result['outline_comparison']['strict_quantized_outlines_equal'])
        self.assertEqual(result['outline_comparison']['changed_vertices_at_matched_centers'], 1)

    def test_changed_center_excluded_from_matched_outline_bound(self):
        result = self.compare(self.fixture('reference'), self.fixture('actual', center=(1.5, 0.5)))
        outline = result['outline_comparison']
        self.assertEqual(outline['matched_centers'], 0)
        self.assertEqual(outline['max_abs_coordinate_delta_px'], 0)
        self.assertEqual(len(outline['unmatched_actual_centers']), 1)
        self.assertFalse(result['winner_centers_and_label_order_equal'])

    def test_corrupt_reference_measurements_are_rejected(self):
        reference, actual = self.fixture('reference'), self.fixture('actual')
        path = Path(str(reference)+'.summary.json')
        row = json.loads(path.read_text()); row['measurements'][0]['area_pixels'] = 7
        path.write_text(json.dumps(row))
        with self.assertRaisesRegex(AssertionError, 'Reference measurement summary'):
            self.compare(reference, actual)

    def test_raster_measurement_units_and_perimeter(self):
        row = check.measurements([1, 0, 0, 0], self.pixels, 2, 2)['measurements'][0]
        self.assertEqual(row['area_pixels'], 1)
        self.assertEqual(row['perimeter_4_neighbor_pixels'], 4)
        self.assertEqual(row['bbox'], [0, 0, 0, 0])
        self.assertEqual(row['centroid_x_pixels'], 0.5)
        self.assertEqual(row['mean_intensity'], 1)

    def test_fixture_corruption_is_rejected_before_extraction(self):
        fixture_root = self.root/'packet'
        (fixture_root/'fixtures').mkdir(parents=True)
        (fixture_root/'fixtures'/'input.gati.gz').write_bytes(b'corrupt')
        original_root = check.ROOT
        try:
            check.ROOT = fixture_root
            with self.assertRaisesRegex(AssertionError, 'SHA-256 mismatch'):
                check.extract_fixtures(self.root/'unpacked', {'files': {'input.gati.gz': {'sha256': '0'*64}}})
        finally:
            check.ROOT = original_root

    def test_extractor_preserves_already_compressed_polygons(self):
        fixture_root = self.root/'packet'
        (fixture_root/'fixtures').mkdir(parents=True)
        payload = gzip.compress(b'polygon-payload', mtime=0)
        path = fixture_root/'fixtures'/'legacy.polygons.gz'
        path.write_bytes(payload)
        record = {'sha256': check.hu.digest(path), 'encoding': 'identity', 'extracted_bytes': len(payload),
                  'extracted_sha256': check.hu.digest(path), 'extracted_name': 'legacy.polygons.gz'}
        original_root = check.ROOT
        try:
            check.ROOT = fixture_root
            check.extract_fixtures(self.root/'unpacked', {'files': {path.name: record}})
            self.assertEqual((self.root/'unpacked'/path.name).read_bytes(), payload)
        finally:
            check.ROOT = original_root

    def test_input_shape_is_fixed(self):
        path = self.root/'input.gati'
        path.write_bytes(struct.pack('>4i4f', 0x47415449, 1, 2, 2, *self.pixels))
        self.assertEqual(check.input_pixels(path, 2, 2), tuple(self.pixels))
        with self.assertRaisesRegex(AssertionError, 'shape or size'):
            check.input_pixels(path, 1, 4)


if __name__ == '__main__':
    unittest.main()
