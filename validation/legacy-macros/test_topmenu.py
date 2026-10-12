"""Gate unit tests only; no real GUI or model runs are implied."""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import compare_topmenu as checker
import prepare_topmenu
import audit_sources
import build_impact_matrix


def roi(name='Neuron_1', x=5.0):
    return [name, 0, 0, 0, 0, 0, [[x, 7.0], [x + 5, 7.0], [x + 5, 9.0], [x, 9.0]]]


class RoiGateTests(unittest.TestCase):
    def test_identical(self):
        self.assertEqual(checker.roi_difference([roi()], [roi()], 0), (0, True))

    def test_default_is_strict(self):
        diff, passed = checker.roi_difference([roi()], [roi(x=5.01)], 0)
        self.assertFalse(passed); self.assertGreater(diff, .009)

    def test_explicit_tolerance_only_vertices(self):
        self.assertTrue(checker.roi_difference([roi()], [roi(x=5.01)], .011)[1])
        with self.assertRaises(ValueError): checker.roi_difference([roi()], [roi('wrong')], 100)

    def test_order_count_positions_never_tolerated(self):
        for other in ([], [roi(), roi()], [[*roi()[:5], 1, roi()[6]]]):
            with self.assertRaises(ValueError): checker.roi_difference([roi()], other, 100)

    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError): checker.roi_difference([roi()], [roi(x=math.nan)], 1)

    def test_no_report_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as d:
            result = checker.compare(Path(d))
            self.assertEqual(result['status'], 'FAIL_OR_INCOMPLETE')

    def test_invalid_tolerance(self):
        for tolerance in (-1, math.nan, math.inf):
            self.assertEqual(checker.compare(Path('/does-not-exist'), tolerance)['status'], 'FAIL_OR_INCOMPLETE')


class InstallationTests(unittest.TestCase):
    def test_driver_forwards_config_with_explicit_call_boundary(self):
        actual = prepare_topmenu.driver_macro(Path('/public fixture/config.json'))
        self.assertEqual(actual, 'call("LegacyMacroTopMenuProbe.launch", "/public fixture/config.json");\n')
        self.assertNotIn('run("Legacy Macro Top Menu Probe"', actual)
        java = (prepare_topmenu.HERE / 'LegacyMacroTopMenuProbe.java').read_text()
        self.assertIn('public static String launch(String config)', java)
        self.assertIn('new LegacyMacroTopMenuProbe().run(config);', java)

    def test_fork_and_probe_jars_excluded_original(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for name, member, excluded in [('legacy.jar', 'de/example/Original.class', False),
                    ('innocent-name.jar', 'Features/Macros/LegacyMacroStarDist.class', True),
                    ('custom.jar', 'org/gatanalysis/inference/NativeInferenceMain.class', True),
                    ('GAT_any.jar', 'X.class', True), ('ValidationProbe.jar', 'X.class', True)]:
                path=d/name
                with zipfile.ZipFile(path,'w') as z: z.writestr(member,b'fixture')
                self.assertEqual(prepare_topmenu.excluded_jar(path),excluded)

    def test_immutable_link_and_script_changes_detected(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); binary=d/'runtime.jar'; binary.write_bytes(b'fixture')
            script=d/'script.ijm'; script.write_text('original')
            path=d/'installation.json'
            path.write_text(json.dumps({'linked_files':[{'source':str(binary),'destination':str(binary),'sha256':prepare_topmenu.sha(binary)}],
                                        'script_files':[{'path':str(script),'sha256':prepare_topmenu.sha(script)}]}))
            self.assertEqual(prepare_topmenu.verify(path),0)
            script.write_text('modified')
            self.assertEqual(prepare_topmenu.verify(path),1)
            script.write_text('original'); binary.write_bytes(b'modified')
            self.assertEqual(prepare_topmenu.verify(path),1)


class ImpactMapTests(unittest.TestCase):
    def test_all_scripts_and_exact_changed_boundaries(self):
        manifest=json.loads((audit_sources.HERE/'source-manifest.json').read_text())
        names=[r['path'] for r in manifest['files']]
        with tempfile.TemporaryDirectory() as d:
            overlay=Path(d)/'overlay.zip'
            with zipfile.ZipFile(overlay,'w') as z:
                for name in names:
                    z.writestr(audit_sources.destination(name),audit_sources.expected_overlay(name,(audit_sources.ROOT/name).read_bytes(),names))
            result=build_impact_matrix.matrix(overlay)
        self.assertEqual(result['change_totals'],{'scripts':47,'stardist_sites':8,'alignment_sites':3,'alignment_fail_stop_guards':3,'settings_option_path_quotes':7,'unallowlisted_computation_changes':0})
        self.assertTrue(result['not_a_runtime_result'])
        by_name={r['source']:r for r in result['scripts']}
        self.assertEqual(by_name['Analysis/_Merge_Results.ijm']['impact'],'filename-menu-namespace-only')
        self.assertIn('batch-command-routing-probe',by_name['Batch_mode/batch_mode_example.ijm']['required_evidence'])
        self.assertEqual(len(by_name),47)


if __name__ == '__main__': unittest.main()
