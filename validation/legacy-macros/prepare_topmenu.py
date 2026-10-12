#!/usr/bin/env python3
"""Build isolated, public-fixture-only Fiji installations; never launches a JVM.

Only immutable runtime JAR/native/JDK files may be hardlinked. Every mutable
script, model, config and preference is copied, and every linked source hash is
recorded for a mandatory post-run comparison. This is setup, not parity proof.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import zipfile

import audit_sources

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIXTURE_SHA = '55251741add488f9a08cf5b33a4ee8ec3fd3023e25ffb0fc18800f80953948d7'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def excluded_jar(path):
    if 'probe' in path.name.lower() or path.name.startswith('GAT_'):
        return True
    with zipfile.ZipFile(path) as jar:
        return any(name.startswith('Features/') or name.endswith('NativeInferenceMain.class')
                   for name in jar.namelist())


def driver_macro(config_path):
    # IJ1 run(command, options) does not forward options to PlugIn.run(arg).
    value = str(config_path).replace('\\', '\\\\').replace('"', '\\"')
    return 'call("LegacyMacroTopMenuProbe.launch", "' + value + '");\n'


def prepare(args):
    source = args.runtime.resolve()
    out = args.output.resolve()
    if out.exists():
        raise ValueError('Refusing to reuse an existing top-menu installation')
    manifest = json.loads((HERE / 'source-manifest.json').read_text())
    audit = audit_sources.audit(ROOT, manifest, args.overlay)
    if audit['status'] != 'PASS_SOURCE_CONTRACT':
        raise ValueError('Original/overlay source audit failed')
    fixture = ROOT / 'Sample Images/2D_enteric_neuron_IF/DYM_22_7_Pr_Hu_crop.tif'
    if sha(fixture) != FIXTURE_SHA:
        raise ValueError('Only the pinned public Hu fixture is accepted')
    out.mkdir(parents=True)
    report = {'schema_version': 1, 'status': 'PREPARED_NOT_RUN', 'runtime_source': str(source),
              'source_audit': audit, 'fixture_sha256': FIXTURE_SHA, 'linked_files': [],
              'excluded_jars': [], 'script_files': [], 'clones': {}}
    # No unknown data directories or cached private inputs are copied.
    dirs = ['jars', 'plugins', 'java', 'lib', 'config', 'macros', 'luts', 'licenses', 'images', 'engines']
    files = ['fiji', 'fiji-linux-x64', 'fiji.bat', 'db.xml.gz', 'README.md', 'WELCOME.md']
    sources = [p for folder in dirs for p in (source / folder).rglob('*') if p.is_file()]
    sources += [source / name for name in files if (source / name).is_file()]
    excluded = {p for p in sources if p.suffix == '.jar' and excluded_jar(p)}
    report['excluded_jars'] = [str(p.relative_to(source)) for p in sorted(excluded)]
    source_hashes = {}
    for variant in ('original', 'native'):
        root = out / variant
        fiji = root / 'Fiji'
        fiji.mkdir(parents=True)
        for src in sources:
            if src in excluded:
                continue
            rel = src.relative_to(source)
            dst = fiji / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            immutable = (rel.parts[0] in ('jars', 'plugins') and src.suffix == '.jar') or rel.parts[0] in ('java', 'lib')
            if immutable:
                os.link(src.resolve(), dst)
                if str(src) not in source_hashes:
                    source_hashes[str(src)] = sha(src)
                report['linked_files'].append({'source': str(src), 'destination': str(dst), 'sha256': source_hashes[str(src)]})
            else:
                shutil.copy2(src, dst)
        # Copy public model bytes: writes by plugins cannot mutate reference models.
        model = '2D_Ganglia_RGB_v3.bioimage.io.model'
        shutil.copytree(source / 'models' / model, fiji / 'models' / model)
        for name in ('2D_enteric_neuron_v4_1.zip', '2D_enteric_neuron_subtype_v4.zip'):
            shutil.copy2(ROOT / 'Models' / name, fiji / 'models' / name)
        if variant == 'original':
            for row in manifest['files']:
                dest = fiji / 'scripts/GAT' / row['path']
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / row['path'], dest)
            dest = fiji / 'scripts/GAT/Tools/commands/close_image.jpg'
            shutil.copy2(ROOT / 'Tools/commands/close_image.jpg', dest)
        else:
            with zipfile.ZipFile(args.overlay) as archive:
                for name in archive.namelist():
                    if not name.startswith('scripts/GAT MacroFork/') or name.endswith('/'):
                        continue
                    if '..' in Path(name).parts:
                        raise ValueError('Unsafe overlay member')
                    dst = fiji / name
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_bytes(archive.read(name))
            shutil.copy2(args.candidate, fiji / 'plugins/GAT_MacroFork.jar')
        for p in (fiji / 'scripts').rglob('*'):
            if p.is_file():
                report['script_files'].append({'path': str(p), 'sha256': sha(p)})
        for folder in ('home', 'cache', 'input', 'evidence'):
            (root / folder).mkdir()
        config = {'schema_version': 1, 'variant': variant, 'scenario': args.scenario,
                  'fixture': str(fixture), 'fixture_sha256': FIXTURE_SHA,
                  'input': str(root / 'input/public_neurons.tif'), 'output': str(root / 'evidence'),
                  'fiji': str(fiji), 'deadline_seconds': 480,
                  'native_worker': str(args.native_worker.resolve()),
                  'source_script': str(fiji / ('scripts/GAT/_Analyse Neurons.ijm' if variant == 'original'
                                               else 'scripts/GAT MacroFork/_Analyse Neurons [MacroFork].ijm'))}
        (root / 'config.json').write_text(json.dumps(config, indent=2) + '\n')
        (root / 'driver.ijm').write_text(driver_macro(root / 'config.json'))
        report['clones'][variant] = str(fiji)
    (out / 'installation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'output': str(out), 'linked_files': len(report['linked_files'])}))


def verify(path):
    manifest = json.loads(path.read_text())
    failures = []
    checked = set()
    for row in manifest['linked_files']:
        for key in ('source', 'destination'):
            name = row[key]
            if name in checked:
                continue
            checked.add(name)
            if not Path(name).is_file() or sha(name) != row['sha256']:
                failures.append(name)
    for row in manifest['script_files']:
        if sha(row['path']) != row['sha256']:
            failures.append(row['path'])
    result = {'status': 'PASS_RUNTIME_IMMUTABILITY' if not failures else 'FAIL_RUNTIME_IMMUTABILITY',
              'checked_linked_paths': len(checked), 'checked_scripts': len(manifest['script_files']), 'failures': failures}
    (path.parent / 'immutability.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return int(bool(failures))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    p = sub.add_parser('prepare')
    for flag in ('runtime', 'output', 'overlay', 'candidate', 'native-worker'):
        p.add_argument('--' + flag, type=Path, required=True)
    p.add_argument('--scenario', choices=('unchanged', 'delete-one', 'add-one'), default='unchanged')
    p = sub.add_parser('verify')
    p.add_argument('installation', type=Path)
    args = parser.parse_args()
    return verify(args.installation) if args.operation == 'verify' else prepare(args)

if __name__ == '__main__':
    raise SystemExit(main())
