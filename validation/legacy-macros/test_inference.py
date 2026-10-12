"""Small deterministic tests of inference-launch isolation and evidence checks.

No model, JVM, image viewer or inference process is executed by these tests.
"""
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

import compare_inference
import run_inference_probe as runner


class LauncherTests(unittest.TestCase):
    def test_reduced_smoke_covers_all_requested_levels(self):
        rows = runner.selected_cases('smoke')
        self.assertEqual(7, len(rows))
        self.assertEqual({1, 2, 4, 5, 8}, {r['tiles'] for r in rows})
        self.assertEqual({8, 16, 32}, {r['dtype'] for r in rows})
        self.assertEqual({.5, 1, 1.5}, {r['scale'] for r in rows})
        self.assertEqual({'neuron', 'subtype'}, {r['model'] for r in rows})
        self.assertEqual({(95, 81), (96, 82)}, {tuple(r['shape']) for r in rows})

    def test_unknown_case_rejected(self):
        with self.assertRaises(ValueError):
            runner.selected_cases('smoke', ['unknown'])

    def test_original_candidate_actual_macro_line_has_one_target_change(self):
        original, old = runner.pinned_macro_line('original')
        native, new = runner.pinned_macro_line('native')
        self.assertEqual(old, new)
        self.assertEqual(original.replace('de.csbdresden.stardist.StarDist2D]', 'Features.Macros.LegacyMacroStarDist]'), native)
        for parameter in ('modelChoice', 'normalizeInput', 'percentileBottom', 'percentileTop', 'probThresh',
                          'nmsThresh', 'nTiles', 'excludeBoundary', 'roiPosition', 'showProbAndDist'):
            self.assertIn(parameter, original)

    def test_original_rejects_fork_jar_even_under_innocent_filename(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'innocent.jar'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('Features/Macros/LegacyMacroStarDist.class', b'unit-test')
            with self.assertRaises(ValueError):
                runner.validate_classpath([path], 'original')
            runner.validate_classpath([path], 'native')

    def test_native_parent_rejects_modern_tensorflow(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'dependency.jar'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('org/tensorflow/types/TFloat32.class', b'unit-test')
            with self.assertRaises(ValueError):
                runner.validate_classpath([path], 'native')

    def test_original_rejects_fork_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp); bad = path / 'Features/Inference/NativeStarDist.class'
            bad.parent.mkdir(parents=True); bad.write_bytes(b'unit-test')
            with self.assertRaises(ValueError):
                runner.validate_classpath([path], 'original')

    def test_protobuf4_rejected_before_any_inference(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'protobuf-java-4.32.0.jar'
            path.write_bytes(b'unit-test')
            with self.assertRaisesRegex(ValueError, 'protobuf'):
                runner.validate_legacy_dependencies([path])

    def test_wrong_bytes_under_old_protobuf_name_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'protobuf-java-3.11.4.jar'
            path.write_bytes(b'unit-test')
            with self.assertRaisesRegex(ValueError, 'protobuf'):
                runner.validate_legacy_dependencies([path])


def fabricate_unit_evidence(root, variant):
    """Fake data only for checking the checker, never scientific evidence."""
    root.mkdir()
    config = runner.selected_cases('smoke', ['neuron-01'])[0]
    _, source = runner.pinned_macro_line(variant)
    fixture = json.loads((runner.ROOT / 'native-inference/validation/cross-platform/fixture-manifest.json').read_text())
    data = struct.pack('>ffff', 0, 1, 1, 0)
    digest = hashlib.sha256(data).hexdigest()
    target = 'Features.Macros.LegacyMacroStarDist' if variant == 'native' else 'de.csbdresden.stardist.StarDist2D'
    report = {'schema_version': 1, 'status': 'PASS_MACRO_INFERENCE_CASE', 'variant': variant,
              'scope': 'registered-legacy-macro-inference-boundary', 'whole_analysis_macro_executed': False,
              'case': config, 'fixture_sha256': fixture['source']['sha256'], 'model_sha256': fixture['cases'][0]['model_sha256'],
              'matching_module_executions': 1, 'dispatched_commands': ['Command From Macro'],
              'input_unchanged': True, 'unrelated_image_unchanged': True, 'label_display_verified': True,
              'auxiliary_outputs_absent': True, 'target_class': {'name': target},
              'command_bridge_class': {'name': 'de.csbdresden.CommandFromMacro'},
              'worker_processes': {'123': 'unit-test-only'} if variant == 'native' else {},
              'backend_property': 'gat.stardist.backend', 'backend_value': 'native',
              'label_pixels_f32be_sha256': digest,
              'label': {'pixels_f32be_sha256': digest, 'shape': [2, 2], 'areas_by_label_id': {'1': 2}, 'object_count': 1},
              'roi_manager': [['roi-unit-test', 2, 0, 0, 0, 0, [[0, 0], [2, 0], [2, 2]]]],
              'prepared_input': {'description': 'fabricated unit fixture only'}, 'new_image_windows': [], 'errors': []}
    case = root / 'neuron-01/evidence'; case.mkdir(parents=True)
    (case / 'labels.f32be').write_bytes(data); (case / 'report.json').write_text(json.dumps(report))
    summary = {'status': 'PASS_SELECTED_CASES', 'variant': variant, 'scope': report['scope'],
               'whole_analysis_macro_executed': False, 'selected_cases': ['neuron-01'], 'macro_source': source,
               'cases': [{'id': 'neuron-01', 'status': 'PASS_MACRO_INFERENCE_CASE',
                          'execution': {'exit_code': 0, 'resource_stop_reason': None}, 'report': 'neuron-01/evidence/report.json'}]}
    (root / 'summary.json').write_text(json.dumps(summary))
    return case / 'report.json'


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.original, self.native = root / 'original', root / 'native'
        self.original_report = fabricate_unit_evidence(self.original, 'original')
        self.native_report = fabricate_unit_evidence(self.native, 'native')

    def tearDown(self):
        self.temp.cleanup()

    def change_native(self, update):
        record = json.loads(self.native_report.read_text()); update(record)
        self.native_report.write_text(json.dumps(record))

    def test_well_formed_unit_reports_compare(self):
        result = compare_inference.compare(self.original, self.native)
        self.assertEqual('PASS_PAIRED_MACRO_INFERENCE_SCOPE', result['status'])
        self.assertEqual(0, result['cases'][0]['label_differences']['different_label_pixels'])

    def test_fallback_without_observed_worker_rejected(self):
        self.change_native(lambda r: r.update(worker_processes={}))
        self.assertEqual('FAIL_OR_INCOMPLETE', compare_inference.compare(self.original, self.native)['status'])

    def test_wrong_backend_property_rejected(self):
        self.change_native(lambda r: r.update(backend_property='gat.inference.backend'))
        self.assertEqual('FAIL_OR_INCOMPLETE', compare_inference.compare(self.original, self.native)['status'])

    def test_tampered_label_file_rejected(self):
        (self.native_report.parent / 'labels.f32be').write_bytes(struct.pack('>ffff', 0, 1, 0, 0))
        self.assertEqual('FAIL_OR_INCOMPLETE', compare_inference.compare(self.original, self.native)['status'])

    def test_roi_difference_explicit_and_quantified(self):
        def mutate(row):
            row['roi_manager'][0][-1][0][0] += .00001
        self.change_native(mutate)
        exact = compare_inference.compare(self.original, self.native)
        self.assertEqual('FAIL_OR_INCOMPLETE', exact['status'])
        self.assertEqual(.00001, exact['cases'][0]['roi_max_vertex_absolute_difference_pixels'])
        tolerant = compare_inference.compare(self.original, self.native, .0001)
        self.assertEqual('PASS_PAIRED_MACRO_INFERENCE_SCOPE', tolerant['status'])
        self.assertEqual('PASS_EXPLICIT_ROI_TOLERANCE', tolerant['cases'][0]['status'])

    def test_roi_tolerance_cannot_hide_positions(self):
        def mutate(row):
            row['roi_manager'][0][5] = 1
        self.change_native(mutate)
        self.assertEqual('FAIL_OR_INCOMPLETE', compare_inference.compare(self.original, self.native, 1)['status'])

    def test_one_quantization_step_handles_decimal_subtraction_only(self):
        original = json.loads(self.original_report.read_text())
        original['roi_manager'][0][-1][0][0] = 64.69
        self.original_report.write_text(json.dumps(original))
        self.change_native(lambda row: row['roi_manager'][0][-1][0].__setitem__(0, 64.70))
        self.assertGreater(64.70 - 64.69, .01)
        self.assertEqual('FAIL_OR_INCOMPLETE', compare_inference.compare(self.original, self.native)['status'])
        result = compare_inference.compare(self.original, self.native, .01)
        self.assertEqual('PASS_PAIRED_MACRO_INFERENCE_SCOPE', result['status'])
        self.assertEqual(1e-12, result['roi_tolerance_comparison_slack_pixels'])

    def test_exact_mode_does_not_receive_numerical_slack(self):
        self.change_native(lambda row: row['roi_manager'][0][-1][0].__setitem__(0, 1e-14))
        result = compare_inference.compare(self.original, self.native)
        self.assertEqual('FAIL_OR_INCOMPLETE', result['status'])
        self.assertEqual(0, result['roi_tolerance_comparison_slack_pixels'])

    def test_larger_than_one_quantization_step_rejected(self):
        self.change_native(lambda row: row['roi_manager'][0][-1][0].__setitem__(0, .01000001))
        self.assertEqual('FAIL_OR_INCOMPLETE', compare_inference.compare(self.original, self.native, .01)['status'])
        self.change_native(lambda row: row['roi_manager'][0][-1][0].__setitem__(0, .02))
        self.assertEqual('FAIL_OR_INCOMPLETE', compare_inference.compare(self.original, self.native, .01)['status'])

    def test_vertex_allowance_cannot_hide_label_count_area_or_name_change(self):
        for field, value in [('object_count', 2), ('areas_by_label_id', {'1': 3})]:
            old = self.native_report.read_text()
            self.change_native(lambda row: row['label'].__setitem__(field, value))
            self.assertEqual('FAIL_OR_INCOMPLETE', compare_inference.compare(self.original, self.native, .01)['status'])
            self.native_report.write_text(old)
        self.change_native(lambda row: row['roi_manager'][0].__setitem__(0, 'different-name'))
        self.assertEqual('FAIL_OR_INCOMPLETE', compare_inference.compare(self.original, self.native, .01)['status'])

    def test_raster_quantification(self):
        a = struct.pack('>ffff', 0, 1, 1, 2)
        b = struct.pack('>ffff', 1, 1, 2, 2)
        result = compare_inference.raster_differences(a, b)
        self.assertEqual(2, result['different_label_pixels'])
        self.assertEqual(1, result['different_foreground_pixels'])
        self.assertEqual(.75, result['foreground_intersection_over_union'])


if __name__ == '__main__':
    unittest.main()
