#!/usr/bin/env python3
"""Compare executed original/native macro-command cases, never promote scope.

Label pixels, label IDs/areas and metadata are exact gates. ROI vertices are exact
by default; a nonzero explicit --roi-atol is disclosed in the result. It cannot
weaken count, ordering, naming, placement, raster or settings comparisons.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load_side(directory, variant):
    summary = json.loads((directory / 'summary.json').read_text())
    if summary.get('status') != 'PASS_SELECTED_CASES' or summary.get('variant') != variant:
        raise ValueError(variant + ' run is not complete/passed')
    if summary.get('scope') != 'registered-legacy-macro-inference-boundary' or summary.get('whole_analysis_macro_executed') is not False:
        raise ValueError('Invalid or inflated evidence scope')
    selected = summary['selected_cases']
    if not selected or len(selected) != len(set(selected)):
        raise ValueError('Empty/duplicate selected case set')
    matrix = json.loads((HERE / 'coverage-matrix.json').read_text())['layers']['inference']['cases']
    specifications = {r['id']: {k: v for k, v in r.items() if k != 'status'} for r in matrix}
    fixtures = json.loads((ROOT / 'native-inference/validation/cross-platform/fixture-manifest.json').read_text())
    model_sha = {'neuron': fixtures['cases'][0]['model_sha256'], 'subtype': fixtures['cases'][1]['model_sha256']}
    result = {}
    for case in summary.get('cases', []):
        name = case['id']
        if name in result or name not in selected or name not in specifications:
            raise ValueError('Unknown/duplicate/unrequested case: ' + name)
        if case.get('status') != 'PASS_MACRO_INFERENCE_CASE' or case['execution'].get('exit_code') != 0 or case['execution'].get('resource_stop_reason'):
            raise ValueError('Unsuccessful process: ' + name)
        path = (directory / case['report']).resolve()
        if not path.is_relative_to(directory.resolve()):
            raise ValueError('Report escapes scoped evidence directory')
        report = json.loads(path.read_text())
        if report.get('schema_version') != 1 or report.get('status') != 'PASS_MACRO_INFERENCE_CASE' or report.get('variant') != variant:
            raise ValueError('Wrong per-case terminal status/variant')
        if report.get('scope') != summary['scope'] or report.get('whole_analysis_macro_executed') is not False:
            raise ValueError('Wrong per-case scope')
        if report.get('case') != specifications[name]:
            raise ValueError('Actual settings differ from pinned case schedule: ' + name)
        if report.get('fixture_sha256') != fixtures['source']['sha256'] or report.get('model_sha256') != model_sha[report['case']['model']]:
            raise ValueError('Unpinned/nonpublic fixture or wrong model: ' + name)
        if report.get('matching_module_executions') != 1 or 'Command From Macro' not in report.get('dispatched_commands', []):
            raise ValueError('Actual registered macro-command execution not established')
        for key in ('input_unchanged', 'unrelated_image_unchanged', 'label_display_verified', 'auxiliary_outputs_absent'):
            if report.get(key) is not True:
                raise ValueError('Missing/failed output assertion: ' + key)
        target = 'Features.Macros.LegacyMacroStarDist' if variant == 'native' else 'de.csbdresden.stardist.StarDist2D'
        if report.get('target_class', {}).get('name') != target or report.get('command_bridge_class', {}).get('name') != 'de.csbdresden.CommandFromMacro':
            raise ValueError('Wrong production/bridge class')
        if variant == 'native':
            if report.get('backend_property') != 'gat.stardist.backend' or report.get('backend_value') != 'native' or len(report.get('worker_processes', {})) != 1:
                raise ValueError('Actual native worker execution not established; fallback is insufficient')
        elif report.get('worker_processes'):
            raise ValueError('Original control used fork worker')
        data = (path.parent / 'labels.f32be').read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        label = report['label']
        if digest != label['pixels_f32be_sha256'] or digest != report['label_pixels_f32be_sha256']:
            raise ValueError('Saved label raster hash differs from report')
        if len(data) != 4 * math.prod(label['shape']):
            raise ValueError('Incomplete/oversized label raster')
        areas = {}
        for (value,) in struct.iter_unpack('>f', data):
            if not math.isfinite(value) or value < 0 or value != int(value):
                raise ValueError('Invalid label value')
            if value:
                key = str(int(value)); areas[key] = areas.get(key, 0) + 1
        if areas != label['areas_by_label_id'] or len(areas) != label['object_count']:
            raise ValueError('Independent label areas/counts disagree')
        if report.get('errors'):
            raise ValueError('Recorded runtime error')
        result[name] = report
    if set(result) != set(selected):
        raise ValueError('Incomplete selected cases')
    return summary, result


def roi_delta(original, native):
    if len(original) != len(native):
        return None
    maximum = 0.0
    for a, b in zip(original, native):
        if len(a) != 7 or len(b) != 7 or a[:6] != b[:6] or len(a[6]) != len(b[6]):
            return None
        for x, y in zip(a[6], b[6]):
            if len(x) != 2 or len(y) != 2:
                return None
            for m, n in zip(x, y):
                if not math.isfinite(m) or not math.isfinite(n):
                    return None
                maximum = max(maximum, abs(m - n))
    return maximum


def raster_differences(original, native):
    a = [v[0] for v in struct.iter_unpack('>f', original)]
    b = [v[0] for v in struct.iter_unpack('>f', native)]
    if len(a) != len(b):
        return {'same_pixel_count': False, 'original_pixels': len(a), 'native_pixels': len(b)}
    changed = sum(x != y for x, y in zip(a, b))
    foreground = sum((x != 0) != (y != 0) for x, y in zip(a, b))
    intersection = sum(x != 0 and y != 0 for x, y in zip(a, b))
    union = sum(x != 0 or y != 0 for x, y in zip(a, b))
    return {'same_pixel_count': True, 'pixels': len(a), 'different_label_pixels': changed,
            'different_label_pixel_fraction': changed / len(a) if a else 0,
            'different_foreground_pixels': foreground, 'foreground_intersection_over_union': intersection / union if union else 1.0}


def compare(original, native, roi_atol=0.0):
    result = {'schema_version': 1, 'scope': 'registered-legacy-macro-inference-boundary',
              'whole_analysis_macro_executed': False, 'roi_vertex_atol_pixels': roi_atol,
              'roi_tolerance_comparison_slack_pixels': 1e-12 if roi_atol > 0 else 0.0,
              'status': 'FAIL_OR_INCOMPLETE', 'cases': [], 'errors': []}
    try:
        if not math.isfinite(roi_atol) or roi_atol < 0:
            raise ValueError('ROI tolerance must be finite and nonnegative')
        source_summary, source = load_side(original, 'original')
        fork_summary, fork = load_side(native, 'native')
        if set(source) != set(fork):
            raise ValueError('Original/native selected case sets differ')
        if source_summary['macro_source'] != fork_summary['macro_source']:
            raise ValueError('Different original macro revision/blobs')
        for name in sorted(source):
            a, b = source[name], fork[name]
            mismatches = []
            for field in ('case', 'fixture_sha256', 'model_sha256', 'prepared_input', 'label', 'new_image_windows'):
                if a[field] != b[field]:
                    mismatches.append(field)
            delta = roi_delta(a['roi_manager'], b['roi_manager'])
            # A serialized decimal difference such as 64.70 - 64.69 can be
            # 0.010000000000005116 in binary floating point. This allowance is
            # solely for an explicitly positive tolerance; exact mode stays
            # exactly zero. It is many orders below a float ROI coordinate.
            within_roi_tolerance = delta is not None and (delta <= roi_atol or
                (roi_atol > 0 and math.isclose(delta, roi_atol, rel_tol=0.0, abs_tol=1e-12)))
            if not within_roi_tolerance:
                mismatches.append('roi_geometry_order_names_positions')
            row = {'id': name, 'status': 'PASS_EXACT' if not mismatches and delta == 0 else
                   'PASS_EXPLICIT_ROI_TOLERANCE' if not mismatches else 'FAIL', 'mismatches': mismatches,
                   'roi_max_vertex_absolute_difference_pixels': delta,
                   'original_objects': a['label']['object_count'], 'native_objects': b['label']['object_count'],
                   'labels_exact': a['label']['pixels_f32be_sha256'] == b['label']['pixels_f32be_sha256']}
            source_path = original / next(c['report'] for c in source_summary['cases'] if c['id'] == name)
            fork_path = native / next(c['report'] for c in fork_summary['cases'] if c['id'] == name)
            row['label_differences'] = raster_differences((source_path.parent / 'labels.f32be').read_bytes(),
                                                        (fork_path.parent / 'labels.f32be').read_bytes())
            area_a, area_b = a['label']['areas_by_label_id'], b['label']['areas_by_label_id']
            row['area_delta_pixels_by_label_id'] = {key: area_b.get(key, 0) - area_a.get(key, 0)
                for key in sorted(set(area_a) | set(area_b), key=int) if area_b.get(key, 0) != area_a.get(key, 0)}
            result['cases'].append(row)
        if not any(row['original_objects'] > 0 for row in result['cases']):
            raise ValueError('All selected original controls are empty; no positive segmentation control established')
        if any(row['status'] == 'FAIL' for row in result['cases']):
            result['errors'].append('At least one paired actual inference case differs')
        if not result['errors']:
            result['status'] = 'PASS_PAIRED_MACRO_INFERENCE_SCOPE'
    except (KeyError, ValueError, TypeError, OSError) as error:
        result['errors'].append(str(error))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--roi-atol', type=float, default=0.0)
    args = parser.parse_args()
    result = compare(args.original, args.native, args.roi_atol)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(result['status'], len(result['cases']), 'paired cases')
    return 0 if result['status'] == 'PASS_PAIRED_MACRO_INFERENCE_SCOPE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
