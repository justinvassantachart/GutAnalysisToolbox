#!/usr/bin/env python3
"""Fail closed unless the V2 input method and ganglia/statistics helpers match."""
import argparse
import hashlib
import json
from pathlib import Path

PREP_PATH = 'src/main/java/Features/Core/PluginCalls.java'
HELPERS = ('src/main/java/Features/AnalyseWorkflows/GangliaOps.java',
           'src/main/java/Features/Core/Params.java',
           'src/main/java/Features/Tools/ImageOps.java')


def preparation(source):
    start = source.index('    public static GangliaPrep prepareGangliaInputs(')
    ending = '        return new GangliaPrep(dij, rgb);\n    }'
    finish = source.index(ending, start) + len(ending)
    return source[start:finish].encode('utf-8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def without_mip(source):
    """Exclude only the explicitly tested C/Z/T projection repair, not other helpers."""
    start = source.index('    public static ImagePlus mip(')
    opening = source.index('{', start)
    depth = 1
    at = opening + 1
    while depth:
        if at >= len(source):
            raise ValueError('Unclosed mip method')
        depth += (source[at] == '{') - (source[at] == '}')
        at += 1
    return (source[:start] + source[at:]).encode('utf-8')


def audit(original, control, fork):
    roots = {'original': original, 'control': control, 'fork': fork}
    prep = {key: preparation((root / PREP_PATH).read_text()) for key, root in roots.items()}
    helpers = {}
    for path in HELPERS:
        values = {key: (root / path).read_bytes() for key, root in roots.items()}
        row = {'sha256': {key: digest(value) for key, value in values.items()},
               'all_byte_identical': len(set(values.values())) == 1}
        if path.endswith('/ImageOps.java'):
            remaining = {key: without_mip(value.decode('utf-8')) for key, value in values.items()}
            row['non_projection_code_sha256'] = {key: digest(value) for key, value in remaining.items()}
            row['non_projection_code_byte_identical'] = len(set(remaining.values())) == 1
            row['explicit_difference_scope'] = 'mip only: corrected separate Z projection for every channel/time; tested by ImageProjectionTest'
            row['source_contract_pass'] = row['non_projection_code_byte_identical']
        else:
            row['source_contract_pass'] = row['all_byte_identical']
        helpers[path] = row
    result = {'preparation_method_sha256': {key: digest(value) for key, value in prep.items()},
              'original_corrected_method_byte_identical': prep['original'] == prep['fork'],
              'control_method_differs': prep['original'] != prep['control'],
              'unchanged_helpers': helpers}
    result['status'] = 'PASS' if (result['original_corrected_method_byte_identical']
                                 and result['control_method_differs']
                                 and all(row['source_contract_pass'] for row in helpers.values())) else 'FAIL'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('original', 'control', 'fork', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.original, args.control, args.fork)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print('V2 source contract:', result['status'])
    return 0 if result['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
