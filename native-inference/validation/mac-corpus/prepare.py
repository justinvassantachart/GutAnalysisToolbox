#!/usr/bin/env python3
"""Prepare hash-pinned public test inputs, references and models, without inference."""
import argparse
from array import array
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
CORPUS = ROOT.parent / 'corpus' / 'results'


def digest(path):
    hasher = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify(path, expected):
    if digest(path) != expected:
        raise ValueError(f'SHA-256 mismatch: {Path(path).name}')


def save(path, data):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w') as stream:
        stream.write(json.dumps(data, indent=2, allow_nan=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def load_manifest():
    manifest = json.loads((ROOT / 'frozen-manifest.json').read_text())
    cases = manifest['cases']
    ids = [c['case_id'] for c in cases]
    if (manifest['schema'] != 1 or len(cases) != 40 or len(set(ids)) != 40 or
            len({c['input_sha256'] for c in cases}) != 39 or
            sum(bool(c['same_train_input_case_ids']) for c in cases) != 1 or
            any(c['split'] != 'test' or c['model'] not in ('neuron', 'subtype') for c in cases)):
        raise ValueError('Unexpected corpus membership/independence metadata')
    for case in cases:
        width, height = case['width'], case['height']
        if (not 1 <= width * height <= 1_861_256 or case['channels'] != 97 or
                case['input_bytes'] != 16 + width * height * 4 or
                case['tiles']['requested_tiles'] != 4 or case['nms_threshold'] != 0.3 or
                case['excluded_boundary'] != 2 or
                case['probability_threshold'] != (0.5 if case['model'] == 'neuron' else 0.4)):
            raise ValueError(f'Unexpected fixed dimensions/settings: {case["case_id"]}')
    return manifest


def verify_references(manifest):
    for relative, expected in manifest['reference_files'].items():
        verify(CORPUS / relative, expected)


def fetch(path, url, sha256, limit, enabled):
    path = Path(path)
    if not path.exists():
        if not enabled:
            raise FileNotFoundError(f'Missing {path.name}; provide it or use --download for pinned public files')
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + '.download')
        total = 0
        try:
            with urllib.request.urlopen(url, timeout=120) as response, temporary.open('wb') as output:
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > limit:
                        raise ValueError(f'Download exceeds fixed size bound: {path.name}')
                    output.write(chunk)
            verify(temporary, sha256)
            temporary.replace(path)
        finally:
            if temporary.exists():
                temporary.unlink()
    verify(path, sha256)


def convert_case(case, archive, destination):
    from PIL import Image
    source = case['source']
    raw = archive.read(source['source_path'])
    if hashlib.sha256(raw).hexdigest() != source['source_sha256']:
        raise ValueError(f'Source image hash mismatch: {case["case_id"]}')
    with Image.open(io.BytesIO(raw)) as image:
        if image.n_frames != 1 or image.size != (case['width'], case['height']):
            raise ValueError('Unexpected TIFF plane count or dimensions')
        expected_modes = ('L', 'P') if source['dtype'] == 'uint8' else ('I;16B',)
        if image.mode not in expected_modes:
            raise ValueError(f'Unexpected TIFF scalar type: {image.mode}, expected {expected_modes}')
        # uint8/uint16 fit exactly in binary32; no contrast, resize or normalization.
        values = array('f', image.getdata())
    if values.itemsize != 4:
        raise ValueError('Host float array does not use binary32')
    if sys.byteorder == 'little':
        values.byteswap()
    binary = struct.pack('>4i', 0x47415449, 1, case['width'], case['height']) + values.tobytes()
    if len(binary) != case['input_bytes'] or hashlib.sha256(binary).hexdigest() != case['input_sha256']:
        raise ValueError(f'Converted input differs from archived exact pixels: {case["case_id"]}')
    destination.write_bytes(binary)


def materialize_reference(case, destination, records):
    reference = case['legacy_outline']
    with zipfile.ZipFile(CORPUS / reference['archive']) as archive:
        raw = archive.read(reference['member'])
    if hashlib.sha256(raw).hexdigest() != reference['sha256']:
        raise ValueError(f'Legacy polygon hash mismatch: {case["case_id"]}')
    (destination / (case['case_id'] + '.legacy.polygons.gz')).write_bytes(raw)
    details = records[case['case_id']]['metrics'].get('legacy_object_measurements', [])
    if bool(details) != case['legacy_order_available']:
        raise ValueError('Archived paint-order availability changed')
    if details:
        count = case['legacy_expected']['legacy_count']
        labels = {r['label_id'] for r in details}
        centers = {(r['winning_center_x_px'], r['winning_center_y_px']) for r in details}
        if len(details) != count or labels != set(range(1, count + 1)) or len(centers) != count:
            raise ValueError('Incomplete or duplicate archived paint order')
        (destination / (case['case_id'] + '.legacy-order.tsv')).write_text(''.join(
            f'{r["winning_center_x_px"]}\t{r["winning_center_y_px"]}\t{r["label_id"]}\n' for r in details))


def prepare(archives, models, output, download=False):
    manifest = load_manifest()
    verify_references(manifest)
    output.mkdir(parents=True, exist_ok=True)
    inputs, refs = output / 'inputs', output / 'references'
    inputs.mkdir(exist_ok=True)
    refs.mkdir(exist_ok=True)
    records = {r['case_id']: r for r in json.loads((CORPUS / 'core/cases.json').read_text())}
    for model in manifest['models'].values():
        fetch(models / model['filename'], model['url'], model['sha256'], 50_000_000, download)
    prepared = []
    for name, source in manifest['archives'].items():
        archive_path = archives / name
        fetch(archive_path, source['url'], source['sha256'], source['bytes'], download)
        if archive_path.stat().st_size != source['bytes']:
            raise ValueError('Archive size mismatch')
        with zipfile.ZipFile(archive_path) as archive:
            for case in manifest['cases']:
                if case['source']['source_archive'] != name:
                    continue
                destination = inputs / (case['case_id'] + '.gati')
                convert_case(case, archive, destination)
                materialize_reference(case, refs, records)
                prepared.append(case['case_id'])
    import PIL
    report = dict(status='prepared_without_inference', case_count=len(prepared),
                  unique_input_count=39, train_overlap_count=1, case_ids=prepared,
                  frozen_manifest_sha256=digest(ROOT / 'frozen-manifest.json'),
                  pillow_version=PIL.__version__, python_version=sys.version.split()[0],
                  reference_files_verified=manifest['reference_files'],
                  model_sha256={k: v['sha256'] for k, v in manifest['models'].items()},
                  source_archives={k: v['sha256'] for k, v in manifest['archives'].items()},
                  pixel_conversion=manifest['conversion'])
    save(output / 'preparation.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archives', type=Path, required=True)
    parser.add_argument('--models', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--download', action='store_true', help='Fetch only immutable public URLs pinned by SHA-256')
    args = parser.parse_args()
    report = prepare(args.archives, args.models, args.output, args.download)
    print(json.dumps({k: report[k] for k in ('status', 'case_count', 'unique_input_count', 'train_overlap_count')}))


if __name__ == '__main__':
    main()
