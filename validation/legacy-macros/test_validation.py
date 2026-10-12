"""Harness tests and deliberate evidence counterexamples, never runtime evidence."""
import copy
import itertools
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import audit_sources
import check_nms_report as checker


def report_fixture():
    """Fabricated unit fixture solely for testing report rejection/acceptance."""
    rows = []
    sentinel = ['existing-roi-sentinel', 0, 7, 0, 7, 0, [[1, 2], [3, 2], [3, 5], [1, 5]]]
    for (w, h), d, p, n, output, placement in itertools.product(
            ((33, 29), (32, 30)), (2, 4), checker.PROB, checker.NMS, checker.OUTPUTS, checker.POSITIONS):
        snap = {'label_present': output != 'ROI Manager', 'rois_in_manager_order': [sentinel] if output == 'Label Image' else []}
        if output != 'Label Image' and p < 1:
            snap['rois_in_manager_order'].append(['unit-roi', 2, 0, 0, 0, 0, [[7, 8], [9, 8], [9, 10]]])
        snap['roi_count_including_existing_sentinel'] = len(snap['rois_in_manager_order'])
        if snap['label_present']:
            snap.update(label_shape=[w, h], label_axes=['X', 'Y'], label_dtype='unit-fixture',
                        label_name='unit-fixture', label_pixels_sha256='2' * 64)
        rows.append({'shape': [w, h, 9], 'input_dimensions': d, 'probability': p, 'overlap': n,
                     'output_type': output, 'roi_position': placement,
                     'fixture': 'deterministic-synthetic-8-ray-peaks-v1',
                     'probability_sha256': '0' * 64, 'distance_sha256': '1' * 64,
                     'original': copy.deepcopy(snap), 'adapter': copy.deepcopy(snap),
                     'inputs_unchanged': True, 'auxiliary_pixels_match': True, 'pass': True})
    return {'schema_version': 1, 'scope': 'original-nms-vs-adapter-postprocessing-only',
            'model_execution': False, 'whole_macro_execution': False,
            'status': 'PASS_POSTPROCESSING_SCOPE', 'case_count': 720, 'cases': rows,
            'original_class': {'name': 'de.csbdresden.stardist.StarDist2DNMS',
                               'code_source': 'unit-fixture-only.jar', 'class_sha256': '3' * 64},
            'adapter_class': {'name': 'Features.Macros.LegacyMacroStarDist',
                             'code_source': 'unit-fixture-only.jar', 'class_sha256': '4' * 64}}


class ReportCheckerTest(unittest.TestCase):
    def setUp(self):
        self.report = report_fixture()

    def assertRejected(self):
        self.assertEqual('FAIL_EVIDENCE', checker.check(self.report)['status'])

    def test_complete_well_formed_unit_fixture(self):
        self.assertEqual('PASS_POSTPROCESSING_SCOPE', checker.check(self.report)['status'])

    def test_empty_report_cannot_pass(self):
        self.report['cases'] = []
        self.assertRejected()

    def test_missing_setting_cannot_pass(self):
        self.report['cases'].pop()
        self.assertRejected()

    def test_duplicate_cannot_replace_missing_setting(self):
        self.report['cases'][-1] = copy.deepcopy(self.report['cases'][0])
        self.assertRejected()

    def test_label_difference_rejected_even_with_equal_counts(self):
        self.report['cases'][0]['adapter']['label_pixels_sha256'] = 'a' * 64
        self.assertRejected()

    def test_subpixel_roi_geometry_change_rejected(self):
        self.report['cases'][0]['adapter']['rois_in_manager_order'][0][-1][0][0] += .125
        self.assertRejected()

    def test_roi_position_change_rejected(self):
        self.report['cases'][0]['adapter']['rois_in_manager_order'][0][5] = 1
        self.assertRejected()

    def test_unexecuted_status_rejected(self):
        self.report['status'] = 'BLOCKED_SETUP'
        self.assertRejected()

    def test_cannot_claim_inference_or_macro_scope(self):
        self.report['whole_macro_execution'] = True
        self.assertRejected()

    def test_class_provenance_required(self):
        del self.report['original_class']['class_sha256']
        self.assertRejected()

    def test_empty_default_is_not_positive_control(self):
        for row in self.report['cases']:
            for variant in ('original', 'adapter'):
                if row['output_type'] != 'Label Image':
                    row[variant]['rois_in_manager_order'] = []
                    row[variant]['roi_count_including_existing_sentinel'] = 0
        self.assertRejected()


class SourceAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((audit_sources.HERE / 'source-manifest.json').read_text())
        cls.names = [r['path'] for r in cls.manifest['files']]

    def test_reference_revision_is_legacy_not_java_v2(self):
        self.assertEqual('f2098636d5f42f73c3e724286af0b212fe3ea5c0', self.manifest['source_revision'])
        self.assertEqual(47, len(self.names))

    def test_live_source_bytes_match_actual_historical_git_blobs(self):
        self.assertEqual('PASS_SOURCE_CONTRACT', audit_sources.audit(audit_sources.ROOT, self.manifest)['status'])

    def test_unrecognized_native_command_site_rejected(self):
        with self.assertRaises(ValueError):
            audit_sources.expected_overlay('unexpected.ijm',
                b'run("Command From Macro", "command=[de.csbdresden.stardist.StarDist2D]");', self.names)

    def test_overlay_and_deliberately_changed_float_open(self):
        with tempfile.TemporaryDirectory() as temporary:
            for corrupt in (False, True):
                path = Path(temporary) / ('bad.zip' if corrupt else 'good.zip')
                with zipfile.ZipFile(path, 'w') as archive:
                    for name in self.names:
                        data = audit_sources.expected_overlay(name, (audit_sources.ROOT / name).read_bytes(), self.names)
                        if corrupt and name == 'Tools/commands/Segment_Ganglia.ijm':
                            self.assertIn(b'iterations=3 count=2 black do=Open', data)
                            data = data.replace(b'iterations=3 count=2 black do=Open', b'iterations=1 count=2 black do=Open')
                        archive.writestr(audit_sources.destination(name), data)
                actual = audit_sources.audit(audit_sources.ROOT, self.manifest, path)['status']
                self.assertEqual('FAIL_SOURCE_CONTRACT' if corrupt else 'PASS_SOURCE_CONTRACT', actual)

    def test_custom_settings_need_explicit_exact_reference(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'settings.zip'
            settings = Path(temporary) / 'gat_settings.ijm'
            settings.write_bytes(b'Parameters\tValues\tUnit\nprob_neuron\t0.8\t\n')
            with zipfile.ZipFile(path, 'w') as archive:
                for name in self.names:
                    data = audit_sources.expected_overlay(name, (audit_sources.ROOT / name).read_bytes(), self.names)
                    if name == 'Tools/commands/gat_settings.ijm':
                        data = settings.read_bytes()
                    archive.writestr(audit_sources.destination(name), data)
            self.assertEqual('FAIL_SOURCE_CONTRACT', audit_sources.audit(audit_sources.ROOT, self.manifest, path)['status'])
            self.assertEqual('PASS_SOURCE_CONTRACT', audit_sources.audit(audit_sources.ROOT, self.manifest, path, settings)['status'])


if __name__ == '__main__':
    unittest.main()
