#!/usr/bin/env python3
"""Authoring utility: freeze ONLY the existing official 40 test-labeled references.

This does not execute any model. Review changes to the frozen manifest explicitly;
normal preparation/runs never regenerate this manifest or the legacy references.
"""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CORPUS = ROOT.parent / 'corpus' / 'results'


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(data)
    return result.hexdigest()


def tile_plan(width, height):
    def size(dimension, tiles):
        return ((dimension // tiles + 63) // 64) * 64
    nx = ny = 1
    while nx * ny < 4:
        sx, sy = size(width, nx), size(height, ny)
        if sx > 64 and sx >= sy:
            nx += 1
        elif sy > 64:
            ny += 1
        else:
            break
    tw, th = size(width, nx), size(height, ny)
    ox, oy = (64 if nx > 1 else 0), (64 if ny > 1 else 0)
    return dict(requested_tiles=4, tiles_x=nx, tiles_y=ny,
                actual_tiles=nx * ny, core_width=tw, core_height=th,
                overlap_x=ox, overlap_y=oy, input_tile_width=tw + 2 * ox,
                input_tile_height=th + 2 * oy, expanded_width=tw * nx,
                expanded_height=th * ny, block_size=64,
                edge_extension='unchanged CSBDeep nested MirrorDouble')


def build():
    with (CORPUS / 'core/manifest.tsv').open() as stream:
        rows = list(csv.DictReader(stream, delimiter='\t'))
    records = {r['case_id']: r for r in json.loads((CORPUS / 'core/cases.json').read_text())}
    provenance = json.loads((CORPUS / 'core/provenance.json').read_text())
    tests = [row for row in rows if row['split'] == 'test']
    assert len(tests) == 40 and len({r['input_sha256'] for r in tests}) == 39
    source_names = {'neuron.zip': '2D_enteric_neuron_Hu_train_test.zip',
                    'subtype.zip': '2D_neuronal_subtype_train_test_data.zip'}
    archives = {}
    for name, record in provenance['archives'].items():
        archives[name] = {**record, 'published_filename': source_names[name],
                         'url': f'https://zenodo.org/records/15314214/files/{source_names[name]}?download=1'}
    cases = []
    stains = {'Calb': 'Calbindin', 'CalR': 'Calretinin', 'Chat': 'ChAT',
              'NFM': 'Neurofilament', 'NOS': 'nNOS'}
    for row in tests:
        ref = records[row['case_id']]
        assert ref['status'] == 'compared' and ref['metadata'] == row
        width, height = int(row['width']), int(row['height'])
        outline = next(a for a in ref['polygon_artifacts'] if a['path'].endswith('-legacy.polygons.gz'))
        stain = 'Hu' if row['model'] == 'neuron' else stains[Path(row['source_path']).stem.split('_')[1]]
        source = {k: row[k] for k in ('source_path', 'source_archive', 'source_sha256', 'dtype', 'minimum', 'maximum', 'mean')}
        expected = {k: v for k, v in ref['metrics'].items()
                    if k in ('legacy_count', 'legacy_candidates', 'legacy_visible_labels', 'legacy_tensor_sha256',
                             'legacy_label_sha256', 'legacy_canonical_sha256', 'legacy_measurements_sha256')}
        cases.append(dict(case_id=row['case_id'], model=row['model'], split='test', stain=stain,
                          source=source, input_sha256=row['input_sha256'], input_bytes=16 + width * height * 4,
                          width=width, height=height, channels=97,
                          crop=dict(x=0, y=0, width=width, height=height, source_width=width, source_height=height,
                                    policy='entire supplied 2D image; no crop or resize'),
                          tiles=tile_plan(width, height), probability_threshold=0.5 if row['model'] == 'neuron' else 0.4,
                          nms_threshold=0.3, excluded_boundary=2, legacy_expected=expected,
                          legacy_outline=dict(archive=Path(outline['archive']).name, member=outline['archive_entry'], sha256=outline['sha256']),
                          legacy_order_available=bool(ref['metrics'].get('legacy_object_measurements')),
                          archived_legacy_raw_tensor_retained_at_original_run=ref['raw_tensors_retained'],
                          same_test_input_case_ids=[r['case_id'] for r in tests if r['case_id'] != row['case_id'] and r['input_sha256'] == row['input_sha256']],
                          same_train_input_case_ids=[r['case_id'] for r in rows if r['split'] == 'train' and r['input_sha256'] == row['input_sha256']]))
    models = {}
    for model, name in (('neuron', '2D_enteric_neuron_v4_1.zip'), ('subtype', '2D_enteric_neuron_subtype_v4.zip')):
        models[model] = dict(filename=name, sha256=provenance['model_hashes'][name],
                            url=f'https://raw.githubusercontent.com/pr4deepr/GutAnalysisToolbox/61d57c4e4bcfe82aa0369100c0a3b0739b70affa/Models/{name}')
    source_files = ['core/cases.json', 'core/manifest.tsv', 'core/provenance.json', 'outline-sha256.json',
                    *sorted({c['legacy_outline']['archive'] for c in cases})]
    payload = dict(schema=1, source_record='https://zenodo.org/records/15314214', source_version='v4',
                   case_count=40, unique_input_count=39, input_pixels=sum(c['width'] * c['height'] for c in cases),
                   test_cases_with_train_overlap=1,
                   independence_note='40 source-labeled test files; 39 unique inputs; one unique test input also occurs in training. Not 40 independent held-out samples.',
                   stains=dict(Counter(c['stain'] for c in cases)), models=models, archives=archives,
                   legacy_runtime=provenance['legacy_runtime'], legacy_platform=provenance['test_platform'],
                   raw_legacy_tensor_comparison_performed=False,
                   reference_limitation='Most full TF1 probability/distance tensors and label arrays were not retained. Original raster and measurement hashes plus all legacy polygons are retained; no tensor tolerance claim is possible for all40.',
                   reference_files={p: digest(CORPUS / p) for p in source_files},
                   normalization='Unchanged production CSBDeep 1/99.8 nearest-index percentile; float32 arithmetic; lower-only clamp; no upper clamp. See CsbdeepNormalizer.java.',
                   conversion='Pillow decodes one unsigned 8/16-bit scalar TIFF plane; preserve numerical pixels (palette TIFFs retain scalar palette indices, as in the original NumPy conversion); cast exactly to big-endian float32 row-major GATI v1; no color, intensity, size, or axis transformation.',
                   cases=cases)
    return payload


if __name__ == '__main__':
    (ROOT / 'frozen-manifest.json').write_text(json.dumps(build(), indent=2, allow_nan=False) + '\n')
