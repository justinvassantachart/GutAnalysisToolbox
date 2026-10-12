#!/usr/bin/env python3
"""Compare real Hu+marker/no-Hu menus, actual channel calls and reopened outputs.

No NMS, command-boundary or source-only pass can satisfy this gate. ROI vertex
rounding differences remain exact failures by default; any explicit tolerance
is recorded and applies only to floating vertex coordinates, never labels,
counts, names, order, positions, settings or exported measurements.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import zipfile
from pathlib import Path

import audit_sources

HERE = Path(__file__).resolve().parent
SCOPE = 'real-top-menu-marker-whole-workflow'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def load_side(installation, variant):
    root = installation / variant
    launcher = json.loads((root / 'launcher.json').read_text())
    report = json.loads((root / 'evidence/report.json').read_text())
    config = json.loads((root / 'config.json').read_text())
    family = config.get('family')
    require(family in ('hu-one-marker','no-hu-one-marker') and report.get('family') == family, 'Wrong marker family')
    has_hu = family == 'hu-one-marker'
    immutable = json.loads((installation / 'immutability.json').read_text())
    require(immutable.get('status') == 'PASS_RUNTIME_IMMUTABILITY', 'Runtime immutability not established')
    for row in (launcher, report):
        require(row.get('status') == 'PASS_TOP_MENU_WORKFLOW_SCOPE' and row.get('variant') == variant,
                'Incomplete or wrong variant top-menu evidence')
    require(report.get('scope') == SCOPE and report.get('whole_analysis_macro_executed') is True,
            'Wrong scope or whole analysis macro not completed')
    require(launcher.get('execution', {}).get('exit_code') == 0 and not launcher['execution'].get('resource_stop_reason'),
            'Unsuccessful bounded process')
    fixture_manifest = json.loads((audit_sources.ROOT / 'native-inference/validation/cross-platform/fixture-manifest.json').read_text())
    require(report.get('fixture_sha256') == fixture_manifest['source']['sha256'], 'Wrong public fixture')
    for model in fixture_manifest['cases']:
        require(launcher.get('models', {}).get(model['model']) == model['model_sha256'], 'Wrong model identity')
    fiji = root / 'Fiji'
    require('-Djava.system.class.loader=BaselineUrlClassLoader' in launcher.get('command', [])
            and launcher.get('url_loader_sha256') == sha(fiji / 'jars/LegacyValidationUrlLoader.jar'),
            'Proven original URL system loader not established')
    require(launcher.get('harness_sha256') == sha(fiji / 'plugins/LegacyMacroMarkerMenuProbe.jar'), 'Actual validation harness bytes changed')
    target = 'Features.Macros.LegacyMacroStarDist' if variant == 'native' else 'de.csbdresden.stardist.StarDist2D'
    owner = fiji / 'plugins/GAT_MacroFork.jar' if variant == 'native' else next(fiji.rglob('StarDist_-0.3.0.jar'))
    with zipfile.ZipFile(owner) as jar:
        class_sha = hashlib.sha256(jar.read(target.replace('.', '/') + '.class')).hexdigest()
    require(report.get('target_class', {}).get('name') == target
            and report['target_class'].get('class_sha256') == class_sha, 'Wrong actual command class bytes')
    if variant == 'native':
        require(launcher.get('candidate_sha256') == sha(owner), 'Wrong candidate plugin identity')
    source = Path(config['source_script'])
    manifest = json.loads((HERE / 'source-manifest.json').read_text())
    script = '_Analyse Neuron (Multi-channel).ijm' if has_hu else '_Analyse Neuron (Multi-channel - No Hu).ijm'
    row = next(r for r in manifest['files'] if r['path'] == script)
    reference = (audit_sources.ROOT / row['path']).read_bytes()
    require(hashlib.sha256(reference).hexdigest() == row['sha256'], 'Pinned reference source changed')
    expected = reference if variant == 'original' else audit_sources.expected_overlay(row['path'], reference, [r['path'] for r in manifest['files']])
    require(source.read_bytes() == expected and report.get('source_script_sha256') == sha(source)
            and launcher.get('source_sha256') == sha(source), 'Actual installed macro body changed')
    menu = ' Analyse Neuron (Multi-channel)' if has_hu else ' Analyse Neuron (Multi-channel - No Hu)'
    menu += ' [MacroFork]' if variant == 'native' else ''
    require(report.get('invoked_menu') == menu and menu in report.get('discovered_marker_menus', []) and report.get('menu_binding'),
            'Actual registered menu discovery/dispatch absent')
    expected_calls = 2 if has_hu else 1
    require(report.get('errors') == [] and report.get('matching_module_executions') == expected_calls,
            'Runtime error or wrong model execution count')
    calls = report.get('actual_inference_calls', [])
    require(len(calls) == expected_calls, 'Actual command settings missing')
    models = ['2D_enteric_neuron_v4_1.zip','2D_enteric_neuron_subtype_v4.zip'] if has_hu else ['2D_enteric_neuron_subtype_v4.zip']
    for call, model in zip(calls, models):
        expected_args = {'normalizeInput':'true','percentileBottom':'1.0','percentileTop':'99.8',
                         'probThresh':'0.5' if model == models[0] and has_hu else '0.4', 'nmsThresh':'0.3',
                         'nTiles':'4','excludeBoundary':'2','outputType':'Label Image','roiPosition':'Automatic',
                         'verbose':'false','showCsbdeepProgress':'false','showProbAndDist':'false'}
        require(Path(call.get('modelFile','')).name == model, 'Wrong model or channel execution order')
        for key, value in expected_args.items():require(call.get(key) == value, 'Unexpected original parameter: '+key)
    workers = report.get('worker_processes', {})
    require(len(workers) == (expected_calls if variant == 'native' else 0), 'Native process isolation/observation mismatch')
    if variant == 'native':
        require(report.get('backend_property') == 'gat.stardist.backend' and report.get('backend_value') == 'native', 'Native branch not established')
        for model in models:
            require(sum('org.gatanalysis.inference.NativeInferenceMain' in c and config['native_worker'] in c
                        and model in c and c.endswith(' 4') for c in workers.values()) == 1, 'Wrong worker process/model/tiles')
    reviews = report.get('reviews', {})
    markers = ['Hu','Marker'] if has_hu else ['Marker']
    require(list(reviews) == markers, 'Wrong actual marker review order')
    for marker in markers:
        before, after = reviews[marker].get('before',[]), reviews[marker].get('after',[])
        require(len(before)>0 and before==after, 'Vacuous or changed marker review')
    require(report.get('scenario') == config.get('scenario') == 'unchanged', 'Unknown marker review scenario')
    require(report.get('input',{}).get('channels')==2, 'Distinguishable marker channel fixture absent')
    dialogs = report.get('dialogs', [])
    require(not any(r.get('action') == 'UNKNOWN_LEFT_UNTOUCHED' for r in dialogs), 'Unknown dialog encountered')
    require([r.get('marker') for r in dialogs if r.get('action')=='unchanged marker review']==markers
            and sum(r.get('action')=='acknowledge exact original completion exit' for r in dialogs)==1,
            'Missing actual reviews or source completion')
    if not has_hu:require(sum(r.get('action')=='accept exact original no-Hu defaults' for r in dialogs)==1,'No-Hu settings dialog missing')
    exports = report.get('exports', [])
    expected_names = {'Marker_unmodified_ROIs_public_neurons_1.zip','Marker_ROIs_public_neurons_1.zip',
                      'Analysis_public_neurons_1_cell_counts.csv','MAX_public_neurons_1.tif','Log.txt'}
    if has_hu:expected_names.update({'Hu_unmodified_ROIs_public_neurons_1.zip','Hu_ROIs_public_neurons_1.zip','Hu_label_MAX_public_neurons_1.tif'})
    require({r.get('path') for r in exports}==expected_names and len(exports)==len(expected_names), 'Export set incomplete/duplicated')
    directory = Path(config['input']).parent/'Analysis/public_neurons_1'
    for exported in exports:
        file=directory/exported['path']
        require(file.is_file() and file.stat().st_size==exported['bytes'] and sha(file)==exported['sha256'], 'Saved export bytes changed')
        if file.suffix=='.zip':
            marker='Hu' if file.name.startswith('Hu_') else 'Marker'
            require(len(exported.get('reopened_rois',[]))==len(reviews[marker]['after']), 'Saved/review ROI count differs')
        elif file.suffix=='.csv':
            require(exported.get('reopened_csv')==file.read_text(), 'CSV roundtrip evidence differs')
            rows=list(csv.DictReader(io.StringIO(file.read_text())))
            require(len(rows)==1 and float(rows[0]['Marker'])==len(reviews['Marker']['after']), 'CSV marker count differs')
            if has_hu:require(float(rows[0]['Total Hu'])==len(reviews['Hu']['after']), 'CSV Hu count differs')
        elif file.suffix=='.tif':require(exported.get('reopened_image',{}).get('pixel_f32be_sha256'), 'Saved image evidence missing')
    return report


def roi_difference(a, b, atol):
    require(len(a) == len(b), 'ROI counts differ')
    maximum = 0.0
    for left, right in zip(a, b):
        require(left[:6] == right[:6], 'ROI names/types/order/positions differ')
        require(len(left[6]) == len(right[6]), 'ROI vertex counts differ')
        for lp, rp in zip(left[6], right[6]):
            require(len(lp) == len(rp) == 2, 'Invalid ROI point')
            for x, y in zip(lp, rp):
                require(math.isfinite(x) and math.isfinite(y), 'Nonfinite ROI vertex')
                maximum = max(maximum, abs(x - y))
    return maximum, maximum <= atol


def compare(installation, atol=0, original_installation=None):
    result = {'schema_version': 1, 'scope': SCOPE, 'status': 'FAIL_OR_INCOMPLETE', 'roi_vertex_atol': atol,
              'mismatches': [], 'max_roi_vertex_abs_difference': 0.0,
              'native_installation': str(installation.resolve()),
              'original_installation': str((original_installation or installation).resolve())}
    try:
        require(math.isfinite(atol) and atol >= 0, 'Invalid explicit ROI tolerance')
        a, b = load_side(original_installation or installation, 'original'), load_side(installation, 'native')
        result['scenario'] = a['scenario']
        for key in ('family', 'scenario', 'parameters', 'input', 'fixture_sha256'):
            if a.get(key) != b.get(key): result['mismatches'].append(key)
        require(list(a['reviews'])==list(b['reviews']), 'Paired marker order differs')
        for marker in a['reviews']:
            for phase in ('before','after'):
                difference, passed=roi_difference(a['reviews'][marker][phase],b['reviews'][marker][phase],atol)
                result['max_roi_vertex_abs_difference']=max(result['max_roi_vertex_abs_difference'],difference)
                if not passed:result['mismatches'].append(marker+' review '+phase)
        exports = {r['path']: r for r in b['exports']}
        for left in a['exports']:
            name = left['path']; right = exports[name]
            if name.endswith('.zip'):
                difference, passed = roi_difference(left['reopened_rois'], right['reopened_rois'], atol)
                result['max_roi_vertex_abs_difference'] = max(result['max_roi_vertex_abs_difference'], difference)
                if not passed: result['mismatches'].append(name)
            elif name.endswith('.csv'):
                if left['reopened_csv'] != right['reopened_csv']: result['mismatches'].append(name)
            elif name.endswith(('.tif', '.jpg')):
                if left['reopened_image'] != right['reopened_image']: result['mismatches'].append(name)
        result['status'] = 'PASS_PAIRED_TOP_MENU_WORKFLOW_SCOPE' if not result['mismatches'] else 'FAIL_TOP_MENU_DIFFERENCES'
    except (ValueError, KeyError, TypeError, OSError, StopIteration, zipfile.BadZipFile) as error:
        result['error'] = str(error)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--installation', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    p.add_argument('--roi-atol', type=float, default=0)
    p.add_argument('--original-installation', type=Path, help='Reuse a separately recorded successful original control; both roots remain explicit')
    a = p.parse_args()
    if a.output.exists(): p.error('Existing comparisons are never overwritten')
    result = compare(a.installation, a.roi_atol, a.original_installation)
    a.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(result['status'])
    return 0 if result['status'].startswith('PASS_') else 1

if __name__ == '__main__':
    raise SystemExit(main())
