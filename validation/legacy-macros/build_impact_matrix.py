#!/usr/bin/env python3
"""Classify every preserved macro by exact, independently audited fork changes.

This is an impact/coverage contract, not a test-result generator. Unchanged
scientific branches are not scheduled as new standalone regression projects.
"""
import argparse
import json
import re
from pathlib import Path
import zipfile
import audit_sources

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def matrix(overlay):
    manifest = json.loads((HERE / 'source-manifest.json').read_text())
    audit = audit_sources.audit(ROOT, manifest, overlay)
    if audit['status'] != 'PASS_SOURCE_CONTRACT':
        raise ValueError('Cannot reason about impact when exact source audit fails')
    names = [r['path'] for r in manifest['files']]
    rows = []
    with zipfile.ZipFile(overlay) as archive:
        for row in manifest['files']:
            name = row['path']; source = (ROOT / name).read_bytes()
            destination = audit_sources.destination(name); generated = archive.read(destination)
            stardist = audit_sources.STAR_SITES.get(name, 0)
            alignment = audit_sources.ALIGN_SITES.get(name, 0)
            installation = source.count(b'"GAT"')
            refs = [n for n in names if Path(n).name.encode() in source]
            batch = source.count(b'" Analyse Neurons"')
            batch_dispatch = sum(line.lstrip().startswith(b'run(" Analyse Neurons",') for line in source.splitlines())
            item = {'source': name, 'source_sha256': row['sha256'], 'destination': destination,
                    'destination_sha256': audit_sources.sha(generated), 'filename_namespace_changed': True,
                    'body_identical': source == generated, 'stardist_target_changes': stardist,
                    'alignment_target_changes': alignment, 'alignment_fail_stop_guards': alignment,
                    'settings_option_path_quotes': int(name in audit_sources.SETTINGS_SITES),
                    'installation_path_changes': installation,
                    'batch_menu_changes': batch, 'batch_executable_dispatch_sites': batch_dispatch,
                    'referenced_script_names': refs,
                    'unallowlisted_computation_changes': 0}
            item['required_evidence'] = ['exact-source-overlay-audit', 'namespace-installation-audit']
            if stardist:
                call = next(line.strip() for line in source.decode().splitlines()
                            if line.lstrip().startswith('run("Command From Macro",') and 'de.csbdresden.stardist.StarDist2D]' in line)
                item['actual_original_call_contract'] = {
                    'arguments': dict(re.findall(r"'([A-Za-z][A-Za-z0-9]*)':'([^']*)'", call)),
                    'bridge_process_false': 'process=[false]' in call,
                    'line_sha256': audit_sources.sha(call.encode())}
                item['impact'] = 'native-inference-boundary-and-returned-image-roi-state'
                item['required_evidence'] += ['registered-inference-matrix', 'original-nms-roi-matrix']
                if name in ('_Analyse Neurons.ijm', '_Analyse Neuron (Multi-channel).ijm', '_Analyse Neuron (Multi-channel - No Hu).ijm'):
                    item['required_evidence'] += ['representative-real-top-menu-flow']
                elif name == '_Analyse Glia (Sox10 only).ijm':
                    item['condition'] = 'Automatic biological-model validation requires an actual researcher-selected Sox10 model; default setting is NA. Do not substitute a neuron model.'
                elif name.startswith('Tools/'):
                    item['discharge_rule'] = 'Probability/scale/tile-dependent adapter behavior is covered by executable inference and NMS matrices; unchanged loop/UI/calibration arithmetic is byte-audited, not reimplemented.'
                else:
                    item['discharge_rule'] = 'Changed calcium StarDist boundary uses the same validated original parameter contract; unchanged F/F0, EDF, tracing and CSV computations do not require standalone retesting.'
            elif alignment:
                item['impact'] = 'native-alignment-call-boundary-pixels-ui-and-error-flow'
                item['required_evidence'] += ['registered-alignment-paired-probe', 'alignment-unsupported-input-control']
            elif batch:
                item['impact'] = 'renamed-indirect-neuron-menu-dispatch'
                item['required_evidence'] += ['registered-renamed-neuron-menu', 'batch-command-routing-probe']
            elif source != generated:
                item['impact'] = 'namespace-routing-only'
                item['discharge_rule'] = 'Assert every changed literal resolves to the same exact original/generated helper. The scientific computation bytes are unchanged; representative top-menu execution exercises helper loading.'
            else:
                item['impact'] = 'filename-menu-namespace-only'
                item['discharge_rule'] = 'Verify installation/menu identity; no changed scientific function exists to retest independently.'
            rows.append(item)
    return {'schema_version': 1, 'scope': 'macro-user-workflow-impact-only', 'not_a_runtime_result': True,
            'source_revision': manifest['source_revision'], 'instruction': 'Test workflows if and only if functionality can be affected by fork changes. Do not fix or expand unrelated inherited behavior.',
            'change_totals': {'scripts': len(rows), 'stardist_sites': sum(r['stardist_target_changes'] for r in rows),
                              'alignment_sites': sum(r['alignment_target_changes'] for r in rows),
                              'alignment_fail_stop_guards': sum(r['alignment_fail_stop_guards'] for r in rows),
                              'settings_option_path_quotes': sum(r['settings_option_path_quotes'] for r in rows),
                              'unallowlisted_computation_changes': 0},
            'evidence_contracts': {
                'exact-source-overlay-audit': 'audit_sources.py: exact pre-deletion blobs plus narrow independently reconstructed substitutions',
                'namespace-installation-audit': 'All47 scripts,48 assets and changed helper/menu references present with checked byte identity; actual Fiji discovery where the renamed menu is invoked',
                'registered-inference-matrix': '30 actual original/native Command From Macro model cases on Linux and native Apple Silicon; exact label and quantified ROI comparisons',
                'original-nms-roi-matrix': '720 actual original NMS versus native-adapter NMS pairs; real global ROI Manager, outputs and positions',
                'representative-real-top-menu-flow': 'Unchanged installed original/generated macro invoked by actual discovered menu, real dashboard/review, reopened exports',
                'registered-alignment-paired-probe': 'Actual original IJ.run versus generated call() boundary; independent shift/pixel oracle and visible ordered Results/CSV',
                'alignment-unsupported-input-control': 'Same unsupported32 input must stop cleanly with recorded after-call continuation behavior; no unrelated errors accepted',
                'registered-renamed-neuron-menu': 'Actual Fiji Menus registration and successful renamed top-menu dispatch, not synthetic mapping',
                'batch-command-routing-probe': 'Execute original/generated exact batch command with preserved argument values; namespace audit alone is not marked as executed batch coverage'},
            'explicitly_not_new_standalone_suites': ['unchanged EDF/projection mathematics', 'unchanged spatial analysis mathematics',
                                                   'unchanged CSV merge or export calculations', 'unchanged calcium F/F0 and tracing calculations',
                                                   'inherited bugs outside altered call/namespace boundaries'],
            'scripts': rows}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--overlay', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    a=p.parse_args(); result=matrix(a.overlay)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['change_totals']))

if __name__=='__main__': main()
