import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import prepare
import run
import freeze_manifest


class ScopeTests(unittest.TestCase):
    def test_frozen_scope_and_stains(self):
        manifest = prepare.load_manifest()
        self.assertEqual(len(manifest['cases']), 40)
        self.assertEqual(manifest['input_pixels'], 26030351)
        self.assertEqual(manifest['stains'], {'Hu': 25, 'Calbindin': 3, 'ChAT': 3, 'Calretinin': 2, 'Neurofilament': 2, 'nNOS': 5})
        self.assertEqual(len({c['input_sha256'] for c in manifest['cases']}), 39)
        self.assertEqual(sum(bool(c['same_train_input_case_ids']) for c in manifest['cases']), 1)
        for c in manifest['cases']:
            self.assertEqual(c['crop']['width'], c['width'])
            self.assertEqual(c['crop']['height'], c['height'])
            self.assertEqual(c['crop']['x'], 0)
            self.assertEqual(c['crop']['y'], 0)

    def test_freeze_is_reproducible_from_existing_references(self):
        self.assertEqual(freeze_manifest.build(), prepare.load_manifest())

    def test_reference_hashes(self):
        prepare.verify_references(prepare.load_manifest())

    def test_tile_plan_exact_odd_dimensions(self):
        plan = freeze_manifest.tile_plan(1576, 1181)
        self.assertEqual((plan['tiles_x'], plan['tiles_y']), (2, 2))
        self.assertEqual((plan['core_width'], plan['core_height']), (832, 640))
        self.assertEqual((plan['input_tile_width'], plan['input_tile_height']), (960, 768))

    def test_expected_native_host(self):
        run.require_native_mac(dict(system='Darwin', machine='arm64', java={'os.arch': 'aarch64'}))

    def test_rosetta_rejected(self):
        with self.assertRaises(ValueError):
            run.require_native_mac(dict(system='Darwin', machine='arm64', java={'os.arch': 'aarch64'}, **{'sysctl.proc_translated': '1'}))

    def test_wrong_java_and_linux_rejected(self):
        for host in [dict(system='Linux', machine='aarch64', java={'os.arch': 'aarch64'}),
                     dict(system='Darwin', machine='arm64', java={'os.arch': 'x86_64'})]:
            with self.assertRaises(ValueError):
                run.require_native_mac(host)

    def test_mixed_worker_classpath_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'worker.jar').write_bytes(b'worker')
            (root / 'lib').mkdir()
            (root / 'lib/tensorflow-1.15.jar').write_bytes(b'legacy')
            with self.assertRaises(ValueError):
                run.worker_inventory(root / 'worker.jar', 'macosx-arm64')

    def test_killed_worker_partial_outputs_and_extraction_are_cleaned(self):
        with tempfile.TemporaryDirectory() as temp:
            case_dir = Path(temp) / 'case'
            scratch = case_dir / 'worker-scratch'
            scratch.mkdir(parents=True)
            script = ("from pathlib import Path; import time; "
                      f"p=Path({str(scratch)!r}); "
                      "(p/'.gat-result-failed.tmp').write_bytes(b'partial prediction'); "
                      "(p/'jvm-tmp/model-extract').mkdir(parents=True); "
                      "(p/'jvm-tmp/model-extract/variables').write_bytes(b'model'); time.sleep(30)")
            with self.assertRaises(subprocess.TimeoutExpired):
                run.timed_run([sys.executable, '-c', script], case_dir / 'worker.log', 0.3)
            inventory = run.worker_scratch_inventory(scratch)
            self.assertEqual(inventory['files'], 2)
            self.assertEqual(inventory['partial_prediction_sha256']['.gat-result-failed.tmp'], hashlib.sha256(b'partial prediction').hexdigest())
            run.cleanup_worker_scratch(scratch, case_dir)
            self.assertFalse(scratch.exists())
            self.assertTrue((case_dir / 'worker.log').is_file())

    def test_cleanup_refuses_unowned_or_symlinked_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            case_dir = Path(temp) / 'case'
            case_dir.mkdir()
            elsewhere = Path(temp) / 'important'
            elsewhere.mkdir()
            with self.assertRaises(ValueError):
                run.cleanup_worker_scratch(elsewhere, case_dir)
            scratch = case_dir / 'worker-scratch'
            scratch.symlink_to(elsewhere, target_is_directory=True)
            with self.assertRaises(ValueError):
                run.cleanup_worker_scratch(scratch, case_dir)
            self.assertTrue(elsewhere.exists())

    def test_corrupted_input_rejected(self):
        case = prepare.load_manifest()['cases'][0]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'input.gati'
            path.write_bytes(b'bad')
            with self.assertRaises(ValueError):
                run.check_input(path, case)

    def test_fetch_never_accepts_unverified_existing_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'file'
            path.write_bytes(b'corrupt')
            with self.assertRaises(ValueError):
                prepare.fetch(path, 'https://example.invalid', 'a' * 64, 20, False)

    def test_fetch_does_not_download_without_flag(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(FileNotFoundError), mock.patch('urllib.request.urlopen') as urlopen:
                prepare.fetch(Path(temp) / 'missing', 'https://example.invalid', 'a' * 64, 20, False)
            urlopen.assert_not_called()


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.case = copy.deepcopy(prepare.load_manifest()['cases'][0])
        self.geometry = dict(width=self.case['width'], height=self.case['height'], channels=97,
                             probability_threshold=0.5, nms_threshold=0.3, excluded_boundary=2)
        for key, value in self.case['legacy_expected'].items():
            self.geometry[key.replace('legacy_', 'modern_')] = value
        self.geometry.update(legacy_label_sha256=None, legacy_canonical_sha256=None, legacy_measurements_sha256=None,
                             legacy_count=self.case['legacy_expected']['legacy_count'])

    def test_exact_hashes_preserve_qualification(self):
        report = run.reference_comparison(self.case, self.geometry)
        self.assertTrue(report['exact_raster_and_measurements_equal'])
        self.assertFalse(report['tensor_numerical_comparison_performed'])
        self.assertFalse(report['legacy_composite_available'])
        self.assertEqual(report['original_exclusive_label_difference_count'], 0)

    def test_label_id_changes_do_not_fail_canonical_geometry(self):
        self.geometry['modern_label_sha256'] = 'different'
        report = run.reference_comparison(self.case, self.geometry)
        self.assertTrue(report['exact_raster_and_measurements_equal'])
        self.assertFalse(report['exact_raw_label_ids_and_pixels_equal'])

    def test_mismatch_without_order_has_null_pixel_delta(self):
        self.geometry['modern_canonical_sha256'] = 'different'
        report = run.reference_comparison(self.case, self.geometry)
        self.assertFalse(report['exact_raster_and_measurements_equal'])
        self.assertIsNone(report['original_exclusive_label_difference_count'])
        self.assertFalse(report['original_exclusive_label_difference_count_available'])

    def test_changed_measurement_is_not_equal(self):
        self.geometry['modern_measurements_sha256'] = 'different'
        self.assertFalse(run.reference_comparison(self.case, self.geometry)['exact_raster_and_measurements_equal'])

    def test_bad_legacy_reconstruction_rejected(self):
        self.geometry['legacy_canonical_sha256'] = 'not original'
        with self.assertRaises(ValueError):
            run.reference_comparison(self.case, self.geometry)

    def test_verified_order_can_supply_mismatch_pixel_delta(self):
        self.case['legacy_order_available'] = True
        for field in ('label_sha256', 'canonical_sha256', 'measurements_sha256'):
            self.geometry['legacy_' + field] = self.case['legacy_expected']['legacy_' + field]
        self.geometry['modern_canonical_sha256'] = 'different'
        self.geometry['different_canonical_label_pixels'] = 7
        report = run.reference_comparison(self.case, self.geometry)
        self.assertEqual(report['original_exclusive_label_difference_count'], 7)

    def test_missing_required_legacy_reconstruction_rejected(self):
        self.case['legacy_order_available'] = True
        with self.assertRaises(ValueError):
            run.reference_comparison(self.case, self.geometry)

    def test_legacy_count_change_rejected(self):
        self.geometry['legacy_count'] += 1
        with self.assertRaises(ValueError):
            run.reference_comparison(self.case, self.geometry)

    def test_changed_shape_rejected(self):
        self.geometry['width'] += 1
        with self.assertRaises(ValueError):
            run.reference_comparison(self.case, self.geometry)

    def test_changed_threshold_rejected(self):
        self.geometry['probability_threshold'] = 0.49
        with self.assertRaises(ValueError):
            run.reference_comparison(self.case, self.geometry)


class FinalizationTests(unittest.TestCase):
    def run_control(self, failure):
        with tempfile.TemporaryDirectory() as temp:
            case_dir = Path(temp)
            scratch = case_dir / 'worker-scratch'
            scratch.mkdir()
            prediction = scratch / 'actual.gato'
            prediction.write_bytes(b'prediction')
            (case_dir / 'actual.geometry.json').write_text('{}')
            report = dict(case_id='last_case', status='comparison_ready')
            if failure == 'cleanup':
                patch = mock.patch.object(run, 'cleanup_worker_scratch', side_effect=OSError('cleanup failed'))
            elif failure == 'save':
                original = run.save
                def save(path, value):
                    if value.get('status') == 'compared':
                        raise OSError('terminal report save failed')
                    return original(path, value)
                patch = mock.patch.object(run, 'save', side_effect=save)
            else:
                patch = mock.patch.object(run, 'digest', side_effect=OSError('artifact hashing failed'))
            with patch, self.assertRaises(OSError):
                run.finalize_case(report, case_dir, scratch, prediction, False)
            self.assertEqual(report['status'], 'failed')
            self.assertIn('evidence_finalization_error', report)
            persisted = json.loads((case_dir / 'case.json').read_text())
            self.assertEqual(persisted['status'], 'failed')

    def test_last_case_cleanup_failure_never_compared(self):
        self.run_control('cleanup')

    def test_last_case_terminal_save_failure_never_compared(self):
        self.run_control('save')

    def test_last_case_hash_failure_never_compared(self):
        self.run_control('hash')

    def test_compared_is_committed_only_after_cleanup_and_save(self):
        with tempfile.TemporaryDirectory() as temp:
            case_dir = Path(temp)
            scratch = case_dir / 'worker-scratch'
            scratch.mkdir()
            prediction = scratch / 'actual.gato'
            prediction.write_bytes(b'prediction')
            report = dict(status='comparison_ready')
            run.finalize_case(report, case_dir, scratch, prediction, False)
            self.assertFalse(scratch.exists())
            self.assertEqual(report['status'], 'compared')
            self.assertEqual(json.loads((case_dir / 'case.json').read_text()), report)


class ReportTests(unittest.TestCase):
    def test_complete_is_not_equivalence(self):
        manifest = prepare.load_manifest()
        rows = [dict(case_id=c['case_id'], status='compared', comparison={'exact_raster_and_measurements_equal': True}) for c in manifest['cases']]
        report = run.summary(manifest, rows, {'evidence_manifest_committed': True})
        self.assertTrue(report['run_completed'])
        self.assertTrue(report['all40_exact_identity_insensitive_raster_and_measurement_hashes_equal'])
        self.assertFalse(report['scientific_equivalence_established'])
        self.assertFalse(report['native_all40_completed'])

    def test_complete_with_difference_still_reports_difference(self):
        manifest = prepare.load_manifest()
        rows = [dict(case_id=c['case_id'], status='compared', comparison={'exact_raster_and_measurements_equal': True}) for c in manifest['cases']]
        rows[0]['comparison']['exact_raster_and_measurements_equal'] = False
        report = run.summary(manifest, rows, {'evidence_manifest_committed': True})
        self.assertTrue(report['run_completed'])
        self.assertEqual(report['exact_raster_and_measurement_case_count'], 39)
        self.assertFalse(report['all40_exact_identity_insensitive_raster_and_measurement_hashes_equal'])

    def test_subset_never_claims_full_completion(self):
        rows = [dict(status='compared', comparison={'exact_raster_and_measurements_equal': True})]
        self.assertFalse(run.summary(prepare.load_manifest(), rows, {})['run_completed'])

    def test_outer_error_prevents_completion_even_with40_compared(self):
        manifest = prepare.load_manifest()
        rows = [dict(case_id=c['case_id'], status='compared', comparison={'exact_raster_and_measurements_equal': True}) for c in manifest['cases']]
        self.assertFalse(run.summary(manifest, rows, {'setup_or_run_error': 'cleanup failed', 'evidence_manifest_committed': True})['run_completed'])

    def test_no_complete_until_artifact_manifest_committed(self):
        manifest = prepare.load_manifest()
        rows = [dict(case_id=c['case_id'], status='compared', comparison={'exact_raster_and_measurements_equal': True}) for c in manifest['cases']]
        self.assertFalse(run.summary(manifest, rows, {'evidence_manifest_committed': False})['run_completed'])

    def test_duplicate_ids_do_not_masquerade_as_complete(self):
        manifest = prepare.load_manifest()
        rows = [dict(case_id=manifest['cases'][0]['case_id'], status='compared', comparison={'exact_raster_and_measurements_equal': True}) for _ in range(40)]
        report = run.summary(manifest, rows, {'evidence_manifest_committed': True})
        self.assertFalse(report['run_completed'])
        self.assertEqual(len(report['missing_case_ids']), 39)

    def test_failed_and_blocked_cases_count(self):
        rows = [dict(status='failed'), dict(status='blocked'), dict(status='not_run')]
        report = run.summary(prepare.load_manifest(), rows, {})
        self.assertEqual(report['failed_cases'], 1)
        self.assertEqual(report['blocked_cases'], 1)
        self.assertEqual(report['pending_cases'], 1)
        self.assertFalse(report['run_completed'])


if __name__ == '__main__':
    unittest.main()
