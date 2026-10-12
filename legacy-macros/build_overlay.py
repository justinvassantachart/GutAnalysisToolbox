#!/usr/bin/env python3
"""Generate a side-by-side MacroFork script overlay; never change original macros.

Only command targets, fail-stop guards and installation/menu routing may differ. Each input/output
hash and each literal substitution is recorded. Models, preprocessing, CLIJ,
settings values, segmentation thresholds and processing order are not retuned.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FOLDERS = ('Tools', 'Calcium imaging', 'Batch_mode', 'Analysis', 'Spatial Analysis', 'Multiplex')
MENU_SUFFIX = ' [MacroFork]'
NAMESPACE = 'GAT MacroFork'
STAR = b'de.csbdresden.stardist.StarDist2D'
ADAPTER = b'Features.Macros.LegacyMacroStarDist'
ALIGN = b'run("Align slices in stack...",'
ALIGN_ADAPTER = b'gat_alignment_status=call("Features.Macros.LegacyTemplateMatching.run",'
ALIGN_GUARD = b' if(gat_alignment_status!="GAT_ALIGNMENT_OK") exit("MacroFork alignment failed: "+gat_alignment_status);'
SETTINGS_OPEN = b'run("Results... ", "open="+gat_settings_path);'
SETTINGS_QUOTED = b'run("Results... ", "open=["+gat_settings_path+"]");'
SETTINGS_SITES = {
    "_Analyse Neurons.ijm", "_Analyse Neuron (Multi-channel).ijm",
    "_Analyse Neuron (Multi-channel - No Hu).ijm",
    "Tools/_Test_neuron_probability.ijm", "Tools/_Test_neuron_rescaling.ijm",
    "Tools/_Test_neuron_rescaling_advanced.ijm", "Tools/commands/check_plugin.ijm",
}
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
ALIGN_SITES = {'Calcium imaging/_Align_stack.ijm': 2, 'Calcium imaging/_Align_stack_batch.ijm': 1}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_paths(root=ROOT):
    # Git's tracked asset list excludes accidental private/local fixture files.
    raw = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root)
    paths = []
    for name in raw.decode().split('\0'):
        p = Path(name)
        if not name:
            continue
        if (len(p.parts) == 1 and p.suffix == '.ijm') or (p.parts[0] in SOURCE_FOLDERS
                and p.suffix in ('.ijm', '.py', '.jpg')):
            paths.append(p)
    return sorted(paths)


def destination_path(path):
    if path.suffix in ('.ijm', '.py'):
        return path.with_name(path.stem + MENU_SUFFIX + path.suffix)
    return path


def replace_count(data, before, after, changes, kind):
    count = data.count(before)
    if count:
        data = data.replace(before, after)
        changes.append({'kind': kind, 'before': before.decode(), 'after': after.decode(), 'count': count})
    return data


def transform(path, original, paths):
    """Byte-level allowlist: no line-ending/whitespace/scientific rewrites."""
    if path.suffix not in ('.ijm', '.py'):
        return original, []
    data, changes = original, []
    # Preserve comments verbatim, changing actual StarDist run lines only.
    # These audited commands are each a single line. Fail if source shape moves.
    lines = data.splitlines(keepends=True)
    star_count, align_count = 0, 0
    alignment_changes = {}
    for index, line in enumerate(lines):
        if line.lstrip().startswith((b'//', b'#')):
            continue
        if STAR + b']' in line:
            if not line.lstrip().startswith(b'run("Command From Macro",'):
                raise ValueError('Unaudited StarDist command form: ' + str(path))
            lines[index] = line.replace(STAR + b']', ADAPTER + b']')
            star_count += line.count(STAR + b']')
        if ALIGN in line:
            statement = line.strip()
            if not statement.startswith(ALIGN) or not statement.endswith(b');') or b'gat_alignment_status' in original:
                raise ValueError('Unaudited alignment command form or status variable collision: ' + str(path))
            guarded = statement.replace(ALIGN, ALIGN_ADAPTER, 1) + ALIGN_GUARD
            lines[index] = lines[index].replace(statement, guarded, 1)
            alignment_changes[statement] = alignment_changes.get(statement, 0) + 1
            align_count += line.count(ALIGN)
    name = path.as_posix()
    if star_count != STAR_SITES.get(name, 0) or align_count != ALIGN_SITES.get(name, 0):
        raise ValueError('Native-boundary call count changed: ' + name)
    data = b''.join(lines)
    if star_count:
        changes.append({'kind': 'stardist-command', 'before': STAR.decode(), 'after': ADAPTER.decode(), 'count': star_count})
    for statement, count in alignment_changes.items():
        changes.append({'kind': 'alignment-command', 'before': statement.decode(),
                        'after': (statement.replace(ALIGN, ALIGN_ADAPTER, 1) + ALIGN_GUARD).decode(), 'count': count})
    # The renamed root/leaf contain spaces; IJ1 options need outer brackets.
    # IJ1 Macro.getValue counts nested brackets, including the [MacroFork] suffix.
    expected_settings = 1 if name in SETTINGS_SITES else 0
    if data.count(SETTINGS_OPEN) != expected_settings:
        raise ValueError('Settings option path count changed: ' + name)
    data = replace_count(data, SETTINGS_OPEN, SETTINGS_QUOTED, changes, 'settings-option-path')
    data = replace_count(data, b'"GAT"', ('"' + NAMESPACE + '"').encode(), changes, 'installation-path')
    # Every script leaf is unique, including helper leaves. This avoids ImageJ's
    # global command-name collisions when original and fork menus coexist.
    for source in paths:
        if source.suffix not in ('.ijm', '.py'):
            continue
        data = replace_count(data, source.name.encode(), destination_path(source).name.encode(), changes, 'script-path')
    # Batch mode invokes the registered top-level command rather than a path.
    data = replace_count(data, b'" Analyse Neurons"', b'" Analyse Neurons [MacroFork]"', changes, 'batch-menu')
    return data, changes


def generated_files(root=ROOT, settings=None):
    paths = source_paths(root)
    lock = json.loads((root / 'legacy-macros/source-lock.json').read_text())
    pinned = {item['path']: item for item in lock['files']}
    if set(pinned) != {p.as_posix() for p in paths}:
        raise ValueError('Legacy macro asset list differs from the reviewed source lock')
    if not set(STAR_SITES).issubset({p.as_posix() for p in paths}):
        raise ValueError('Missing a pinned legacy StarDist caller')
    records, output = [], {}
    for path in paths:
        original = (root / path).read_bytes()
        if digest(original) != pinned[path.as_posix()]['sha256']:
            raise ValueError('Legacy macro source differs from the reviewed source lock: ' + str(path))
        transformed, changes = transform(path, original, paths)
        source = 'repository'
        if path.as_posix() == 'Tools/commands/gat_settings.ijm' and settings:
            # Explicit source supplied by installer/user. Keep their current
            # values byte-for-byte instead of resetting to package defaults.
            transformed = Path(settings).read_bytes()
            changes = []
            source = 'explicit-existing-settings'
        name = 'scripts/' + NAMESPACE + '/' + destination_path(path).as_posix()
        output[name] = transformed
        records.append({'source': path.as_posix(), 'destination': name,
                        'source_sha256': digest(original), 'destination_sha256': digest(transformed),
                        'settings_source': source if path.name == 'gat_settings.ijm' else None,
                        'substitutions': changes})
    metadata = {
        'format_version': 1,
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        'legacy_macro_source_commit': lock['source_commit'],
        'macro_source': 'Preserved legacy macro blobs, distinct from Java V2 commit 1870d9e',
        'native_stardist_call_sites': sum(STAR_SITES.values()),
        'native_alignment_call_sites': sum(ALIGN_SITES.values()),
        'alignment_fail_stop_guards': sum(ALIGN_SITES.values()),
        'settings_option_path_sites': len(SETTINGS_SITES),
        'files': records,
        'validation_status': 'Candidate only. Source preservation does not establish runtime equivalence.',
    }
    output['MACROFORK_BUILD_INFO.json'] = (json.dumps(metadata, indent=2) + '\n').encode()
    output['MACROFORK_README.md'] = (root / 'legacy-macros/README.md').read_bytes()
    output['MACROFORK_LICENSE'] = (root / 'LICENSE').read_bytes()
    return output, metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New ZIP; existing files are refused')
    parser.add_argument('--settings', type=Path, help='Existing original gat_settings.ijm to preserve byte-for-byte')
    args = parser.parse_args()
    output, metadata = generated_files(settings=args.settings)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(output.items()):
            archive.writestr(name, data)
    print(json.dumps({'zip': str(args.output), 'sha256': digest(args.output.read_bytes()),
                      'script_assets': len(metadata['files']), 'runtime_verified': False}))


if __name__ == '__main__':
    main()
