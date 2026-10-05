#!/usr/bin/env python3
"""Serial cold-process native corpus diagnostics. Completion is NOT equivalence."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import time

from prepare import ROOT, CORPUS, digest, fetch, load_manifest, save, verify, verify_references

THREADS = {'TF_NUM_INTRAOP_THREADS': '2', 'TF_NUM_INTEROP_THREADS': '1', 'OMP_NUM_THREADS': '2',
           'CUDA_VISIBLE_DEVICES': '-1'}
MAX_HEAP = '-Xmx3g'
# These are investigation flags, never an acceptance tolerance or production change.
OUTLIER_RULES = {'any_unmatched_winner_center': True, 'all_matched_per_cell_deltas_retained': True,
                 'note': 'No fitted acceptance thresholds. Inspect full per-cell IoU, area, centroid and outline deltas.'}


def host_metadata(java):
    path = ROOT.parent / 'cross-platform/check.py'
    spec = importlib.util.spec_from_file_location('mac_corpus_host_metadata', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.runner_metadata(java)
    result['numeric_thread_environment'] = THREADS
    result['metadata_probe_source_sha256'] = digest(path)
    if platform.system() == 'Darwin':
        for key in ('hw.model', 'hw.memsize', 'hw.logicalcpu', 'sysctl.proc_translated'):
            try:
                probe = subprocess.run(['/usr/sbin/sysctl', '-n', key], capture_output=True,
                                       text=True, timeout=5, check=False)
                result[key] = probe.stdout.strip() if probe.returncode == 0 else None
            except (OSError, subprocess.TimeoutExpired):
                result[key] = None
    return result


def require_native_mac(host):
    if (host.get('system') != 'Darwin' or host.get('machine') != 'arm64' or
            host.get('java', {}).get('os.arch') not in ('aarch64', 'arm64') or
            host.get('sysctl.proc_translated') == '1'):
        raise ValueError('Requires actual native arm64 macOS and ARM Java; Rosetta/architecture labels do not qualify')


def worker_inventory(worker, expected_native):
    if not worker.is_file():
        raise FileNotFoundError('Missing isolated modern worker JAR')
    libs = sorted((worker.parent / 'lib').glob('*.jar'))
    names = {p.name for p in libs}
    wanted = {'javacpp-1.5.12.jar', 'protobuf-java-4.31.1.jar', 'tensorflow-core-api-1.2.0.jar',
              'tensorflow-core-native-1.2.0.jar', 'tensorflow-ndarray-1.2.0.jar',
              f'tensorflow-core-native-1.2.0-{expected_native}.jar'}
    if names != wanted:
        raise ValueError(f'Unexpected/mixed worker runtime JARs: {sorted(names ^ wanted)}')
    return {p.name: digest(p) for p in [worker, *libs]}


def prepare_geometry(cache, java, javac):
    entries = json.loads((ROOT / 'dependencies.json').read_text())
    cache.mkdir(parents=True, exist_ok=True)
    for item in entries:
        fetch(cache / item['file'], item['url'], item['sha256'], 20_000_000, True)
    jars = os.pathsep.join(str(cache / item['file']) for item in entries if item['file'].endswith('.jar'))
    classes = cache / 'classes'
    classes.mkdir(exist_ok=True)
    sources = [str(cache / item['file']) for item in entries if item['file'].endswith('.java')]
    subprocess.run([javac, '-encoding', 'UTF-8', '-cp', jars, '-d', str(classes),
                    *sources, str(ROOT / 'MacCorpusGeometry.java'), str(ROOT / 'MacCorpusGeometryTest.java')], check=True, timeout=180)
    subprocess.run([java, '-Xmx512m', '-Djava.awt.headless=true', '-cp', str(classes) + os.pathsep + jars,
                    'MacCorpusGeometryTest'], check=True, timeout=120)
    return [java, '-XX:-UsePerfData', '-Xms64m', MAX_HEAP, '-Djava.awt.headless=true',
            '-cp', str(classes) + os.pathsep + jars, 'MacCorpusGeometry']


def timed_run(command, log, timeout, environment=None):
    started = time.perf_counter()
    with log.open('w') as stream:
        subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout,
                       check=True, env=environment)
    return time.perf_counter() - started


def cleanup_worker_scratch(scratch, case_dir):
    """Remove only this fresh case's owned scratch after its worker has exited."""
    if scratch.parent != case_dir or scratch.name != 'worker-scratch' or scratch.is_symlink():
        raise ValueError('Refusing cleanup outside owned worker scratch')
    if scratch.exists():
        shutil.rmtree(scratch)


def worker_scratch_inventory(scratch):
    files = [p for p in scratch.rglob('*') if p.is_file()]
    return dict(files=len(files), bytes=sum(p.stat().st_size for p in files),
                partial_prediction_sha256={p.name: digest(p) for p in scratch.glob('.gat-result-*.tmp')})


def finalize_case(report, case_dir, scratch, prediction, replay):
    """Commit compared only after durable compact evidence and owned-temp cleanup."""
    try:
        if not replay and prediction.exists() and 'modern_tensor_sha256' not in report:
            report['modern_tensor_sha256'] = digest(prediction)
            report['modern_tensor_bytes'] = prediction.stat().st_size
        if not replay:
            report['worker_scratch_before_cleanup'] = worker_scratch_inventory(scratch)
            report['raw_modern_tensor_retained_in_report'] = prediction.exists()
            save(case_dir / 'case.json', report)
            cleanup_worker_scratch(scratch, case_dir)
        terminal = dict(report)
        terminal['raw_modern_tensor_retained_in_report'] = False
        terminal['artifacts_sha256'] = {p.name: digest(p) for p in case_dir.iterdir()
                                       if p.is_file() and p.name != 'case.json'}
        if terminal['status'] == 'comparison_ready':
            terminal['status'] = 'compared'
        save(case_dir / 'case.json', terminal)
        report.clear()
        report.update(terminal)
    except Exception as error:
        report['status'] = 'failed'
        report['evidence_finalization_error'] = f'{type(error).__name__}: {error}'
        report['raw_modern_tensor_retained_in_report'] = bool(not replay and prediction.exists())
        try:
            save(case_dir / 'case.json', report)
        except Exception as persistence_error:
            report['failure_report_persistence_error'] = f'{type(persistence_error).__name__}: {persistence_error}'
        raise


def check_input(path, case):
    if path.stat().st_size != case['input_bytes']:
        raise ValueError('Prepared input byte length mismatch')
    verify(path, case['input_sha256'])
    with path.open('rb') as stream:
        header = struct.unpack('>4i', stream.read(16))
    if header != (0x47415449, 1, case['width'], case['height']):
        raise ValueError('Prepared input header mismatch')


def reference_comparison(case, geometry):
    if (geometry['width'], geometry['height'], geometry['channels']) != (case['width'], case['height'], 97):
        raise ValueError('Geometry dimensions changed')
    if (geometry['probability_threshold'] != case['probability_threshold'] or
            geometry['nms_threshold'] != 0.3 or geometry['excluded_boundary'] != 2):
        raise ValueError('Geometry thresholds changed')
    expected = case['legacy_expected']
    if geometry['legacy_count'] != expected['legacy_count']:
        raise ValueError('Archived legacy polygon count changed')
    expected_order = case['legacy_order_available']
    for name in ('label_sha256', 'canonical_sha256', 'measurements_sha256'):
        if (geometry.get('legacy_' + name) is not None) != expected_order:
            raise ValueError('Legacy composite hash presence does not match retained-order availability')
    # Any available reconstructed legacy composite must first prove that it is
    # exactly the archived original. Independent polygon masks are not this map.
    for name in ('label_sha256', 'canonical_sha256', 'measurements_sha256'):
        reconstructed = geometry.get('legacy_' + name)
        if reconstructed is not None and reconstructed != expected['legacy_' + name]:
            raise ValueError(f'Reconstructed legacy composite disagrees with authoritative {name}')
    equal = {name: geometry['modern_' + name] == expected['legacy_' + name]
             for name in ('count', 'visible_labels', 'label_sha256', 'canonical_sha256', 'measurements_sha256')}
    equal['candidates'] = geometry['modern_candidates'] == expected['legacy_candidates']
    return dict(archived_legacy=expected, actual_modern={
                    'modern_' + k: geometry['modern_' + k] for k in equal},
                exact_count_equal=equal['count'], exact_candidate_count_equal=equal['candidates'],
                exact_raw_label_ids_and_pixels_equal=equal['label_sha256'],
                exact_identity_insensitive_raster_equal=equal['canonical_sha256'],
                exact_canonical_measurements_equal=equal['measurements_sha256'],
                exact_raster_and_measurements_equal=all(equal[k] for k in ('count', 'visible_labels', 'canonical_sha256', 'measurements_sha256')),
                legacy_composite_available=case['legacy_order_available'],
                original_exclusive_label_difference_count_available=case['legacy_order_available'] or equal['canonical_sha256'],
                original_exclusive_label_difference_count=(0 if equal['canonical_sha256'] else geometry.get('different_canonical_label_pixels')),
                tensor_numerical_comparison_performed=False,
                tensor_comparison_note='Full legacy probability/distance tensors are unavailable for38/40; this harness does not perform tensor tolerance comparisons.',
                legacy_paint_order_limitation=None if case['legacy_order_available'] else
                    'Archived polygons are lexical-center ordered, not winner ordered. No original legacy exclusive label-map reconstruction or mismatch pixel count is claimed.')


def summary(manifest, reports, metadata):
    compared = [r for r in reports if r['status'] == 'compared']
    expected_ids = {c['case_id'] for c in manifest['cases']}
    observed_ids = [r.get('case_id') for r in reports]
    membership_exact = len(observed_ids) == len(set(observed_ids)) and set(observed_ids) == expected_ids
    complete = (membership_exact and len(reports) == 40 and len(compared) == 40
                and not metadata.get('setup_or_run_error')
                and metadata.get('evidence_manifest_committed') is True)
    exact = complete and all(r['comparison']['exact_raster_and_measurements_equal'] for r in compared)
    host = metadata.get('runner', {})
    native = (host.get('system') == 'Darwin' and host.get('machine') == 'arm64' and
              host.get('java', {}).get('os.arch') in ('aarch64', 'arm64') and
              host.get('sysctl.proc_translated') != '1' and
              metadata.get('execution_kind') == 'cold_modern_worker_inference')
    return dict(schema=1, status=('complete' if complete else 'incomplete_or_failed'),
                native_all40_completed=complete and native,
                run_completed=complete, scientific_equivalence_established=False,
                all40_exact_identity_insensitive_raster_and_measurement_hashes_equal=exact,
                expected_cases=40, selected_cases=len(reports), compared_cases=len(compared),
                exact_case_id_membership=membership_exact,
                missing_case_ids=sorted(expected_ids - set(observed_ids)),
                failed_cases=sum(r['status'] == 'failed' for r in reports),
                blocked_cases=sum(r['status'] == 'blocked' for r in reports),
                pending_cases=sum(r['status'] in ('not_run', 'running', 'comparison_ready') for r in reports),
                exact_raster_and_measurement_case_count=sum(r['comparison']['exact_raster_and_measurements_equal'] for r in compared),
                strict_quantized_outline_case_count=sum(r.get('geometry_summary', {}).get('strict_quantized_outlines_equal', False) for r in compared),
                unmatched_modern_outline_centers=sum(r.get('geometry_summary', {}).get('unmatched_modern_outline_centers', 0) for r in compared),
                unmatched_legacy_outline_centers=sum(r.get('geometry_summary', {}).get('unmatched_legacy_outline_centers', 0) for r in compared),
                unique_input_count=manifest['unique_input_count'], input_pixels=manifest['input_pixels'],
                independence_note=manifest['independence_note'],
                tensor_numerical_comparison_performed=False, metadata=metadata, cases=reports,
                interpretation='Completion records execution coverage only. Hash/geometry differences remain reported; no biological accuracy or general scientific equivalence claim. Fixed production thresholds remain unchanged.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', type=Path)
    parser.add_argument('--models', type=Path)
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--java', default='java')
    parser.add_argument('--javac', default='javac')
    parser.add_argument('--dependencies', type=Path)
    parser.add_argument('--expect-native-mac', action='store_true')
    parser.add_argument('--case-id', action='append', help='Development subset only; cannot produce all40 completion')
    parser.add_argument('--replay-predictions', type=Path, help='Development ONLY: read retained <case>/modern.bin; never infer or relabel as native')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output must be new/empty: prevents stale outputs from passing a rerun')
    output.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    manifest = load_manifest()
    cases = manifest['cases']
    reports = [dict(case_id=c['case_id'], status='not_run', metadata=c) for c in cases]
    metadata = dict(evidence_manifest_committed=False, frozen_manifest_sha256=digest(ROOT / 'frozen-manifest.json'),
                    harness_source_hashes={p.name: digest(p) for p in sorted(ROOT.glob('*.py')) + sorted(ROOT.glob('*.java'))},
                    dependencies_manifest_sha256=digest(ROOT / 'dependencies.json'),
                    reference_runtime=manifest['legacy_runtime'], reference_platform=manifest['legacy_platform'],
                    execution_kind='archived_linux_tensor_development_replay' if args.replay_predictions else 'cold_modern_worker_inference',
                    timing_sample_count_per_case=1, timing_warmup_runs=0, maximum_java_heap='3GiB',
                    serial_process_policy='One worker OR one geometry JVM at a time; each case uses a fresh cold worker process',
                    outlier_investigation_rules=OUTLIER_RULES)
    repo = ROOT.parents[2]
    source = repo / 'native-inference/src/main/java/org/gatanalysis/inference'
    metadata['production_sources_sha256'] = {p.name: digest(p) for p in sorted(source.glob('*.java'))}
    commit = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'], capture_output=True, text=True, timeout=10, check=False)
    metadata['checkout_commit'] = commit.stdout.strip() if commit.returncode == 0 else None
    try:
        verify_references(manifest)
        preparation = json.loads((args.prepared / 'preparation.json').read_text())
        if preparation['frozen_manifest_sha256'] != metadata['frozen_manifest_sha256'] or preparation['case_count'] != 40:
            raise ValueError('Preparation does not match frozen40 manifest')
        metadata['preparation'] = preparation
        metadata['runner'] = host_metadata(args.java)
        if args.expect_native_mac:
            require_native_mac(metadata['runner'])
            if args.replay_predictions:
                raise ValueError('Replay is not native inference')
        cases = manifest['cases']
        if args.case_id:
            if len(set(args.case_id)) != len(args.case_id) or not set(args.case_id) <= {c['case_id'] for c in cases}:
                raise ValueError('Unknown or duplicate requested case ID')
            cases = [c for c in cases if c['case_id'] in args.case_id]
        if not args.replay_predictions:
            if args.worker is None or args.models is None:
                raise ValueError('--worker and --models are required for inference')
            native = 'macosx-arm64' if metadata['runner']['system'] == 'Darwin' else 'linux-x86_64'
            metadata['worker_inventory_sha256'] = worker_inventory(args.worker.resolve(), native)
            for model in manifest['models'].values():
                verify(args.models / model['filename'], model['sha256'])
        reports = [dict(case_id=c['case_id'], status='not_run', metadata=c) for c in cases]
        save(output / 'summary.json', summary(manifest, reports, metadata))
        setup = time.perf_counter()
        geometry_command = prepare_geometry((args.dependencies or output / 'dependencies').resolve(), args.java, args.javac)
        metadata['geometry_dependency_verification_and_compilation_seconds'] = time.perf_counter() - setup
        for case, report in zip(cases, reports):
            case_dir = output / case['case_id']
            case_dir.mkdir()
            report['status'] = 'running'
            save(output / 'summary.json', summary(manifest, reports, metadata))
            case_started = time.perf_counter()
            scratch = case_dir / 'worker-scratch'
            prediction = (args.replay_predictions / case['case_id'] / 'modern.bin') if args.replay_predictions else scratch / 'actual.gato'
            try:
                source = args.prepared / 'inputs' / (case['case_id'] + '.gati')
                check_input(source, case)
                legacy = args.prepared / 'references' / (case['case_id'] + '.legacy.polygons.gz')
                verify(legacy, case['legacy_outline']['sha256'])
                order = args.prepared / 'references' / (case['case_id'] + '.legacy-order.tsv')
                if order.exists() != case['legacy_order_available']:
                    raise ValueError('Unexpected legacy order availability')
                if not args.replay_predictions:
                    if shutil.disk_usage(output).free < 2_000_000_000:
                        raise RuntimeError('Less than2GB free disk; bounded run cannot safely proceed')
                    jvm_temp = scratch / 'jvm-tmp'
                    jvm_temp.mkdir(parents=True)
                    worker = args.worker.resolve()
                    command = [args.java, '-XX:-UsePerfData', '-Xms64m', MAX_HEAP,
                               '-Djava.io.tmpdir=' + str(jvm_temp), '-cp',
                               str(worker) + os.pathsep + str(worker.parent / 'lib' / '*'),
                               'org.gatanalysis.inference.NativeInferenceMain',
                               str((args.models / manifest['models'][case['model']]['filename']).resolve()),
                               str(source.resolve()), str(prediction), '4']
                    worker_started = time.perf_counter()
                    try:
                        timed_run(command, case_dir / 'worker.log', 900, dict(os.environ, **THREADS))
                    finally:
                        report['cold_worker_process_end_to_end_seconds'] = time.perf_counter() - worker_started
                else:
                    report['cold_worker_process_end_to_end_seconds'] = None
                report['modern_tensor_sha256'] = digest(prediction)
                report['modern_tensor_bytes'] = prediction.stat().st_size
                geometry_started = time.perf_counter()
                try:
                    timed_run(geometry_command + [str(prediction.resolve()), str(legacy.resolve()),
                              str(order.resolve()) if order.exists() else '-', str(case_dir / 'actual'),
                              str(case['probability_threshold'])], case_dir / 'geometry.log', 300)
                finally:
                    report['geometry_process_end_to_end_seconds'] = time.perf_counter() - geometry_started
                geometry = json.loads((case_dir / 'actual.geometry.json').read_text())
                if geometry['modern_tensor_sha256'] != report['modern_tensor_sha256']:
                    raise ValueError('Comparator processed a different modern tensor')
                report['comparison'] = reference_comparison(case, geometry)
                report['geometry_summary'] = {k: geometry[k] for k in (
                    'winner_centers_equal', 'strict_quantized_outlines_equal', 'matched_outline_objects',
                    'unmatched_modern_outline_centers', 'unmatched_legacy_outline_centers',
                    'outline_ray_count_mismatches', 'outlines_with_changed_vertices', 'changed_outline_vertices',
                    'max_abs_vertex_coordinate_delta_px', 'max_euclidean_vertex_delta_px',
                    'max_abs_polygon_area_delta_px2', 'max_abs_polygon_perimeter_delta_px',
                    'matched_center_min_independent_polygon_iou', 'foreground_iou', 'different_foreground_pixels',
                    'independent_polygon_masks_equal_ignoring_ids_and_centers')}
                changed = [r for r in geometry['matched_center_comparisons']
                           if r['different_mask_pixels'] or r['changed_vertices'] or not r['ray_counts_match']]
                changed.sort(key=lambda r: (r['per_object_iou'], -(r['centroid_distance_px'] or 0)))
                save(case_dir / 'outliers.json', dict(
                    scope='Independent polygon masks; exclusive legacy label differences require retained order',
                    total_changed_matched_objects=len(changed),
                    matched_objects_ranked_by_iou_then_centroid_distance=changed,
                    unmatched_modern_best_overlap=geometry['unmatched_modern_best_overlap'],
                    unmatched_legacy_best_overlap=geometry['unmatched_legacy_best_overlap'],
                    warning='Best-overlap associations are diagnostic, not forced one-to-one biological correspondences'))
                report['geometry_artifact'] = case['case_id'] + '/actual.geometry.json'
                report['status'] = 'comparison_ready'
            except Exception as error:
                report['status'] = 'failed'
                report['error'] = f'{type(error).__name__}: {error}'
            finally:
                report['case_wall_seconds'] = time.perf_counter() - case_started
                finalize_case(report, case_dir, scratch, prediction, bool(args.replay_predictions))
                save(output / 'summary.json', summary(manifest, reports, metadata))
                print(json.dumps({'case_id': case['case_id'], 'status': report['status'],
                                  'seconds': round(report['case_wall_seconds'], 3),
                                  'exact_raster_and_measurements_equal': report.get('comparison', {}).get('exact_raster_and_measurements_equal')}), flush=True)
    except Exception as error:
        metadata['setup_or_run_error'] = f'{type(error).__name__}: {error}'
        for report in reports:
            if report['status'] == 'not_run':
                report['status'] = 'blocked'
                report['error'] = metadata['setup_or_run_error']
    metadata['total_wall_seconds'] = time.perf_counter() - start
    try:
        # Summary links to this durable manifest; excluding summary prevents a
        # circular checksum and leaves every progress summary incomplete.
        save(output / 'artifact-manifest.json', {str(p.relative_to(output)): digest(p)
             for p in sorted(output.rglob('*')) if p.is_file() and 'dependencies' not in p.parts
             and p.name not in ('summary.json', 'artifact-manifest.json')})
        metadata['artifact_manifest_sha256'] = digest(output / 'artifact-manifest.json')
        metadata['evidence_manifest_committed'] = True
    except Exception as error:
        metadata['setup_or_run_error'] = f'Evidence manifest failure: {type(error).__name__}: {error}'
    result = summary(manifest, reports, metadata)
    save(output / 'summary.json', result)
    if not result['run_completed']:
        print('INCOMPLETE or development subset: inspect summary.json; no native all40 pass claimed', flush=True)
        return 1
    print('COMPLETE40: execution coverage only; inspect exact-raster flags and per-cell geometry; scientific equivalence NOT established', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
