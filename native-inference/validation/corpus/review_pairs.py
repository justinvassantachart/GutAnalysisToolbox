#!/usr/bin/env python3
"""Compare one ready prediction pair at a time; persist metrics before releasing producer."""
import argparse, csv, hashlib, json, os
from pathlib import Path
import shutil, subprocess, time, traceback
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root', type=Path, required=True, help='Corpus directory with manifest.tsv and outputs/<case>/.ready')
parser.add_argument('--classpath', required=True, help='Compiled comparator plus pinned StarDist/ImageJ/ImgLib2 dependencies')
parser.add_argument('--java', default='java')
parser.add_argument('--max-heap', default='3g')
parser.add_argument('--case-timeout', type=int, default=1800)
parser.add_argument('--remove-matching-tensors', action='store_true', help='After durable metrics, remove fully matching raw prediction pairs; mismatches always remain')
args = parser.parse_args()
ROOT = args.root.resolve()
OUTPUTS = ROOT / 'outputs'
REVIEW = ROOT / 'review'
RESULTS = REVIEW / 'results'
RESULTS.mkdir(parents=True, exist_ok=True)
JAVA = args.java
CP = args.classpath
NMS = '0.3'
def save(path, obj):
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w') as f:
        json.dump(obj, f, indent=2, allow_nan=False)
        f.write('\n'); f.flush(); os.fsync(f.fileno())
    temporary.replace(path)
    fd = os.open(str(path.parent), os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)
def manifest():
    for name in ('manifest.tsv', 'cases.tsv'):
        file = ROOT / name
        if file.exists():
            with file.open() as f:
                rows = list(csv.DictReader(f, delimiter='\t'))
            return {row.get('case_id', row.get('id')): row for row in rows}
    return {}
def handle(directory, records):
    case = directory.name
    modern, legacy = directory / 'modern.bin', directory / 'legacy.bin'
    if not modern.is_file() or not legacy.is_file():
        return False
    meta = records.get(case, {})
    for filename in ('case.json', 'metadata.json'):
        if (directory / filename).is_file():
            meta = {**meta, **json.loads((directory / filename).read_text())}
    result_path = RESULTS / (case + '.json')
    print('START', case, flush=True)
    start = time.monotonic()
    probability = '0.4' if meta.get('model') == 'subtype' else '0.5'
    try:
        run = subprocess.run([JAVA, '-XX:-UsePerfData', '-Xmx' + args.max_heap, '-Djava.awt.headless=true', '-cp', CP,
                              'CorpusNmsComparison', str(modern), str(legacy), probability, NMS, str(REVIEW / 'outlines' / case)],
                             capture_output=True, text=True, timeout=args.case_timeout)
        if run.returncode:
            raise RuntimeError(f'Comparator exit {run.returncode}: {run.stderr[-8000:]} {run.stdout[-1000:]}')
        json_lines = [line for line in run.stdout.splitlines() if line.startswith('{')]
        if len(json_lines) != 1:
            raise ValueError('Expected one JSON result; stdout tail: ' + run.stdout[-1000:])
        metrics = json.loads(json_lines[0])
        exact = (metrics['different_label_pixels'] == 0
                 and metrics['modern_count'] == metrics['legacy_count']
                 and metrics['pixel_measurements_equal']
                 and metrics['winner_centers_equal'])
        remove_raw = (args.remove_matching_tensors and exact and metrics['outside_atol_1e4_rtol_1e4'] == 0
                      and metrics['probability_threshold_flips'] == 0)
        outcome = {'case_id': case, 'metadata': meta, 'status': 'compared',
                   'comparison_seconds': time.monotonic() - start,
                   'comparator_source_sha256': hashlib.sha256(Path(__file__).with_name('CorpusNmsComparison.java').read_bytes()).hexdigest(),
                   'upstream_stardist_commit': 'aff59dbd3cdf88dfa567d4dd562eab943bf4f99b',
                   'exact_segmentation_match': exact,
                   'exact_label_raster_match': exact,
                   'polygon_artifacts': [str(REVIEW / 'outlines' / (case + '-modern.polygons.gz')), str(REVIEW / 'outlines' / (case + '-legacy.polygons.gz'))],
                   'raw_tensors_retained': not remove_raw,
                   'metrics': metrics}
        save(result_path, outcome)
        # Preserve all raster/count/measurement/numeric anomalies. Compact polygon
        # pairs also preserve subpixel-only differences even if raw tensors are removed.
        if remove_raw:
            for file in (modern, legacy):
                if file.parent.resolve().parent != OUTPUTS.resolve() or file.is_symlink():
                    raise RuntimeError('Refusing cleanup of unexpected tensor path')
                file.unlink()
        save(directory / '.reviewed', {'case_id': case, 'status': 'compared',
             'result_path': str(result_path), 'exact_segmentation_match': exact,
             'raw_tensors_removed': remove_raw})
        print('DONE', case, 'exact=' + str(exact),
              'counts=' + str(metrics['modern_count']) + '/' + str(metrics['legacy_count']),
              'label_diff=' + str(metrics['different_label_pixels']),
              'seconds=' + str(round(time.monotonic()-start, 2)), flush=True)
    except Exception as exc:
        failure = {'case_id': case, 'metadata': meta, 'status': 'comparison_failed',
                   'error': str(exc), 'traceback': traceback.format_exc(),
                   'comparison_seconds': time.monotonic()-start}
        save(result_path, failure)
        # A failure is explicitly marked, never treated as passing or raw-cleaned.
        save(directory / '.reviewed', {**failure, 'result_path': str(result_path), 'raw_tensors_removed': False})
        print('FAILED', case, str(exc), flush=True)
    return True
while True:
    records = manifest()
    cases = sorted(p.parent for p in OUTPUTS.glob('*/.ready') if not (p.parent/'.reviewed').exists())
    for case in cases:
        handle(case, records)
    if (REVIEW / '.stop').exists():
        print('PAUSED by review supervisor', flush=True)
        break
    if (ROOT / '.producer-complete').exists() and not any(
            not (p.parent/'.reviewed').exists() for p in OUTPUTS.glob('*/.ready')):
        print('COMPLETE: producer finished and all ready pairs have durable comparison results', flush=True)
        break
    time.sleep(2)
