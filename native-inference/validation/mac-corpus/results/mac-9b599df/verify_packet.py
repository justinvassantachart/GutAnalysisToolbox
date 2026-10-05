#!/usr/bin/env python3
"""Read-only verification of this frozen native-corpus evidence packet."""
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
import statistics
import zipfile

ROOT = Path(__file__).resolve().parent
SHA = '678f2f005f2975e8269cdb16d8eb853de05efc401f0d3aada8472f500808d95d'
PREFIX = 'target/mac-corpus-results/'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    files = {}
    for line in (ROOT / 'SHA256SUMS').read_text().splitlines():
        expected, relative = line.split('  ', 1)
        assert relative not in files and '..' not in PurePosixPath(relative).parts
        files[relative] = expected
        assert digest((ROOT / relative).read_bytes()) == expected, relative
    present = {str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file()
               and p.name != 'SHA256SUMS' and '__pycache__' not in p.parts}
    assert set(files) == present, 'Unlisted or missing packet files'
    original = ROOT / 'original'
    zpath = original / 'gat-native-mac-official40-corpus.zip'
    assert zpath.stat().st_size == 6171926 and digest(zpath.read_bytes()) == SHA
    members = json.loads((original / 'zip-member-manifest.json').read_text())
    s = json.loads((original / 'summary.json').read_text())
    p = json.loads((ROOT / 'summary.json').read_text())
    f = json.loads((original / 'frozen-manifest.json').read_text())
    source = json.loads((original / 'github-source.json').read_text())
    assert source['source_commit'] == s['metadata']['checkout_commit'] == p['source_commit']
    assert source['run_id'] == 37381573321 and source['job_id'] == 112004603172
    assert s['run_completed'] and s['native_all40_completed'] and not s['scientific_equivalence_established']
    assert not p['scientific_equivalence_established'] and not p['tensor_numerical_parity_performed']
    assert len(s['cases']) == len(p['cases']) == len(f['cases']) == 40
    assert len({c['metadata']['input_sha256'] for c in s['cases']}) == 39
    assert sum(bool(c['metadata']['same_train_input_case_ids']) for c in s['cases']) == 1
    assert {c['case_id'] for c in s['cases']} == {c['case_id'] for c in f['cases']}
    assert digest((original / 'frozen-manifest.json').read_bytes()) == s['metadata']['frozen_manifest_sha256']
    assert digest((original / 'dependencies.json').read_bytes()) == s['metadata']['dependencies_manifest_sha256']
    with zipfile.ZipFile(zpath) as z:
        assert z.testzip() is None and len(z.namelist()) == len(set(z.namelist())) == 413
        assert {r['path'] for r in members['members']} == set(z.namelist())
        for row in members['members']:
            path = PurePosixPath(row['path'])
            assert not path.is_absolute() and '..' not in path.parts
            raw = z.read(row['path'])
            assert len(raw) == row['bytes'] and digest(raw) == row['sha256']
        for name in ('summary.json', 'artifact-manifest.json'):
            assert (original / name).read_bytes() == z.read(PREFIX + name)
        assert (original / 'preparation.json').read_bytes() == z.read('target/mac-corpus-prepared/preparation.json')
        for name in ('case.json', 'actual.geometry.json', 'outliers.json'):
            assert (original / ('outlier-' + name)).read_bytes() == z.read(PREFIX+'neuron_test_widefield_9/'+name)
        manifest = json.loads((original / 'artifact-manifest.json').read_text())
        assert len(manifest) == 404
        for relative, expected in manifest.items():
            assert digest(z.read(PREFIX+relative)) == expected
        for case, row in zip(s['cases'], p['cases']):
            name = case['case_id']
            assert name == row['case_id'] and case['status'] == 'compared'
            assert json.loads(z.read(PREFIX+name+'/case.json')) == case
            for filename, expected in case['artifacts_sha256'].items():
                assert digest(z.read(PREFIX+name+'/'+filename)) == expected
            geometry = json.loads(z.read(row['geometry_member']))
            assert geometry['modern_count'] == row['objects_mac'] == row['objects_legacy']
            assert case['cold_worker_process_end_to_end_seconds'] == row['cold_cpu_worker_seconds']
            assert case['geometry_process_end_to_end_seconds'] == row['geometry_subprocess_seconds']
            assert case['comparison']['original_exclusive_label_difference_count'] == row['original_exclusive_canonical_changed_pixels']
    audit = json.loads((ROOT / 'independent/independent-audit.json').read_text())
    assert audit['status'] == 'passed' and audit['self_tests_passed'] == 7
    assert audit['counts']['case_count'] == 40 and audit['counts']['object_count'] == 4472
    assert audit['artifact_zip_sha256'] == SHA
    assert audit['audit_script_sha256'] == digest((ROOT / 'independent/audit_native_corpus.py').read_bytes())
    assert p['independent_audit']['report_sha256'] == digest((ROOT / 'independent/independent-audit.json').read_bytes())
    rows = p['cases']
    assert sum(r['objects_mac'] for r in rows) == sum(r['objects_legacy'] for r in rows) == 4472
    assert sum(r['canonical_raster_hash_equal'] and r['canonical_measurement_hash_equal'] for r in rows) == 39
    assert sum(r['raw_label_hash_equal'] for r in rows) == 37
    assert sum(r['strict_quantized_outlines_equal'] for r in rows) == 8
    assert all(r['winner_centers_equal'] and r['count_equal'] for r in rows)
    assert sum(r['changed_outline_objects'] for r in rows) == 162
    assert sum(r['changed_outline_vertices'] for r in rows) == 164
    outlier = next(r for r in rows if r['case_id'] == 'neuron_test_widefield_9')
    assert outlier['original_exclusive_canonical_changed_pixels'] is None
    assert not outlier['original_exclusive_changed_count_available']
    assert outlier['foreground_union_changed_pixels'] == 1
    assert outlier['min_matched_independent_polygon_iou'] == 690 / 691
    times = [r['cold_cpu_worker_seconds'] for r in rows]
    for name, actual in [('min', min(times)), ('max', max(times)), ('median', statistics.median(times)), ('sum', sum(times))]:
        assert p['timing_seconds']['cold_cpu_worker_'+name] == actual
    assert p['timing_seconds']['geometry_subprocess_sum'] == sum(r['geometry_subprocess_seconds'] for r in rows)
    assert p['timing_seconds']['runner_total'] == s['metadata']['total_wall_seconds']
    with (ROOT / 'cases.csv').open(newline='') as stream:
        csv_rows = list(csv.DictReader(stream))
    assert len(csv_rows) == 40
    for expected, actual in zip(rows, csv_rows):
        assert set(expected) == set(actual)
        for key, value in expected.items():
            if value is None:
                assert actual[key] == '', key
            elif isinstance(value, bool):
                assert actual[key] == str(value).lower(), key
            elif isinstance(value, (int, float)):
                assert float(actual[key]) == value, key
            else:
                assert actual[key] == value, key
    print('VERIFIED: original ZIP413 members,404 compact hashes,40 exact case rows and CSV, all count/hash/timing claims; one qualified raster outlier retained')


if __name__ == '__main__':
    main()
