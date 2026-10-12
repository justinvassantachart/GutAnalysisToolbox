#!/usr/bin/env python3
"""Independent exact-blob audit of the legacy source and candidate macro overlay.

This does not import the overlay generator and is not runtime parity evidence.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STAR_SITES = {
    '_Analyse Neurons.ijm': 1,
    '_Analyse Neuron (Multi-channel).ijm': 1,
    '_Analyse Neuron (Multi-channel - No Hu).ijm': 1,
    '_Analyse Glia (Sox10 only).ijm': 1,
    'Calcium imaging/_Calcium_imaging_analysis.ijm': 1,
    'Tools/_Test_neuron_probability.ijm': 1,
    'Tools/_Test_neuron_rescaling.ijm': 1,
    'Tools/_Test_neuron_rescaling_advanced.ijm': 1,
}
ALIGN_SITES = {'Calcium imaging/_Align_stack.ijm': 2,
               'Calcium imaging/_Align_stack_batch.ijm': 1}
SETTINGS_SITES = {
    '_Analyse Neurons.ijm', '_Analyse Neuron (Multi-channel).ijm',
    '_Analyse Neuron (Multi-channel - No Hu).ijm',
    'Tools/_Test_neuron_probability.ijm', 'Tools/_Test_neuron_rescaling.ijm',
    'Tools/_Test_neuron_rescaling_advanced.ijm', 'Tools/commands/check_plugin.ijm',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def destination(name):
    p = Path(name)
    return 'scripts/GAT MacroFork/' + str(p.with_name(p.stem + ' [MacroFork]' + p.suffix))


def expected_overlay(name, data, names):
    """Reconstruct a narrow independent allowlist, retaining every other byte."""
    output, star, alignment = [], 0, 0
    for line in data.splitlines(keepends=True):
        if not line.lstrip().startswith((b'//', b'#')):
            target = b'de.csbdresden.stardist.StarDist2D]'
            if target in line:
                if not line.lstrip().startswith(b'run("Command From Macro",'):
                    raise ValueError('Unexpected StarDist caller: ' + name)
                star += line.count(target)
                line = line.replace(target, b'Features.Macros.LegacyMacroStarDist]')
            target = b'run("Align slices in stack...",'
            if target in line:
                match = re.fullmatch(rb'(\s*)run\("Align slices in stack\.\.\.",(.*)\);(\r?\n?)', line)
                if not match or b'gat_alignment_status' in data:
                    raise ValueError('Unexpected alignment statement or variable collision: ' + name)
                alignment += 1
                line = (match[1] + b'gat_alignment_status=call("Features.Macros.LegacyTemplateMatching.run",'
                        + match[2] + b'); if(gat_alignment_status!="GAT_ALIGNMENT_OK") '
                        + b'exit("MacroFork alignment failed: "+gat_alignment_status);' + match[3])
        output.append(line)
    if star != STAR_SITES.get(name, 0) or alignment != ALIGN_SITES.get(name, 0):
        raise ValueError('Native command site count changed: ' + name)
    result = b''.join(output)
    old = b'run("Results... ", "open="+gat_settings_path);'
    if result.count(old) != (1 if name in SETTINGS_SITES else 0):
        raise ValueError('Unexpected settings option path site: ' + name)
    result = result.replace(old, b'run("Results... ", "open=["+gat_settings_path+"]");')
    result = result.replace(b'"GAT"', b'"GAT MacroFork"')
    for source in sorted(names):
        old = Path(source).name
        new = Path(destination(source)).name
        result = result.replace(old.encode(), new.encode())
    return result.replace(b'" Analyse Neurons"', b'" Analyse Neurons [MacroFork]"')


def audit(root, manifest, overlay=None, settings=None):
    rows, names = [], [f['path'] for f in manifest['files']]
    if len(names) != 47 or len(set(names)) != len(names):
        raise ValueError('Reference must contain the 47 distinct pinned legacy scripts')
    reader = zipfile.ZipFile(overlay) if overlay else None
    try:
        if reader and len(reader.namelist()) != len(set(reader.namelist())):
            raise ValueError('Overlay contains duplicate ZIP members')
        for entry in manifest['files']:
            name = entry['path']
            data = (root / name).read_bytes()
            reference = subprocess.check_output(['git', 'show', manifest['source_revision'] + ':' + name], cwd=root)
            blob = subprocess.check_output(['git', 'rev-parse', manifest['source_revision'] + ':' + name], cwd=root, text=True).strip()
            valid = (data == reference and sha(data) == entry['sha256'] and len(data) == entry['bytes']
                     and blob == entry['git_blob'])
            row = {'path': name, 'source_contract_pass': valid, 'sha256': sha(data)}
            if reader:
                expected = expected_overlay(name, reference, names)
                if name == 'Tools/commands/gat_settings.ijm' and settings:
                    expected = Path(settings).read_bytes()
                actual = reader.read(destination(name))
                row['overlay_contract_pass'] = expected == actual
                row['overlay_sha256'] = sha(actual)
            rows.append(row)
    finally:
        if reader:
            reader.close()
    passed = all(r['source_contract_pass'] and r.get('overlay_contract_pass', True) for r in rows)
    return {'schema_version': 1, 'scope': 'exact-source-and-allowlisted-overlay-only',
            'source_revision': manifest['source_revision'], 'runtime_tested': False,
            'status': 'PASS_SOURCE_CONTRACT' if passed else 'FAIL_SOURCE_CONTRACT', 'files': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--manifest', type=Path, default=HERE / 'source-manifest.json')
    parser.add_argument('--overlay', type=Path)
    parser.add_argument('--settings', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root, json.loads(args.manifest.read_text()), args.overlay, args.settings)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'], len(result['files']), 'scripts; runtime untested')
    return 0 if result['status'] == 'PASS_SOURCE_CONTRACT' else 1


if __name__ == '__main__':
    raise SystemExit(main())
