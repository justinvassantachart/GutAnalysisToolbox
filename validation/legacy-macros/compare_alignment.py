#!/usr/bin/env python3
"""Fail-closed original/native actual macro alignment comparison.

Independently reconstructs Java's seeded synthetic input, the expected integer
translations and raw output pixels. Exact geometry, CSV row order, metadata,
visible Results, native-worker evidence and clean unsupported-type rejection
are mandatory. Does not promote this boundary test to a whole-workflow claim.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import re
from pathlib import Path
import struct

from alignment_runtime import artifacts
from run_alignment_probe import macro_source, SCOPE

HERE = Path(__file__).resolve().parent
NATIVE_TYPE_ERROR = 'java.lang.IllegalArgumentException: Native Template Matching requires an 8/16-bit stack, valid reference slice and at most 67,108,864 total pixels'
ORIGINAL_TYPE_ERROR = '"Align slices in stack..." requires an image of type: 8-bit grayscale 16-bit grayscale'
ERROR_PATTERN = re.compile(r'exception|\[error\]|no such method|unsatisfiedlink', re.I)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def translate(plane, width, height, dx, dy):
    return [plane[(y - dy) * width + x - dx] if 0 <= x - dx < width and 0 <= y - dy < height else 0.0
            for y in range(height) for x in range(width)]


def f32(value):
    return struct.unpack('>f', struct.pack('>f', value))[0]


def synthetic(spec, schedule):
    """Independent Python implementation of java.util.Random.nextInt(bound)."""
    state = (schedule['seed'] ^ 0x5DEECE66D) & ((1 << 48) - 1)
    def next_int(bound):
        nonlocal state
        while True:
            state = (state * 0x5DEECE66D + 0xB) & ((1 << 48) - 1)
            bits = state >> 17
            value = bits % bound
            if bits - value + bound - 1 < (1 << 31):
                return value
    width, height, bits = spec['width'], spec['height'], spec['bits']
    base = [0.0] * (width * height)
    for y in range(10, height - 10):
        for x in range(10, width - 10):
            value = next_int(200 if bits == 8 else 50000) + 1
            base[y * width + x] = f32(f32(value * f32(.37)) - f32(17.25)) if bits == 32 else float(value)
    return [translate(base, width, height, dx, dy) for dx, dy in schedule['shifts']]


def packed(planes):
    return b''.join(struct.pack('>f', value) for plane in planes for value in plane)


def expected_rows(spec, schedule):
    ref = spec['reference']; rx, ry = schedule['shifts'][ref - 1]
    return [[i, rx - schedule['shifts'][i - 1][0], ry - schedule['shifts'][i - 1][1]]
            for i in [*range(ref - 1, 0, -1), *range(ref + 1, len(schedule['shifts']) + 1)]]


def csv_rows(data):
    rows = list(csv.reader(io.StringIO(data.decode('utf-8-sig'))))
    if len(rows) != 4:
        raise ValueError('CSV must have one header and three motion rows')
    header = rows[0]
    if header == ['', 'Slice', 'dX', 'dY'] or header == [' ', 'Slice', 'dX', 'dY']:
        if [row[0] for row in rows[1:]] != ['1', '2', '3']:
            raise ValueError('CSV row index/order differs')
        values = [row[1:] for row in rows[1:]]
    elif header == ['Slice', 'dX', 'dY']:
        values = rows[1:]
    else:
        raise ValueError('Unexpected motion CSV columns')
    result = [[float(value) for value in row] for row in values]
    if any(len(row) != 3 or any(not math.isfinite(value) for value in row) for row in result):
        raise ValueError('Nonfinite/incomplete motion CSV')
    return result


def expected_macro(spec, variant):
    line, _ = macro_source(variant)
    line = line.replace('ref.slice=3', 'ref.slice=' + str(spec['reference']))
    return ('selectWindow("' + spec['id'] + '");\nsizeX=' + str(spec['width']) + ';sizeY=' + str(spec['height'])
            + ';\nx_size=floor(sizeX*0.7);\ny_size=floor(sizeY*0.7);\nx0=floor(sizeX/6);\ny0=floor(sizeY/6);\n' + line + '\nprint("GAT_ALIGNMENT_AFTER_BOUNDARY_' + spec['id'] + '");\n')


def verify_snapshot(snapshot, spec, data, aligned):
    w, h, bits, ref = spec['width'], spec['height'], spec['bits'], spec['reference']
    expected = {'pixels_f32be_sha256': digest(data), 'dimensions': [w, h, 1, 4, 1],
                'bit_depth': bits, 'title': spec['id'], 'open_as_hyperstack': False,
                'display_range': [10, 180] if bits == 8 else [100, 42000 if bits == 16 else 15000],
                'position': [1, ref, 1, ref] if aligned else [1, 1, 1, 1],
                'slice_labels': ['synthetic-plane-' + str(i) for i in range(1, 5)],
                'template_roi': [w // 6, h // 6, math.floor(w * .7), math.floor(h * .7)] if aligned else None}
    for key, value in expected.items():
        if snapshot.get(key) != value:
            raise ValueError('Unexpected ' + key + ': ' + spec['id'])
    cal = snapshot.get('calibration', [])
    if len(cal) != 5 or cal[:4] != [.37, .63, 2.5, 1.25] or cal[4] not in ('um', 'µm', 'μm'):
        raise ValueError('Lost/changed calibration: ' + spec['id'])


def load_side(directory, variant):
    launcher = json.loads((directory / 'launcher.json').read_text())
    report = json.loads((directory / 'result/report.json').read_text())
    schedule = json.loads((HERE / 'alignment-cases.json').read_text())
    _, source = macro_source(variant)
    for record in (launcher, report):
        if (record.get('schema_version') != 1 or record.get('status') != 'PASS_ALIGNMENT_BOUNDARY'
                or record.get('scope') != SCOPE or record.get('whole_calcium_macro_executed') is not False
                or record.get('variant') != variant or record.get('schedule') != schedule or record.get('macro_source') != source):
            raise ValueError('Incomplete, wrong-scope, wrong-source or wrong-variant alignment evidence')
    for stage in ('compilation', 'execution'):
        if launcher.get(stage, {}).get('exit_code') != 0 or launcher[stage].get('resource_stop_reason'):
            raise ValueError('Unsuccessful bounded ' + stage)
    runtime = launcher.get('runtime_artifacts', [])
    if len(runtime) != len({p['name'] for p in runtime}):
        raise ValueError('Duplicate runtime artifacts')
    actual_artifacts = {p['name']: p['sha256'] for p in runtime}
    for artifact in artifacts():
        if actual_artifacts.get(artifact['file']) != artifact['sha256']:
            raise ValueError('Missing/changed pinned original alignment dependency')
    target = report.get('target_class', {})
    native = variant == 'native'
    class_name = 'Features.Macros.LegacyTemplateMatching' if native else 'TemplateMatching.Align_slices'
    expected_hash = launcher.get('production_classes', {}).get('Features/Macros/LegacyTemplateMatching.class') if native else artifacts()[0]['classes_sha256']['TemplateMatching/Align_slices.class']
    if not expected_hash or target.get('name') != class_name or target.get('sha256') != expected_hash:
        raise ValueError('Wrong actual production/original command class')
    if native:
        if report.get('backend') != 'native' or not launcher.get('worker_files', {}).get('gat-native-alignment.jar'):
            raise ValueError('Native worker/backend not established')
    elif report.get('backend') != 'unset' or launcher.get('production_classes') or launcher.get('worker_files'):
        raise ValueError('Original control contaminated by fork')
    if 'TemplateMatching.Align_slices' not in report.get('original_menu', ''):
        raise ValueError('Original registered menu absent')
    observed = report.get('cases', [])
    if [r.get('case') for r in observed] != schedule['cases']:
        raise ValueError('Missing/duplicate/reordered/changed scheduled cases')
    results = {}
    for row, spec in zip(observed, schedule['cases']):
        name = spec['id']; rejected = spec['expected'] == 'rejected'
        prefix = directory / 'result' / name
        invoked = prefix.with_suffix('.ijm').read_bytes()
        if invoked.decode() != expected_macro(spec, variant) or digest(invoked) != row.get('invoked_macro_sha256'):
            raise ValueError('Executed macro source/settings were changed: ' + name)
        inp = Path(str(prefix) + '-input.f32be').read_bytes()
        out = Path(str(prefix) + '-aligned.f32be').read_bytes()
        planes = synthetic(spec, schedule)
        if inp != packed(planes):
            raise ValueError('Input is not the exact public seeded synthetic fixture: ' + name)
        verify_snapshot(row['input'], spec, inp, False)
        verify_snapshot(row['output'], spec, out, not rejected)
        expected_processes = 1 if native and not rejected else 0
        processes = row.get('worker_processes', {})
        if len(processes) != expected_processes or any('TemplateMatching.NativeAlignmentMain' not in s for s in processes.values()):
            raise ValueError('Missing/wrong actual native worker evidence: ' + name)
        if row.get('dispatched_commands', []).count('Align slices in stack...') != (0 if native else 1):
            raise ValueError('Missing/wrong actual original command dispatch: ' + name)
        if row.get('sentinel_unchanged') is not True:
            raise ValueError('Unrelated image changed')
        if rejected:
            if row.get('status') != 'PASS_UNSUPPORTED_TYPE_CONTROL' or any(row.get(key) is not True for key in
                    ('input_unchanged', 'results_absent', 'unsupported_type_diagnostic')) or inp != out:
                raise ValueError('Unsupported-type negative control failed')
            marker = 'GAT_ALIGNMENT_AFTER_BOUNDARY_' + name
            log = row.get('log', '')
            remaining_log = ' '.join(log.replace(marker, '').split())
            exception = row.get('exception_window', '')
            allowed_thrown = (None, '') if native else (None, '', 'java.lang.RuntimeException: Macro canceled')
            if row.get('errors') or row.get('macro_thrown') not in allowed_thrown:
                raise ValueError('Unrelated exception beside unsupported-type diagnostic')
            if type(row.get('continuation_observed')) is not bool or row['continuation_observed'] != (marker in log):
                raise ValueError('Missing/inconsistent after-call continuation observation')
            if native:
                lines = exception.splitlines()
                if (not lines or lines[0] != NATIVE_TYPE_ERROR or any(line.strip() and not line.strip().startswith('at ') for line in lines[1:])
                        or remaining_log or row.get('ij_error') or row.get('observed_macro_error_dialogs')
                        or row.get('exception_window_visible') is not True):
                    raise ValueError('Missing or contaminated native unsupported-type exception window')
            else:
                dialogs = row.get('observed_macro_error_dialogs', [])
                if (len(dialogs) != 1 or not ' '.join(dialogs[0].split()).startswith(ORIGINAL_TYPE_ERROR + ' in line ')
                        or ERROR_PATTERN.search(dialogs[0]) or remaining_log or row.get('ij_error') or exception
                        or row.get('exception_window_visible')):
                    raise ValueError('Missing or contaminated original supported-type Macro Error dialog')
            if prefix.with_suffix('.csv').exists():
                raise ValueError('Unsupported-type control unexpectedly exported results')
        else:
            if row.get('status') != 'PASS_ALIGNMENT_CASE' or row.get('errors') or row.get('macro_thrown') or row.get('ij_error') or row.get('macro_return') == '[aborted]':
                raise ValueError('Runtime/macro error in positive control')
            if row.get('observed_macro_error_dialogs') or row.get('exception_window') or ERROR_PATTERN.search(row.get('log', '')) or row.get('continuation_observed') is not True:
                raise ValueError('Positive case recorded exception/log failure or did not continue')
            if row.get('csv_roundtrip') is not True or row.get('results_visible') is not True:
                raise ValueError('Actual visible Results/export roundtrip absent')
            expected = expected_rows(spec, schedule)
            if row.get('headings') != ['Slice', 'dX', 'dY'] or row.get('rows') != expected:
                raise ValueError('Wrong motion values/columns/row order')
            csv_data = prefix.with_suffix('.csv').read_bytes()
            if digest(csv_data) != row.get('csv_sha256') or csv_rows(csv_data) != expected:
                raise ValueError('Saved CSV differs from actual Results')
            rx, ry = schedule['shifts'][spec['reference'] - 1]
            expected_output = packed([translate(plane, spec['width'], spec['height'], rx - dx, ry - dy)
                                      for plane, (dx, dy) in zip(planes, schedule['shifts'])])
            if out != expected_output:
                raise ValueError('Aligned pixels differ from independently translated fixture: ' + name)
        results[name] = row
    return launcher, report, results


def compare(original, native):
    result = {'schema_version': 1, 'scope': SCOPE, 'whole_calcium_macro_executed': False,
              'status': 'FAIL_OR_INCOMPLETE', 'cases': [], 'errors': []}
    try:
        al, ar, a = load_side(original, 'original'); bl, br, b = load_side(native, 'native')
        if al.get('sources') != bl.get('sources') or not al.get('sources'):
            raise ValueError('Different/missing probe/bootstrap source hashes')
        for name in a:
            fields = ['case', 'input', 'output', 'sentinel_unchanged', 'status', 'continuation_observed']
            if a[name]['case']['expected'] != 'rejected':
                fields += ['headings', 'rows', 'csv_roundtrip', 'results_visible']
            mismatches = [key for key in fields if a[name].get(key) != b[name].get(key)]
            result['cases'].append({'id': name, 'status': 'FAIL' if mismatches else 'PASS_EXACT', 'mismatches': mismatches})
        if any(row['status'] != 'PASS_EXACT' for row in result['cases']):
            raise ValueError('Paired alignment cases differ')
        result['status'] = 'PASS_PAIRED_MACRO_ALIGNMENT_SCOPE'
    except (KeyError, ValueError, TypeError, OSError, struct.error) as error:
        result['errors'].append(str(error))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original', type=Path, required=True); p.add_argument('--native', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error('Existing comparison output is never overwritten')
    result = compare(args.original, args.native)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(result['status'], len(result['cases']), 'paired cases')
    return 0 if result['status'] == 'PASS_PAIRED_MACRO_ALIGNMENT_SCOPE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
