"""Strict evidence-gate tests. Fabricated reports here are test inputs, not passes."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import alignment_runtime as runtime
import compare_alignment as compare
import run_alignment_probe as run


def snapshot(spec, data, aligned=False):
    w, h, bits, ref = spec['width'], spec['height'], spec['bits'], spec['reference']
    return {'pixels_f32be_sha256': compare.digest(data), 'dimensions': [w, h, 1, 4, 1],
            'bit_depth': bits, 'title': spec['id'], 'open_as_hyperstack': False,
            'display_range': [10, 180] if bits == 8 else [100, 42000 if bits == 16 else 15000],
            'position': [1, ref, 1, ref] if aligned else [1, 1, 1, 1],
            'slice_labels': ['synthetic-plane-' + str(i) for i in range(1, 5)],
            'template_roi': [w // 6, h // 6, int(w * .7), int(h * .7)] if aligned else None,
            'calibration': [.37, .63, 2.5, 1.25, 'µm']}


def fixture(directory, variant):
    directory.mkdir(); result = directory / 'result'; result.mkdir()
    schedule = json.loads((compare.HERE / 'alignment-cases.json').read_text())
    _, source = run.macro_source(variant)
    native = variant == 'native'
    adapter = variant != 'original'
    record = {'schema_version': 1, 'scope': run.SCOPE, 'whole_calcium_macro_executed': False,
              'variant': variant, 'status': 'PASS_ALIGNMENT_BOUNDARY', 'schedule': schedule,
              'macro_source': source}
    launcher = dict(record, sources={'test-probe': 'a' * 64},
                    runtime_artifacts=[{'name': p['file'], 'sha256': p['sha256']} for p in runtime.artifacts()],
                    production_classes={'Features/Macros/LegacyTemplateMatching.class': 'b' * 64} if adapter else {},
                    compilation={'exit_code': 0, 'resource_stop_reason': None}, execution={'exit_code': 0, 'resource_stop_reason': None})
    if native:
        launcher['worker_files'] = {'gat-native-alignment.jar': 'c' * 64}
    name = 'Features.Macros.LegacyTemplateMatching' if adapter else 'TemplateMatching.Align_slices'
    target_hash = 'b' * 64 if adapter else runtime.artifacts()[0]['classes_sha256']['TemplateMatching/Align_slices.class']
    report = dict(record, backend='native' if native else 'legacy' if adapter else 'unset', original_menu='TemplateMatching.Align_slices("")',
                  target_class={'name': name, 'sha256': target_hash}, cases=[])
    for spec in schedule['cases']:
        rejected = spec['expected'] == 'rejected'; key = spec['id']; planes = compare.synthetic(spec, schedule)
        inp = compare.packed(planes)
        rx, ry = schedule['shifts'][spec['reference'] - 1]
        out = inp if rejected else compare.packed([compare.translate(plane, spec['width'], spec['height'], rx-dx, ry-dy)
                                                   for plane, (dx, dy) in zip(planes, schedule['shifts'])])
        macro = compare.expected_macro(spec, variant).encode()
        (result / (key + '.ijm')).write_bytes(macro)
        (result / (key + '-input.f32be')).write_bytes(inp)
        (result / (key + '-aligned.f32be')).write_bytes(out)
        row = {'case': spec, 'invoked_macro_sha256': compare.digest(macro), 'input': snapshot(spec, inp),
               'output': snapshot(spec, out, not rejected), 'sentinel_unchanged': True,
               'worker_processes': {'123': 'java TemplateMatching.NativeAlignmentMain input output'} if native and not rejected else {},
               'dispatched_commands': [] if native else ['Align slices in stack...'], 'macro_return': '',
               'errors': [], 'macro_thrown': None, 'ij_error': None, 'exception_window': '', 'exception_window_visible': False,
               'observed_macro_error_dialogs': [], 'observed_macro_guard_dialogs': [], 'continuation_observed': not rejected, 'log': '' if rejected else 'GAT_ALIGNMENT_AFTER_BOUNDARY_' + key + '\n'}
        if rejected:
            row.update(status='PASS_UNSUPPORTED_TYPE_CONTROL', input_unchanged=True, results_absent=True,
                       unsupported_type_diagnostic=True, ij_error=None, log='',
                       observed_macro_error_dialogs=[] if native else [compare.ORIGINAL_TYPE_ERROR + ' in line 7 run( Align slices in stack... )'],
                       observed_macro_guard_dialogs=[compare.NATIVE_GUARD_MESSAGE] if native else [])
        else:
            rows = compare.expected_rows(spec, schedule)
            data = ('Slice,dX,dY\n' + ''.join(','.join(map(str, r)) + '\n' for r in rows)).encode()
            (result / (key + '.csv')).write_bytes(data)
            row.update(status='PASS_ALIGNMENT_CASE', headings=['Slice', 'dX', 'dY'], rows=rows,
                       csv_roundtrip=True, results_visible=True, csv_sha256=compare.digest(data))
        report['cases'].append(row)
    (directory / 'launcher.json').write_text(json.dumps(launcher))
    (result / 'report.json').write_text(json.dumps(report))


class AlignmentComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.original = self.root / 'original'; self.native = self.root / 'native'
        fixture(self.original, 'original'); fixture(self.native, 'native')

    def edit(self, callback, side='native', launcher=False):
        path = (self.native if side == 'native' else self.original) / ('launcher.json' if launcher else 'result/report.json')
        value = json.loads(path.read_text()); callback(value); path.write_text(json.dumps(value))

    def rejected(self):
        result = compare.compare(self.original, self.native)
        self.assertEqual('FAIL_OR_INCOMPLETE', result['status'], result)
        self.assertTrue(result['errors'])

    def test_exact_complete_test_fixture_passes(self):
        result = compare.compare(self.original, self.native)
        self.assertEqual('PASS_PAIRED_MACRO_ALIGNMENT_SCOPE', result['status'], result)
        self.assertEqual(7, len(result['cases']))
        self.assertFalse(result['whole_calcium_macro_executed'])

    def test_legacy_delegate_compares_as_distinct_actual_backend(self):
        delegate = self.root / 'delegate'; fixture(delegate, 'legacy-delegate')
        result = compare.compare(self.original, delegate, 'legacy-delegate')
        self.assertEqual('PASS_PAIRED_MACRO_ALIGNMENT_SCOPE', result['status'], result)
        self.assertEqual('legacy-delegate', result['candidate_variant'])
        self.assertEqual('FAIL_OR_INCOMPLETE', compare.compare(self.original, delegate)['status'])

    def test_rejects_partial_passing_report(self):
        self.edit(lambda r: r['cases'].pop()); self.rejected()

    def test_rejects_duplicated_case(self):
        self.edit(lambda r: r['cases'].__setitem__(1, r['cases'][0])); self.rejected()

    def test_rejects_source_drift(self):
        self.edit(lambda r: r['macro_source'].update(sha256='d' * 64)); self.rejected()

    def test_rejects_inflated_scope(self):
        self.edit(lambda r: r.update(whole_calcium_macro_executed=True)); self.rejected()

    def test_rejects_compile_only(self):
        self.edit(lambda r: r.update(status='COMPILED_NOT_RUN'), launcher=True); self.rejected()

    def test_rejects_resource_stop(self):
        self.edit(lambda r: r['execution'].update(resource_stop_reason='ceiling'), launcher=True); self.rejected()

    def test_rejects_changed_dependency(self):
        self.edit(lambda r: r['runtime_artifacts'][0].update(sha256='d' * 64), launcher=True); self.rejected()

    def test_rejects_native_fallback(self):
        self.edit(lambda r: r.update(backend='auto')); self.rejected()

    def test_rejects_missing_real_worker(self):
        self.edit(lambda r: r['cases'][0].update(worker_processes={})); self.rejected()

    def test_rejects_original_native_contamination(self):
        self.edit(lambda r: r['cases'][0].update(worker_processes={'123': 'TemplateMatching.NativeAlignmentMain'}), side='original'); self.rejected()

    def test_rejects_wrong_production_class(self):
        self.edit(lambda r: r['target_class'].update(sha256='d' * 64)); self.rejected()

    def test_rejects_missing_original_dispatch(self):
        self.edit(lambda r: r['cases'][0].update(dispatched_commands=[]), side='original'); self.rejected()

    def test_rejects_reordered_motion_rows(self):
        self.edit(lambda r: r['cases'][1]['rows'].reverse()); self.rejected()

    def test_rejects_actual_csv_mismatch(self):
        p = self.native / 'result/synthetic8-ref1.csv'; p.write_text('Slice,dX,dY\n2,99,2\n3,4,-5\n4,0,0\n')
        self.edit(lambda r: r['cases'][0].update(csv_sha256=compare.digest(p.read_bytes()))); self.rejected()

    def test_rejects_different_invoked_macro_even_with_updated_hash(self):
        p = self.native / 'result/synthetic8-ref1.ijm'; p.write_text(p.read_text().replace('method=5', 'method=3'))
        self.edit(lambda r: r['cases'][0].update(invoked_macro_sha256=compare.digest(p.read_bytes()))); self.rejected()

    def test_rejects_changed_synthetic_pixels_even_with_updated_hash(self):
        p = self.native / 'result/synthetic8-ref1-input.f32be'; p.write_bytes(b'\x3f\x80\0\0' + p.read_bytes()[4:])
        self.edit(lambda r: r['cases'][0]['input'].update(pixels_f32be_sha256=compare.digest(p.read_bytes()))); self.rejected()

    def test_rejects_wrong_aligned_pixels_even_with_updated_hash(self):
        p = self.native / 'result/synthetic8-ref1-aligned.f32be'; p.write_bytes(b'\x3f\x80\0\0' + p.read_bytes()[4:])
        self.edit(lambda r: r['cases'][0]['output'].update(pixels_f32be_sha256=compare.digest(p.read_bytes()))); self.rejected()

    def test_rejects_roi_display_position_and_calibration_drift(self):
        for field, value in [('template_roi', None), ('display_range', [0, 255]), ('position', [1, 2, 1, 2]),
                             ('calibration', [.37, .37, 2.5, 1.25, 'µm'])]:
            with self.subTest(field=field):
                fixture_dir = self.root / ('bad-' + field); fixture(fixture_dir, 'native')
                p = fixture_dir / 'result/report.json'; r = json.loads(p.read_text()); r['cases'][0]['output'][field] = value; p.write_text(json.dumps(r))
                self.assertEqual('FAIL_OR_INCOMPLETE', compare.compare(self.original, fixture_dir)['status'])

    def test_rejects_invisible_table(self):
        self.edit(lambda r: r['cases'][0].update(results_visible=False)); self.rejected()

    def test_rejects_negative_without_actual_diagnostic(self):
        self.edit(lambda r: r['cases'][-1].update(observed_macro_guard_dialogs=[])); self.rejected()

    def test_rejects_negative_that_invoked_worker(self):
        self.edit(lambda r: r['cases'][-1].update(worker_processes={'1': 'TemplateMatching.NativeAlignmentMain'})); self.rejected()

    def test_rejects_missing_original_modal_error_evidence(self):
        self.edit(lambda r: r['cases'][-1].update(observed_macro_error_dialogs=[]), side='original')
        self.rejected()

    def test_rejects_unrelated_error_in_original_modal(self):
        self.edit(lambda r: r['cases'][-1].update(observed_macro_error_dialogs=[compare.ORIGINAL_TYPE_ERROR + ' in line 7 NullPointerException']), side='original')
        self.rejected()

    def test_rejects_expected_type_error_plus_unrelated_exception(self):
        self.edit(lambda r: r['cases'][-1].update(errors=['NullPointerException']))
        self.rejected()

    def test_rejects_expected_type_exception_plus_second_exception(self):
        self.edit(lambda r: r['cases'][-1].update(exception_window=r['cases'][-1]['exception_window'] + 'Caused by: java.lang.LinkageError\n'))
        self.rejected()

    def test_rejects_unrecorded_positive_log_error(self):
        self.edit(lambda r: r['cases'][0].update(log='java.lang.NullPointerException\n'))
        self.rejected()

    def test_rejects_different_macro_continuation_after_rejection(self):
        self.edit(lambda r: r['cases'][-1].update(continuation_observed=True,
                  log='GAT_ALIGNMENT_AFTER_BOUNDARY_' + r['cases'][-1]['case']['id'] + '\n'))
        result = compare.compare(self.original, self.native)
        self.assertEqual('FAIL_OR_INCOMPLETE', result['status'])
        self.assertEqual(6, sum(r['status'] == 'PASS_EXACT' for r in result['cases']))
        self.assertIn('continuation_observed', result['cases'][-1]['mismatches'])

    def test_rejects_continuation_even_if_both_reports_claim_it(self):
        for side in ('original', 'native'):
            self.edit(lambda r: r['cases'][-1].update(continuation_observed=True,
                      log='GAT_ALIGNMENT_AFTER_BOUNDARY_' + r['cases'][-1]['case']['id'] + '\n'), side=side)
        result = compare.compare(self.original, self.native)
        self.assertEqual('FAIL_OR_INCOMPLETE', result['status'])
        self.assertIn('rejected_input_continues', result['cases'][-1]['mismatches'])

    def test_rejects_changed_guard_success_token(self):
        p = self.native / 'result/synthetic8-ref1.ijm'
        p.write_text(p.read_text().replace('GAT_ALIGNMENT_OK', 'wrong-token'))
        self.edit(lambda r: r['cases'][0].update(invoked_macro_sha256=compare.digest(p.read_bytes())))
        self.rejected()

    def test_rejects_changed_harness_sources(self):
        self.edit(lambda r: r['sources'].update(another='d' * 64), launcher=True); self.rejected()

    def test_rejects_runtime_error_despite_pass_status(self):
        self.edit(lambda r: r['cases'][0].update(errors=['IOException'])); self.rejected()

    def test_expected_order_and_shifts_are_independent_of_reports(self):
        schedule = json.loads((compare.HERE / 'alignment-cases.json').read_text())
        self.assertEqual([[2, -7, 7], [1, -4, 5], [4, -4, 5]], compare.expected_rows(schedule['cases'][1], schedule))

    def test_csv_rejects_nonfinite_and_reordered_row_indices(self):
        for data in (b'Slice,dX,dY\n2,nan,0\n3,0,0\n4,0,0\n', b',Slice,dX,dY\n2,2,0,0\n1,3,0,0\n3,4,0,0\n'):
            with self.assertRaises(ValueError): compare.csv_rows(data)


class AlignmentRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)

    def jar(self, name, contents=()):
        p = self.root / name
        with zipfile.ZipFile(p, 'w') as z:
            for value in contents: z.writestr(value, b'unit-test')
        return p

    def test_rejects_hidden_fork_and_worker(self):
        for index, cls in enumerate(runtime.FORBIDDEN):
            with self.assertRaisesRegex(ValueError, 'contamination'): runtime.jar_names(self.jar(str(index) + '.jar', [cls]))

    def test_filters_renamed_bytedeco_and_original_plugin(self):
        for name, classes in [('renamed.jar', ['org/bytedeco/javacpp/Loader.class']), ('plugin.jar', ['TemplateMatching/Align_slices.class'])]:
            p = self.jar(name, classes); self.assertTrue(runtime.is_conflicting(p, runtime.jar_names(p)))

    def test_regular_foundation_is_retained(self):
        p = self.jar('ij-1.54p.jar', ['ij/IJ.class']); self.assertFalse(runtime.is_conflicting(p, runtime.jar_names(p)))

    def test_refuses_missing_pins_and_directory_classpath(self):
        with self.assertRaisesRegex(ValueError, 'five pinned'): runtime.validate([self.jar('ij-1.54p.jar')])
        with self.assertRaisesRegex(ValueError, 'Explicit runtime'): runtime.jar_names(self.root)

    def test_refuses_duplicate_filenames(self):
        p = self.jar('a.jar')
        with self.assertRaisesRegex(ValueError, 'duplicate'): runtime.validate([p, p])

    def test_refuses_changed_cached_bytes_without_network(self):
        p = self.jar('a.jar'); row = {'file': p.name, 'bytes': p.stat().st_size, 'sha256': '0' * 64}
        with patch.object(runtime.subprocess, 'run') as invoked:
            with self.assertRaisesRegex(ValueError, 'Cached dependency'): runtime.fetch(row, self.root)
            invoked.assert_not_called()

    def test_refuses_partial_download_without_network(self):
        (self.root / 'a.jar.download').write_bytes(b'partial')
        with patch.object(runtime.subprocess, 'run') as invoked:
            with self.assertRaisesRegex(ValueError, 'Incomplete download'): runtime.fetch({'file': 'a.jar'}, self.root)
            invoked.assert_not_called()

    def test_preparer_keeps_input_unchanged_and_records_filters(self):
        foundation = self.jar('ij-1.54p.jar', ['ij/IJ.class']); old = self.jar('opencv-new.jar', ['org/bytedeco/opencv/A.class'])
        pins = []
        for i in range(5):
            p = self.jar('pinned%d.jar' % i)
            pins.append({'file': p.name, 'bytes': p.stat().st_size, 'sha256': runtime.sha(p)})
        cp = self.root / 'classpath.txt'; cp.write_text(os.pathsep.join(map(str, [foundation, old])))
        before = cp.read_bytes()
        with patch.object(runtime, 'artifacts', return_value=pins):
            report = runtime.prepare(cp, self.root, self.root / 'output')
        self.assertEqual(before, cp.read_bytes()); self.assertTrue(old.exists())
        self.assertEqual([old.name], [p['name'] for p in report['removed_conflicting_dependencies']])
        self.assertFalse(report['software_executed'])
        with self.assertRaisesRegex(ValueError, 'overwritten'): runtime.prepare(cp, self.root, self.root / 'output')

    def test_original_macro_pin_and_native_only_transformation(self):
        original, a = run.macro_source('original'); native, b = run.macro_source('native')
        self.assertEqual(a, b)
        self.assertEqual(original.replace('run("Align slices in stack...",', 'gat_alignment_status=call("Features.Macros.LegacyTemplateMatching.run",')
                         + ' if(gat_alignment_status!="GAT_ALIGNMENT_OK") exit("MacroFork alignment failed: "+gat_alignment_status);', native)


if __name__ == '__main__':
    unittest.main()
