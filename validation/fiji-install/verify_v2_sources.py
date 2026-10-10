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


def audit(original, control, fork):
    roots = {'original': original, 'control': control, 'fork': fork}
    prep = {key: preparation((root / PREP_PATH).read_text()) for key, root in roots.items()}
    helpers = {}
    for path in HELPERS:
        values = {key: (root / path).read_bytes() for key, root in roots.items()}
        helpers[path] = {'sha256': {key: digest(value) for key, value in values.items()},
                         'all_byte_identical': len(set(values.values())) == 1}
    result = {'preparation_method_sha256': {key: digest(value) for key, value in prep.items()},
              'original_corrected_method_byte_identical': prep['original'] == prep['fork'],
              'control_method_differs': prep['original'] != prep['control'],
              'unchanged_helpers': helpers}
    result['status'] = 'PASS' if (result['original_corrected_method_byte_identical']
                                 and result['control_method_differs']
                                 and all(row['all_byte_identical'] for row in helpers.values())) else 'FAIL'
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
