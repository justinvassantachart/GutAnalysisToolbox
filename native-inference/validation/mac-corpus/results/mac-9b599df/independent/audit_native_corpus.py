#!/usr/bin/env python3
"""Read-only, stdlib-only independent audit of native corpus artifact 11375896651.

No project helper code is imported, no TensorFlow/NMS/inference is run, and no
legacy raster is synthesized. Pixels are independently decoded and measured.
Usage:
  python3 audit_native_corpus.py --artifact gat-mac-official40-9b599df.zip \
    --repo /path/to/GutAnalysisToolbox --output independent-audit.json
Optionally --source-data /path/to/gat-corpus (archives/ and inputs/) and
--models /path/to/models verify retained source/input/model bytes in addition
to exact pin consistency. The report contains no machine-specific paths.
"""
import argparse
import array
import collections
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import zipfile

COMMIT = '9b599df1b8c67977228bc50104f44280047c4154'
ZIP_SHA = '678f2f005f2975e8269cdb16d8eb853de05efc401f0d3aada8472f500808d95d'
ZIP_BYTES = 6171926
MAC = Path('native-inference/validation/mac-corpus')
CORE = Path('native-inference/validation/corpus/results')
RESULTS = 'target/mac-corpus-results/'
FIELDS = ('area_pixels', 'sum_x', 'sum_y', 'four_neighbor_perimeter_px',
          'bbox_x_min', 'bbox_y_min', 'bbox_x_max_inclusive', 'bbox_y_max_inclusive')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def need(condition, message):
    if not condition:
        raise AssertionError(message)


def check_value(actual, expected, message):
    need(actual == expected, f'{message}: actual={actual!r}, expected={expected!r}')


def raster(compressed, width, height):
    """Decode u16 big endian, canonicalize by first occurrence, measure raster."""
    raw = gzip.decompress(compressed)
    check_value(len(raw), width * height * 2, 'u16 byte length')
    labels = array.array('H')
    labels.frombytes(raw)
    if sys.byteorder == 'little':
        labels.byteswap()
    mapping = {0: 0}
    next_id = 1
    canonical = array.array('H')
    for label in labels:
        if label not in mapping:
            mapping[label] = next_id
            next_id += 1
        canonical.append(mapping[label])
    stats = [[0, 0, 0, 0, width, height, 0, 0] for _ in range(next_id)]
    for at, ident in enumerate(canonical):
        if not ident:
            continue
        y, x = divmod(at, width)
        s = stats[ident]
        s[0] += 1
        s[1] += x
        s[2] += y
        s[3] += (x == 0 or canonical[at-1] != ident)
        s[3] += (x == width-1 or canonical[at+1] != ident)
        s[3] += (y == 0 or canonical[at-width] != ident)
        s[3] += (y == height-1 or canonical[at+width] != ident)
        s[4] = min(s[4], x)
        s[5] = min(s[5], y)
        s[6] = max(s[6], x)
        s[7] = max(s[7], y)
    # Java Arrays.toString(long[]) is exactly this ASCII/UTF-8 representation.
    measurement_bytes = ''.join(str(s) + '\n' for s in stats[1:]).encode('utf-8')
    canonical_be = array.array('H', canonical)
    if sys.byteorder == 'little':
        canonical_be.byteswap()
    return {'labels': labels, 'canonical': canonical, 'mapping': mapping,
            'canonical_bytes': canonical_be.tobytes(), 'stats': stats,
            'visible': next_id-1, 'label_sha256': sha(raw),
            'canonical_sha256': sha(canonical_be.tobytes()),
            'measurements_sha256': sha(measurement_bytes)}


def check_rows(rows, pixels, width, height, expected_count, prefix):
    check_value(len(rows), expected_count, prefix+' measurement row count')
    check_value({r['label_id'] for r in rows}, set(range(1, expected_count+1)),
                prefix+' complete unique original label IDs')
    for row in rows:
        label = row['label_id']
        canonical = pixels['mapping'].get(label, 0)
        check_value(row['canonical_label_id'], canonical, prefix+' row canonical ID')
        # Fully occluded labels have the contract's all-zero stats[0].
        s = pixels['stats'][canonical] if canonical else [0]*8
        for index, key in enumerate(FIELDS):
            expected = s[index] if index < 4 or s[0] else None
            check_value(row[key], expected, prefix+' row '+str(label)+' '+key)
        for axis, idx in [('x', 1), ('y', 2)]:
            expected = s[idx] / s[0] + 0.5 if s[0] else None
            check_value(row['centroid_'+axis+'_px'], expected, prefix+' exact centroid '+axis)


def polygons(compressed, width, height):
    b = gzip.decompress(compressed)
    need(len(b) >= 20, 'polygon header too short')
    magic, version, w, h, count = struct.unpack_from('>5I', b)
    check_value((magic, version, w, h), (0x47415450, 1, width, height), 'GATP header')
    out = {}
    at = 20
    for _ in range(count):
        cx, cy, rays = struct.unpack_from('>ffI', b, at)
        at += 12
        need(3 <= rays <= 1024 and math.isfinite(cx) and math.isfinite(cy), 'invalid polygon')
        points = struct.unpack_from('>'+'f'*(2*rays), b, at)
        at += 8*rays
        need(all(math.isfinite(v) for v in points), 'nonfinite polygon vertex')
        need((cx, cy) not in out, 'duplicate polygon winning center')
        out[cx, cy] = points
    check_value(at, len(b), 'exact polygon payload length')
    return out


def self_test():
    """Small hand-calculated controls for borders, separated objects and IDs."""
    def example(values):
        return raster(gzip.compress(struct.pack('>6H', *values)), 3, 2)
    empty = example([0]*6)
    check_value((empty['visible'], empty['measurements_sha256']), (0, sha(b'')), 'self-test empty')
    solid = example([7]*6)
    check_value(solid['stats'][1], [6,6,3,10,0,0,2,1], 'self-test solid border perimeter')
    first = example([2,2,0,7,0,7])
    check_value(list(first['canonical']), [1,1,0,2,0,2], 'self-test first-occurrence IDs')
    check_value(first['stats'][1:], [[2,1,0,6,0,0,1,0],[2,2,2,8,0,1,2,1]], 'self-test separated/adjacent stats')
    check_value(first['measurements_sha256'], sha(b'[2, 1, 0, 6, 0, 0, 1, 0]\n[2, 2, 2, 8, 0, 1, 2, 1]\n'), 'self-test exact measurement encoding')
    renamed = example([55,55,0,9,0,9])
    need(first['label_sha256'] != renamed['label_sha256'] and first['canonical_sha256'] == renamed['canonical_sha256'] and first['measurements_sha256'] == renamed['measurements_sha256'], 'self-test label-ID-only change')
    changed = example([2,0,2,7,7,0])
    need(first['canonical_sha256'] != changed['canonical_sha256'] and first['measurements_sha256'] != changed['measurements_sha256'], 'self-test changed pixels')
    return 7


def run(args):
    self_tests_passed = self_test()
    repo = args.repo
    frozen_bytes = (repo/MAC/'frozen-manifest.json').read_bytes()
    frozen = json.loads(frozen_bytes)
    # Pin to the exact reviewed source revision, rather than a mutable worktree.
    committed = subprocess.check_output(['git', '-C', str(repo), 'show',
                                        COMMIT+':'+str(MAC/'frozen-manifest.json')])
    check_value(frozen_bytes, committed, 'frozen manifest matches exact source commit')
    zip_bytes = args.artifact.read_bytes()
    check_value(len(zip_bytes), ZIP_BYTES, 'download ZIP byte length')
    check_value(sha(zip_bytes), ZIP_SHA, 'download ZIP SHA-256')
    z = zipfile.ZipFile(args.artifact)
    names = [i.filename for i in z.infolist() if not i.is_dir()]
    check_value(len(names), len(set(names)), 'no duplicate ZIP member names')
    need(z.testzip() is None, 'ZIP CRC verification')
    def read(rel):
        return z.read(RESULTS+rel)
    def js(rel):
        return json.loads(read(rel))
    summary = js('summary.json')
    artifact_manifest = js('artifact-manifest.json')
    prep = json.loads(z.read('target/mac-corpus-prepared/preparation.json'))
    check_value(sha(read('artifact-manifest.json')), summary['metadata']['artifact_manifest_sha256'], 'evidence manifest digest')
    actual_compact = {n[len(RESULTS):] for n in names if n.startswith(RESULTS)} - {'summary.json', 'artifact-manifest.json'}
    check_value(set(artifact_manifest), actual_compact, 'complete compact evidence manifest membership')
    for name, expected in artifact_manifest.items():
        check_value(sha(read(name)), expected, 'compact artifact '+name)
    frozen_cases = {c['case_id']: c for c in frozen['cases']}
    check_value(len(frozen_cases), 40, '40 unique case IDs')
    check_value(frozen['case_count'], 40, 'frozen case count')
    check_value({c['case_id'] for c in summary['cases']}, set(frozen_cases), 'summary case membership')
    check_value(len(summary['cases']), 40, 'summary no duplicate cases')
    check_value(set(prep['case_ids']), set(frozen_cases), 'preparation case membership')
    check_value(len(prep['case_ids']), 40, 'preparation no duplicate cases')
    check_value({n.split('/')[0] for n in actual_compact}, set(frozen_cases), 'artifact case membership')
    check_value(summary['metadata']['checkout_commit'], COMMIT, 'source commit')
    check_value(prep, summary['metadata']['preparation'], 'original preparation and summary copy')
    for meta in (prep, summary['metadata']):
        check_value(meta['frozen_manifest_sha256'], sha(frozen_bytes), 'manifest digest pin')
    check_value(prep['reference_files_verified'], frozen['reference_files'], 'reference file pins')
    check_value(prep['model_sha256'], {k:v['sha256'] for k,v in frozen['models'].items()}, 'model pins')
    check_value(prep['source_archives'], {k:v['sha256'] for k,v in frozen['archives'].items()}, 'archive pins')
    check_value(sha((repo/MAC/'dependencies.json').read_bytes()), summary['metadata']['dependencies_manifest_sha256'], 'dependency manifest digest')
    for name, expected in summary['metadata']['harness_source_hashes'].items():
        check_value(sha((repo/MAC/name).read_bytes()), expected, 'harness source '+name)
    for name, expected in frozen['reference_files'].items():
        check_value(sha((repo/CORE/name).read_bytes()), expected, 'actual reference file '+name)
    originals = {c['case_id']: c for c in json.loads((repo/CORE/'core/cases.json').read_text())}
    legacy_zip = zipfile.ZipFile(repo/CORE/'outline-payloads-001.zip')
    check_value({c['case_id'] for c in originals.values() if c['metadata']['split']=='test'}, set(frozen_cases), 'original official-test membership')
    by_input = collections.defaultdict(list)
    for c in originals.values():
        by_input[c['metadata']['input_sha256']].append(c)
    for case in frozen_cases.values():
        for split, key in [('test','same_test_input_case_ids'), ('train','same_train_input_case_ids')]:
            actual = sorted(c['case_id'] for c in by_input[case['input_sha256']]
                            if c['metadata']['split']==split and c['case_id']!=case['case_id'])
            check_value(actual, sorted(case[key]), case['case_id']+' '+key)
    unique = len({c['input_sha256'] for c in frozen_cases.values()})
    overlaps = [c['case_id'] for c in frozen_cases.values() if c['same_train_input_case_ids']]
    total_pixels = sum(c['width']*c['height'] for c in frozen_cases.values())
    check_value(unique, 39, 'unique inputs')
    check_value(len(overlaps), 1, 'one test input overlaps training')
    check_value(total_pixels, 26030351, 'total supplied pixels')
    check_value(dict(collections.Counter(c['stain'] for c in frozen_cases.values())), frozen['stains'], 'stain membership')
    optional = {'retained_model_bytes_verified': False,
                'retained_archive_and_source_tiff_bytes_verified': False,
                'retained_gati_input_bytes_verified': False}
    if args.models:
        for info in frozen['models'].values():
            check_value(sha((args.models/info['filename']).read_bytes()), info['sha256'], 'retained model byte hash')
        optional['retained_model_bytes_verified'] = True
    if args.source_data:
        archives = {}
        for name, info in frozen['archives'].items():
            b = (args.source_data/'archives'/name).read_bytes()
            check_value((len(b), sha(b), hashlib.md5(b).hexdigest()),
                        (info['bytes'], info['sha256'], info['md5']), 'retained source archive '+name)
            archives[name] = zipfile.ZipFile(args.source_data/'archives'/name)
        for name, archive in archives.items():
            actual_sources = {n for n in archive.namelist() if n.startswith('test/images/') and not n.endswith('/')}
            expected_sources = {c['source']['source_path'] for c in frozen_cases.values() if c['source']['source_archive']==name}
            check_value(actual_sources, expected_sources, 'source archive exact test-file membership '+name)
        for cid, case in frozen_cases.items():
            source = case['source']
            tiff = archives[source['source_archive']].read(source['source_path'])
            check_value(sha(tiff), source['source_sha256'], cid+' original TIFF hash')
            data = (args.source_data/'inputs'/(cid+'.bin')).read_bytes()
            check_value((len(data), sha(data)), (case['input_bytes'], case['input_sha256']), cid+' retained GATI length/hash')
            check_value(struct.unpack_from('>4I', data), (0x47415449, 1, case['width'], case['height']), cid+' GATI shape')
        for cid in overlaps:
            case = frozen_cases[cid]
            for train_id in case['same_train_input_case_ids']:
                check_value(sha((args.source_data/'inputs'/(train_id+'.bin')).read_bytes()), case['input_sha256'], 'actual training overlap input bytes '+train_id)
        optional.update(retained_archive_and_source_tiff_bytes_verified=True, retained_gati_input_bytes_verified=True)
    rows = []
    object_total = 0
    retained_total = 0
    summary_cases = {c['case_id']:c for c in summary['cases']}
    for cid, case in frozen_cases.items():
        status = js(cid+'/case.json')
        g = js(cid+'/actual.geometry.json')
        original = originals[cid]
        expected = case['legacy_expected']
        check_value(status, summary_cases[cid], cid+' exact summary case copy')
        check_value(status['metadata'], case, cid+' every frozen per-case metadata field')
        check_value(status['status'], 'compared', cid+' complete status')
        check_value(status['comparison']['archived_legacy'], expected, cid+' legacy hash pins')
        for key, value in expected.items():
            check_value(original['metrics'][key], value, cid+' original reference '+key)
        for key in ('input_sha256', 'source_sha256', 'source_path', 'source_archive'):
            value = case[key] if key in case else case['source'][key]
            check_value(original['metadata'][key], value, cid+' original input/source pin '+key)
        for name, expected_hash in status['artifacts_sha256'].items():
            check_value(sha(read(cid+'/'+name)), expected_hash, cid+' per-case artifact '+name)
        check_value(set(status['artifacts_sha256']), {n.split('/',1)[1] for n in artifact_manifest if n.startswith(cid+'/')} - {'case.json'}, cid+' case hash coverage')
        width, height = case['width'], case['height']
        for key in ('width','height','channels','probability_threshold','nms_threshold','excluded_boundary'):
            check_value(g[key], case[key], cid+' geometry contract '+key)
        p = raster(read(cid+'/actual.modern.labels.u16be.gz'), width, height)
        cb = gzip.decompress(read(cid+'/actual.modern.canonical.u16be.gz'))
        check_value(cb, p['canonical_bytes'], cid+' pixel-exact first-raster-occurrence canonicalization')
        for suffix in ('label_sha256','canonical_sha256','measurements_sha256'):
            check_value(p[suffix], g['modern_'+suffix], cid+' independently recomputed '+suffix)
            check_value(g['modern_'+suffix], status['comparison']['actual_modern']['modern_'+suffix], cid+' comparison '+suffix)
        check_value(p['visible'], g['modern_visible_labels'], cid+' visible labels from raster')
        check_rows(g['modern_object_measurements'], p, width, height, g['modern_count'], cid+' modern')
        object_total += len(g['modern_object_measurements'])
        modern_polys = polygons(read(cid+'/actual.modern.polygons.gz'), width, height)
        legacy_compressed = legacy_zip.read(case['legacy_outline']['member'])
        check_value(sha(legacy_compressed), case['legacy_outline']['sha256'], cid+' archived polygon bytes')
        legacy_polys = polygons(legacy_compressed, width, height)
        check_value(len(modern_polys), g['modern_count'], cid+' independent modern polygon count')
        check_value(len(legacy_polys), expected['legacy_count'], cid+' independent legacy polygon count')
        centers_equal = set(modern_polys) == set(legacy_polys)
        strict_equal = modern_polys == legacy_polys
        check_value(centers_equal, g['winner_centers_equal'], cid+' independently decoded centers')
        check_value(strict_equal, g['strict_quantized_outlines_equal'], cid+' independently decoded vertices')
        check_value(set(modern_polys), {(r['winning_center_x_px'],r['winning_center_y_px']) for r in g['modern_object_measurements']}, cid+' polygon-to-measurement centers')
        check_value(g['modern_candidates'], expected['legacy_candidates'], cid+' reported candidate count vs pinned legacy')
        check_value(len(modern_polys), expected['legacy_count'], cid+' object count matches legacy')
        check_value(p['visible'], expected['legacy_visible_labels'], cid+' visible count matches legacy')
        foreground = {}
        for side in ('modern','legacy'):
            b = gzip.decompress(read(cid+'/actual.'+side+'.foreground.u8.gz'))
            check_value(len(b), width*height, cid+' '+side+' foreground length')
            need(set(b) <= {0,1}, cid+' binary foreground')
            check_value(sha(b), g[side+'_foreground_sha256'], cid+' foreground digest')
            check_value(sum(b), g[side+'_foreground_pixels'], cid+' foreground count')
            foreground[side] = b
        check_value(foreground['modern'], bytes(bool(v) for v in p['labels']), cid+' foreground equals raw label occupancy')
        fg_diff = [i for i,(a,b) in enumerate(zip(foreground['modern'],foreground['legacy'])) if a!=b]
        intersection = sum(a and b for a,b in zip(foreground['modern'],foreground['legacy']))
        union = sum(a or b for a,b in zip(foreground['modern'],foreground['legacy']))
        check_value(len(fg_diff), g['different_foreground_pixels'], cid+' independently measured foreground delta')
        check_value((intersection,union), (g['foreground_intersection_pixels'],g['foreground_union_pixels']), cid+' foreground intersection/union')
        check_value(intersection/union if union else 1.0, g['foreground_iou'], cid+' foreground IoU')
        eq_raw = p['label_sha256'] == expected['legacy_label_sha256']
        eq_can = p['canonical_sha256'] == expected['legacy_canonical_sha256']
        eq_measure = p['measurements_sha256'] == expected['legacy_measurements_sha256']
        for key,value in [('exact_raw_label_ids_and_pixels_equal',eq_raw),('exact_identity_insensitive_raster_equal',eq_can),('exact_canonical_measurements_equal',eq_measure),('exact_raster_and_measurements_equal',eq_can and eq_measure)]:
            check_value(status['comparison'][key], value, cid+' recomputed flag '+key)
        retained = bool(case['legacy_order_available'])
        check_value(g['legacy_composite_available'], retained, cid+' order availability')
        legacy_raster_diffs = None
        if retained:
            retained_total += 1
            details = original['metrics']['legacy_object_measurements']
            order = ''.join(f'{r["winning_center_x_px"]}\t{r["winning_center_y_px"]}\t{r["label_id"]}\n' for r in details).encode()
            check_value(sha(order), g['legacy_order_sha256'], cid+' authoritative retained paint-order pin')
            lp = raster(read(cid+'/actual.legacy.labels.u16be.gz'), width, height)
            check_value(gzip.decompress(read(cid+'/actual.legacy.canonical.u16be.gz')), lp['canonical_bytes'], cid+' retained legacy canonicalization')
            # Verify every authoritative raster/measurement hash BEFORE pixel deltas.
            for suffix in ('label_sha256','canonical_sha256','measurements_sha256'):
                check_value(lp[suffix], expected['legacy_'+suffix], cid+' authoritative legacy raster '+suffix)
                check_value(lp[suffix], g['legacy_'+suffix], cid+' retained legacy geometry '+suffix)
            check_rows(g['legacy_object_measurements'], lp, width, height, expected['legacy_count'], cid+' retained legacy')
            need({(r['winning_center_x_px'],r['winning_center_y_px'],r['label_id']) for r in g['legacy_object_measurements']} == {(r['winning_center_x_px'],r['winning_center_y_px'],r['label_id']) for r in details}, cid+' original order assignments')
            raw_diff = sum(a!=b for a,b in zip(p['labels'],lp['labels']))
            canonical_diff = sum(a!=b for a,b in zip(p['canonical'],lp['canonical']))
            check_value((raw_diff,canonical_diff), (g['different_label_pixels'],g['different_canonical_label_pixels']), cid+' retained exclusive-map deltas')
            legacy_raster_diffs = {'raw_numeric_label_pixels':raw_diff,'canonical_label_pixels':canonical_diff}
        else:
            for key in ('legacy_label_sha256','legacy_canonical_sha256','legacy_measurements_sha256','different_label_pixels','different_canonical_label_pixels'):
                check_value(g[key], None, cid+' unavailable original-map field '+key)
            check_value(g['legacy_object_measurements'], [], cid+' absent legacy object measurements')
        available = eq_can or retained
        check_value(status['comparison']['original_exclusive_label_difference_count_available'], available, cid+' truthful original delta availability')
        expected_delta = 0 if eq_can else (legacy_raster_diffs['canonical_label_pixels'] if retained else None)
        check_value(status['comparison']['original_exclusive_label_difference_count'], expected_delta, cid+' original canonical delta')
        rows.append({'case_id':cid,'width':width,'height':height,'object_count':len(modern_polys),'visible_labels':p['visible'],
                     'candidate_count_reported_and_pin_compared':g['modern_candidates'],
                     'raw_label_sha256_recomputed':p['label_sha256'],'canonical_sha256_recomputed':p['canonical_sha256'],
                     'measurements_sha256_recomputed':p['measurements_sha256'],
                     'raw_label_equal_legacy':eq_raw,'canonical_equal_legacy':eq_can,'measurement_equal_legacy':eq_measure,
                     'winning_centers_equal':centers_equal,'strict_quantized_outlines_equal':strict_equal,
                     'foreground_difference_pixels':len(fg_diff),
                     'foreground_difference_coordinates_xy':[[i%width,i//width] for i in fg_diff],
                     'retained_original_legacy_maps_hash_verified':retained,
                     'original_exclusive_map_differences':legacy_raster_diffs,
                     'original_exclusive_canonical_delta_available':available,
                     'original_exclusive_canonical_delta':expected_delta})
        print('PASS',cid,flush=True)
    counts = {'case_count':len(rows),'object_count':object_total,'unique_input_count':unique,
              'test_cases_with_train_overlap':len(overlaps),'input_pixels':total_pixels,
              'raw_label_equal_cases':sum(r['raw_label_equal_legacy'] for r in rows),
              'canonical_equal_cases':sum(r['canonical_equal_legacy'] for r in rows),
              'measurement_equal_cases':sum(r['measurement_equal_legacy'] for r in rows),
              'winning_center_equal_cases':sum(r['winning_centers_equal'] for r in rows),
              'strict_quantized_outline_equal_cases':sum(r['strict_quantized_outlines_equal'] for r in rows),
              'foreground_equal_cases':sum(r['foreground_difference_pixels']==0 for r in rows),
              'foreground_difference_pixels':sum(r['foreground_difference_pixels'] for r in rows),
              'retained_legacy_order_cases':retained_total,
              'compact_files_hashed':len(artifact_manifest),'zip_members_crc_checked':len(names)}
    for key, expected_count in [('object_count',4472),('raw_label_equal_cases',37),('canonical_equal_cases',39),
                                ('measurement_equal_cases',39),('winning_center_equal_cases',40),
                                ('strict_quantized_outline_equal_cases',8),('foreground_equal_cases',39),
                                ('foreground_difference_pixels',1),('retained_legacy_order_cases',2)]:
        check_value(counts[key], expected_count, 'independent aggregate '+key)
    check_value(summary['exact_raster_and_measurement_case_count'], counts['canonical_equal_cases'], 'summary raster aggregate')
    check_value(summary['strict_quantized_outline_case_count'], counts['strict_quantized_outline_equal_cases'], 'summary outline aggregate')
    check_value(summary['scientific_equivalence_established'], False, 'no equivalence claim')
    check_value(summary['tensor_numerical_comparison_performed'], False, 'no numeric tensor comparison claim')
    return {'audit_schema':1,'status':'passed','artifact_id':11375896651,'run_id':37381573321,'job_id':112004603172,
            'source_commit':COMMIT,'artifact_zip_sha256':ZIP_SHA,'artifact_zip_bytes':ZIP_BYTES,
            'frozen_manifest_sha256':sha(frozen_bytes),'artifact_manifest_sha256':sha(read('artifact-manifest.json')),
            'audit_script_sha256':sha(Path(__file__).read_bytes()),'self_tests_passed':self_tests_passed,'counts':counts,
            'optional_retained_byte_verification':optional,
            'reference_file_hashes_verified':frozen['reference_files'],
            'measurement_contract':'Canonical first-raster-occurrence IDs; SHA-256 of UTF-8 Java array rows [area, sum_x, sum_y, 4_neighbor_perimeter, xmin, ymin, xmax, ymax] plus newline; integer pixel units, centroid +0.5',
            'method':'Independent Python standard-library binary decoder and direct raster scanner; all modern per-object eight-field measurements and centroids verified against decoded pixels; polygons decoded independently for counts, centers and strict vertex equality',
            'limits':['No TensorFlow inference, NMS or numeric tensor-tolerance comparison is performed. Candidate counts are checked across archived records, not recomputed from unavailable tensors.',
                      'The source/model/input bytes checked with optional arguments are retained local copies matching exact frozen pins; native-run original raw input/model files are not included in the compact result artifact.',
                      'Legacy exclusive maps are read only for the two retained-order cases and verified against all authoritative hashes before pixel differences are accepted. No missing-order legacy composite is reconstructed.',
                      'Foreground masks are independently decoded and compared, but this script does not rerasterize polygons. Foreground-union delta is distinct from unavailable original exclusive-label delta.',
                      '40 source-labeled tests represent 39 unique inputs, one overlapping training; this is runtime consistency evidence, not biological validation or scientific equivalence.'],
            'cases':rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact',type=Path,required=True)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--source-data',type=Path)
    parser.add_argument('--models',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    try:
        result = run(args)
    except Exception as exc:
        result = {'audit_schema':1,'status':'failed','error':str(exc)}
        args.output.write_text(json.dumps(result,indent=2)+'\n')
        raise
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['counts'],indent=2))


if __name__ == '__main__':
    main()
