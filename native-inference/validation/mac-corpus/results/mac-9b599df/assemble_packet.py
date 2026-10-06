#!/usr/bin/env python3
"""Assemble portable evidence from the immutable original native-Mac artifact.

No inference, reference regeneration, thresholds, or external writes are performed.
Use --artifact ZIP and --repository ROOT for reproduction into this directory.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import statistics
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent
SOURCE = '9b599df1b8c67977228bc50104f44280047c4154'
ZIP_SHA = '678f2f005f2975e8269cdb16d8eb853de05efc401f0d3aada8472f500808d95d'
PREFIX = 'target/mac-corpus-results/'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--repository', type=Path, required=True)
    args = parser.parse_args()
    raw = args.artifact.read_bytes()
    assert len(raw) == 6171926 and sha(raw) == ZIP_SHA
    original = ROOT / 'original'
    original.mkdir(exist_ok=True)
    (original / 'gat-native-mac-official40-corpus.zip').write_bytes(raw)
    with zipfile.ZipFile(args.artifact) as archive:
        assert archive.testzip() is None
        infos = archive.infolist()
        names = [i.filename for i in infos]
        assert len(names) == len(set(names)) == 413
        assert all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts for n in names)
        members = [{'path': i.filename, 'bytes': i.file_size, 'compressed_bytes': i.compress_size,
                    'crc32': f'{i.CRC:08x}', 'sha256': sha(archive.read(i.filename))} for i in sorted(infos, key=lambda i: i.filename)]
        save(original / 'zip-member-manifest.json', dict(archive='gat-native-mac-official40-corpus.zip',
              sha256=ZIP_SHA, bytes=len(raw), member_count=413, duplicate_paths=False, safe_relative_paths=True,
              crc_verified=True, members=members))
        s = json.loads(archive.read(PREFIX + 'summary.json'))
        (original / 'summary.json').write_bytes(archive.read(PREFIX + 'summary.json'))
        (original / 'preparation.json').write_bytes(archive.read('target/mac-corpus-prepared/preparation.json'))
        (original / 'artifact-manifest.json').write_bytes(archive.read(PREFIX + 'artifact-manifest.json'))
        for name in ('frozen-manifest.json', 'dependencies.json'):
            code = subprocess.run(['git', '-C', str(args.repository), 'show',
                    SOURCE + ':native-inference/validation/mac-corpus/' + name], capture_output=True, check=True).stdout
            expected = s['metadata']['frozen_manifest_sha256' if name == 'frozen-manifest.json' else 'dependencies_manifest_sha256']
            assert sha(code) == expected
            (original / name).write_bytes(code)
        frozen = json.loads((original / 'frozen-manifest.json').read_text())
        assert s['metadata']['checkout_commit'] == SOURCE
        assert s['native_all40_completed'] and s['run_completed'] and s['metadata']['evidence_manifest_committed']
        assert s['compared_cases'] == 40 and not s['scientific_equivalence_established']
        assert {c['case_id'] for c in s['cases']} == {c['case_id'] for c in frozen['cases']}
        artifact_manifest = json.loads((original / 'artifact-manifest.json').read_text())
        assert sha((original / 'artifact-manifest.json').read_bytes()) == s['metadata']['artifact_manifest_sha256']
        for relative, expected in artifact_manifest.items():
            assert sha(archive.read(PREFIX + relative)) == expected, relative
        rows = []
        for case in s['cases']:
            name = case['case_id']
            assert json.loads(archive.read(PREFIX + name + '/case.json')) == case
            for filename, expected in case['artifacts_sha256'].items():
                assert sha(archive.read(PREFIX + name + '/' + filename)) == expected
            geometry = json.loads(archive.read(PREFIX + name + '/actual.geometry.json'))
            metadata, compare, gs = case['metadata'], case['comparison'], case['geometry_summary']
            assert geometry['modern_count'] == geometry['legacy_count']
            assert gs['winner_centers_equal'] and compare['exact_candidate_count_equal']
            rows.append(dict(case_id=name, model=metadata['model'], stain=metadata['stain'],
                source_path=metadata['source']['source_path'], width_px=metadata['width'], height_px=metadata['height'],
                source_sha256=metadata['source']['source_sha256'], input_sha256=metadata['input_sha256'],
                model_sha256=frozen['models'][metadata['model']]['sha256'],
                duplicate_test_case_ids=';'.join(metadata['same_test_input_case_ids']),
                overlapping_train_case_ids=';'.join(metadata['same_train_input_case_ids']),
                candidates_mac=compare['actual_modern']['modern_candidates'], candidates_legacy=compare['archived_legacy']['legacy_candidates'],
                objects_mac=geometry['modern_count'], objects_legacy=geometry['legacy_count'],
                count_equal=compare['exact_count_equal'], winner_centers_equal=gs['winner_centers_equal'],
                raw_label_hash_equal=compare['exact_raw_label_ids_and_pixels_equal'],
                canonical_raster_hash_equal=compare['exact_identity_insensitive_raster_equal'],
                canonical_measurement_hash_equal=compare['exact_canonical_measurements_equal'],
                strict_quantized_outlines_equal=gs['strict_quantized_outlines_equal'],
                foreground_union_changed_pixels=gs['different_foreground_pixels'],
                foreground_union_iou=gs['foreground_iou'],
                min_matched_independent_polygon_iou=gs['matched_center_min_independent_polygon_iou'],
                original_exclusive_canonical_changed_pixels=compare['original_exclusive_label_difference_count'],
                original_exclusive_changed_count_available=compare['original_exclusive_label_difference_count_available'],
                complete_legacy_paint_order_available=compare['legacy_composite_available'],
                changed_outline_objects=gs['outlines_with_changed_vertices'], changed_outline_vertices=gs['changed_outline_vertices'],
                max_vertex_coordinate_delta_px=gs['max_abs_vertex_coordinate_delta_px'],
                max_vertex_euclidean_delta_px=gs['max_euclidean_vertex_delta_px'],
                cold_cpu_worker_seconds=case['cold_worker_process_end_to_end_seconds'],
                geometry_subprocess_seconds=case['geometry_process_end_to_end_seconds'],
                modern_tensor_sha256=case['modern_tensor_sha256'],
                case_member=PREFIX + name + '/case.json', geometry_member=PREFIX + name + '/actual.geometry.json',
                outlier_member=PREFIX + name + '/outliers.json'))
        outlier_id = 'neuron_test_widefield_9'
        for name in ('case.json', 'actual.geometry.json', 'outliers.json'):
            (original / ('outlier-' + name)).write_bytes(archive.read(PREFIX + outlier_id + '/' + name))
        cold = [r['cold_cpu_worker_seconds'] for r in rows]
        geo = [r['geometry_subprocess_seconds'] for r in rows]
        id_only = [r['case_id'] for r in rows if not r['raw_label_hash_equal'] and r['canonical_raster_hash_equal'] and r['canonical_measurement_hash_equal']]
        assert id_only == ['neuron_test_widefield_6', 'neuron_test_widefield_3']
        assert sum(r['canonical_raster_hash_equal'] for r in rows) == 39
        assert sum(r['raw_label_hash_equal'] for r in rows) == 37
        assert sum(r['strict_quantized_outlines_equal'] for r in rows) == 8
        assert sum(r['objects_mac'] for r in rows) == 4472
        summary = dict(schema=1, source_commit=SOURCE,
            run_url='https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37381573321',
            job_url='https://github.com/justinvassantachart/GutAnalysisToolbox/actions/runs/37381573321/job/112004603172',
            source_url='https://github.com/justinvassantachart/GutAnalysisToolbox/commit/' + SOURCE,
            coverage_completed=True, native_apple_silicon_execution_verified=True,
            scientific_equivalence_established=False, biological_accuracy_against_manual_ground_truth_assessed=False,
            cases=rows, case_count=40, unique_pixel_inputs=39, test_inputs_also_in_training=1,
            input_pixels_including_duplicate=26030351,
            independence_note=frozen['independence_note'], stains=frozen['stains'],
            comparison=dict(matching_candidate_counts=40,matching_object_counts=40,matching_winner_centers=40,
                detections_mac=4472,detections_legacy=4472,
                detections_note='Summed case outputs, not unique independent biological cells.',
                exact_canonical_raster_and_measurement_cases=39,exact_raw_label_cases=37,
                label_id_only_case_ids=id_only,strict_complete_outline_exact_cases=8,
                cases_with_subpixel_outline_differences=32, changed_outline_objects=162,changed_outline_vertices=164,
                unmatched_centers_modern=0,unmatched_centers_legacy=0,
                raster_outlier_case_ids=[outlier_id],
                subtype_exact_canonical_raster_and_measurement_cases=15,subtype_case_count=15,
                max_coordinate_delta_px=max(r['max_vertex_coordinate_delta_px'] for r in rows),
                max_euclidean_vertex_delta_px=max(r['max_vertex_euclidean_delta_px'] for r in rows),
                max_delta_scope='Exact-center matched polygons; all winner centers matched in this run.'),
            raster_outlier=dict(case_id=outlier_id,winning_center_xy_px=[606.5,510.5],
                independent_polygon_area_legacy=691,independent_polygon_area_mac=690,
                independent_polygon_changed_pixels=1,foreground_union_changed_pixels=1,
                independent_polygon_iou=690/691,centroid_shift_px=0.018732395302507927,
                original_exclusive_label_changed_pixel_count=None,
                limitation='Legacy winner paint order is unavailable for this image. Independent polygon/union pixel changes are not an original exclusive-label differing-pixel count.',
                original_outlier_member=PREFIX+outlier_id+'/outliers.json'),
            tensor_numerical_parity_performed=False,
            tensor_limit='Most original TF1 probability/distance arrays were not retained; this run makes no tensor-tolerance comparison.',
            runner=s['metadata']['runner'], reference_runtime=s['metadata']['reference_runtime'],
            reference_platform=s['metadata']['reference_platform'],
            timing_seconds=dict(cold_cpu_worker_min=min(cold),cold_cpu_worker_median=statistics.median(cold),
                cold_cpu_worker_max=max(cold),cold_cpu_worker_sum=sum(cold),
                geometry_subprocess_sum=sum(geo),geometry_dependency_setup=s['metadata']['geometry_dependency_verification_and_compilation_seconds'],
                runner_total=s['metadata']['total_wall_seconds'],
                initial_dataset_model_download_conversion_and_build=None,
                initial_setup_note='These workflow steps precede the timed runner; their individual durations are not recorded in this artifact.',
                sample_count_per_case=1,warmup_runs=0,
                scope='CPU worker includes fresh JVM/model loading, normalization, tiling, inference and GATO write; geometry includes NMS, measurements and compact outputs.',
                gpu_comparison_performed=False,gpu_speed_multiplier=None),
            resource_policy=dict(serial_cases=True,max_java_heap='3GiB',tf_intra_op_threads=2,tf_inter_op_threads=1,omp_threads=2,
                worker_scratch_cleaned_for_all_cases=all(c['raw_modern_tensor_retained_in_report'] is False for c in s['cases'])),
            protocol=dict(probability_hu=0.5,probability_subtype=0.4,nms=0.3,excluded_boundary_px=2,requested_tiles=4,
                preprocessing='Unchanged production CSBDeep normalization/tiling; no additional image resizing/cropping.',
                exact_conversion=frozen['conversion'], nms_commit='aff59dbd3cdf88dfa567d4dd562eab943bf4f99b'),
            retention=dict(original_archive='original/gat-native-mac-official40-corpus.zip',archive_sha256=ZIP_SHA,
                archive_bytes=len(raw),archive_members=413,member_manifest='original/zip-member-manifest.json',
                all_case_geometry_and_outliers='All40 original case.json, actual.geometry.json, outliers.json, compact masks/outlines and logs remain byte-preserved as the indicated ZIP members.',
                expanded_original_reports='original/summary.json and original/preparation.json'))
        save(ROOT/'summary.json',summary)
        print(json.dumps({k:summary[k] for k in ('case_count','unique_pixel_inputs','comparison','timing_seconds')}))

if __name__ == '__main__':
    main()
