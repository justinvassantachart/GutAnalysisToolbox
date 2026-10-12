#!/usr/bin/env python3
"""Independently check the complete paired no-model NMS report; fail closed."""
import argparse
import itertools
import json
from pathlib import Path
import re

PROB = (0, .3, .5, .8, 1)
NMS = (0, .3, .7, 1)
OUTPUTS = ('Both', 'Label Image', 'ROI Manager')
POSITIONS = ('Automatic', 'Stack', 'Hyperstack')
HASH = re.compile(r'^[0-9a-f]{64}$')


def key(row):
    return (*row['shape'][:2], row['input_dimensions'], row['probability'], row['overlap'],
            row['output_type'], row['roi_position'])


def check(report):
    errors = []
    if report.get('schema_version') != 1:
        errors.append('Wrong report schema')
    if report.get('scope') != 'original-nms-vs-adapter-postprocessing-only':
        errors.append('Wrong evidence scope')
    if report.get('model_execution') is not False or report.get('whole_macro_execution') is not False:
        errors.append('This report cannot establish inference or whole-macro parity')
    if report.get('status') != 'PASS_POSTPROCESSING_SCOPE':
        errors.append('Runtime did not reach a passed terminal state')
    for label, name in (('original_class', 'de.csbdresden.stardist.StarDist2DNMS'),
                        ('adapter_class', 'Features.Macros.LegacyMacroStarDist')):
        provenance = report.get(label, {})
        if provenance.get('name') != name or not provenance.get('code_source') or not HASH.fullmatch(provenance.get('class_sha256', '')):
            errors.append('Missing real implementation provenance: ' + label)
    expected = {(w, h, d, p, n, o, r) for (w, h), d, p, n, o, r in itertools.product(
        ((33, 29), (32, 30)), (2, 4), PROB, NMS, OUTPUTS, POSITIONS)}
    seen = set()
    for row in report.get('cases', []):
        try:
            case = key(row)
            if case not in expected or case in seen:
                errors.append('Unknown or duplicate case: ' + str(case))
            seen.add(case)
            if row.get('fixture') != 'deterministic-synthetic-8-ray-peaks-v1' or row['shape'][2] != 9:
                errors.append('Unrecognized synthetic tensor')
            if not all(HASH.fullmatch(row.get(k, '')) for k in ('probability_sha256', 'distance_sha256')):
                errors.append('Missing fixture hashes')
            if any(row.get(k) is not True for k in ('pass', 'inputs_unchanged', 'auxiliary_pixels_match')):
                errors.append('Failed pair: ' + str(case))
            original, adapter = row['original'], row['adapter']
            if original != adapter:
                errors.append('Paired output differs: ' + str(case))
            for result in (original, adapter):
                has_label = row['output_type'] != 'ROI Manager'
                if result.get('label_present') is not has_label:
                    errors.append('Wrong output selection: ' + str(case))
                if has_label:
                    for field in ('label_shape', 'label_axes', 'label_dtype', 'label_name', 'label_pixels_sha256'):
                        if field not in result:
                            errors.append('Missing label evidence: ' + field)
                    if not HASH.fullmatch(result.get('label_pixels_sha256', '')):
                        errors.append('Missing pixel hash')
                rois = result['rois_in_manager_order']
                if len(rois) != result.get('roi_count_including_existing_sentinel'):
                    errors.append('ROI list/count disagreement')
                # Actual original NMS clears the global ROI Manager for ROI
                # outputs; Label Image alone leaves it untouched. Preserve that
                # observed legacy behavior rather than invent append semantics.
                if row['output_type'] != 'Label Image' and any(r[0] == 'existing-roi-sentinel' for r in rois):
                    errors.append('ROI output did not replace existing manager contents')
                if row['probability'] == .5 and row['output_type'] != 'Label Image' and not rois:
                    errors.append('Vacuous all-empty default segmentation')
                if row['output_type'] == 'Label Image' and (len(rois) != 1 or rois[0][0] != 'existing-roi-sentinel'):
                    errors.append('Label-only changed ROI Manager')
        except (KeyError, TypeError, IndexError) as error:
            errors.append('Malformed case: ' + str(error))
    if seen != expected or report.get('case_count') != len(expected):
        errors.append('Incomplete grid: %d/%d distinct cases' % (len(seen & expected), len(expected)))
    return {'scope': 'original-nms-vs-adapter-postprocessing-only', 'model_execution': False,
            'whole_macro_execution': False, 'status': 'PASS_POSTPROCESSING_SCOPE' if not errors else 'FAIL_EVIDENCE',
            'expected_cases': len(expected), 'observed_cases': len(seen), 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = check(json.loads(args.report.read_text()))
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'], str(result['observed_cases']) + '/' + str(result['expected_cases']))
    return 0 if result['status'] == 'PASS_POSTPROCESSING_SCOPE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
