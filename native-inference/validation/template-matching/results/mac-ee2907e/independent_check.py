#!/usr/bin/env python3
"""Read-only exact checks against the immutable artifact and legacy reference."""
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent


def main():
    archive = (HERE / 'original-ci-diagnostics.zip').read_bytes()
    assert hashlib.sha256(archive).hexdigest() == '37eff7ef0c97df86cee2f5d3caeedd76e2cd36f5fc3462f6c0119cd1b7c29639'
    reference = (HERE / '../../legacy-reference.json').resolve().read_bytes()
    assert hashlib.sha256(reference).hexdigest() == 'fa5cbcb330667911af446d7e85f84d8bae1eeffed6fea25282946e2612a978fa'
    refs = {case['case']: case for case in json.loads(reference)['cases']}
    with zipfile.ZipFile(io.BytesIO(archive)) as data:
        counts = []
        for name in ('validation-artifacts/template-matching-mac/actual.json',
                     'target/alignment-adapter-mac/adapter.json'):
            cases = json.loads(data.read(name))['cases']
            assert len(cases) == len(refs) and {case['case'] for case in cases} == set(refs)
            for case in cases:
                for field in ('width', 'height', 'frames', 'bits', 'shifts', 'aligned_pixel_sha256'):
                    assert case[field] == refs[case['case']][field], (name, case['case'], field)
            counts.append(sum(case['frames'] for case in cases))
        assert counts == [300, 300]
        rows_checked = 0
        for case in cases:
            name = case['case']
            reference_slice = 3 if name.endswith('ref3') else 2 if name.endswith('ref2') else 71 if name.endswith('ref71') else 1
            text = data.read('target/alignment-adapter-mac/' + name + '_template_matching_alignment.csv').decode()
            rows = list(csv.DictReader(io.StringIO(text)))
            assert len(rows) == case['frames']
            for index, (row, shift) in enumerate(zip(rows, case['shifts']), 1):
                assert row['Algorithm'] == 'TemplateMatching'
                assert int(row['ReferenceSlice']) == reference_slice and int(row['Slice']) == index
                assert [float(row['Dx']), float(row['Dy'])] == shift
                rows_checked += 1
    assert rows_checked == 300
    print('PASS: both six-case/300-frame result sets and all six CSVs/300 rows exactly match the pinned references')


if __name__ == '__main__':
    main()
