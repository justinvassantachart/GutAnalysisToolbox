#!/usr/bin/env python3
"""Add an isolated oneDNN-off control to an already completed sensitivity packet."""
import argparse
import csv
import json
import os
from pathlib import Path
import subprocess

from run_corpus import verify_input
from run_sensitivity import sha256, scores


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--models', type=Path, required=True)
    p.add_argument('--java', default='java')
    p.add_argument('--modern-classpath', required=True)
    p.add_argument('--legacy-classpath', required=True)
    p.add_argument('--comparator-classpath', required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    output = args.output.resolve()
    packet_path = output / 'sensitivity.json'
    packet = json.loads(packet_path.read_text())
    if not packet.get('complete'): raise ValueError('Initial sensitivity packet must be complete')
    with args.manifest.open() as f:
        selected = [r for r in csv.DictReader(f, delimiter='\t') if r['case_id'] == packet['case_id']]
    if len(selected) != 1: raise ValueError('Case must occur once')
    row = selected[0]
    verify_input(row)
    if row['input_sha256'] != packet['input_sha256']: raise ValueError('Input identity changed')
    model = args.models / ('2D_enteric_neuron_v4_1.zip' if row['model'] == 'neuron' else '2D_enteric_neuron_subtype_v4.zip')
    if sha256(model) != packet['model_sha256']: raise ValueError('Model identity changed')
    label = 'single-thread-onednn-off'
    if any(r['variant'] == label for r in packet['runs']): raise ValueError('Control is already present')
    probes = [tuple(map(int, k.split(','))) for k in packet['baseline_retained']['modern']['probability_probes']]
    paths = {}
    packet['complete'] = False
    packet_path.write_text(json.dumps(packet, indent=2))
    for engine in ('modern', 'legacy'):
        target = output / (label + '-' + engine + '.bin')
        if target.exists(): raise ValueError('Control output already exists')
        env = dict(os.environ, TF_NUM_INTRAOP_THREADS='1', TF_NUM_INTEROP_THREADS='1', OMP_NUM_THREADS='1', TF_ENABLE_ONEDNN_OPTS='0')
        with (output / (label + '-' + engine + '.log')).open('w') as log:
            subprocess.run([args.java, '-XX:-UsePerfData', '-Xmx3g', '-cp', getattr(args, engine + '_classpath'),
                            f'org.gatanalysis.inference.{engine.capitalize()}SensitivityMain', str(model), row['input_path'],
                            str(target), row['tiles'], 'single-thread'], env=env, stdout=log, stderr=subprocess.STDOUT,
                           check=True, timeout=900)
        digest = sha256(target)
        record = {'variant': label, 'engine': engine, 'mode': 'single-thread', 'tensor_sha256': digest,
                  'matches_retained_same_engine_hash': digest == packet['baseline_retained'][engine]['tensor_sha256'],
                  'probability_probes': scores(target, probes), 'requested_threading': {'intra_op': 1, 'inter_op': 1, 'omp': 1},
                  'thread_counts_explicit_in_session_config': True, 'meta_optimizer_disabled': False,
                  'oneDNN_disabled_environment': True, 'oneDNN_environment_value': '0'}
        packet['runs'].append(record); paths[engine] = target
        packet_path.write_text(json.dumps(packet, indent=2)); print(json.dumps(record), flush=True)
    for comparison, legacy in [(label + '-cross-engine', paths['legacy']),
                                (label + '-modern-vs-retained-legacy', Path(row['legacy_path']))]:
        run = subprocess.run([args.java, '-XX:-UsePerfData', '-Xmx3g', '-Djava.awt.headless=true', '-cp', args.comparator_classpath,
                              'CorpusNmsComparison', str(paths['modern']), str(legacy), str(packet['probability_threshold']),
                              str(packet['nms_threshold']), str(output / 'outlines' / comparison)], capture_output=True,
                             text=True, check=True, timeout=900)
        records = [line for line in run.stdout.splitlines() if line.startswith('{')]
        if len(records) != 1: raise ValueError('Expected one comparator JSON record')
        packet['comparisons'][comparison] = json.loads(records[0])
        packet_path.write_text(json.dumps(packet, indent=2)); print('COMPARED ' + comparison, flush=True)
    packet['complete'] = True
    packet['isolated_onednn_control_complete'] = True
    packet_path.write_text(json.dumps(packet, indent=2))
    print('COMPLETE isolated oneDNN control', flush=True)


if __name__ == '__main__':
    main()
