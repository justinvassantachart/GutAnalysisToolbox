#!/usr/bin/env python3
"""Prepare checksummed public-only inputs and the isolated legacy command runtime.

Does not execute models, install into Fiji, or include production/worker classes.
The caller resolves the existing pinned baseline dependency POM first. Both the
original reference and native adapter use this parent runtime; modern TensorFlow
stays in the independently built worker JVM only.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {'ij-1.54p.jar', 'imagej-legacy-2.0.3.jar', 'ij1-patcher-2.0.0.jar',
            'tensorflow-1.15.0.jar', 'libtensorflow-1.15.0.jar',
            'libtensorflow_jni-1.15.0.jar', 'proto-1.15.0.jar', 'protobuf-java-3.11.4.jar'}
FORBIDDEN = ('Features/Macros/LegacyMacroStarDist.class', 'Features/Inference/NativeStarDist.class',
             'org/tensorflow/types/TFloat32.class', 'org/gatanalysis/inference/NativeInferenceMain.class')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def verify(path, expected_sha, expected_bytes=None):
    if not path.is_file() or sha(path) != expected_sha:
        raise ValueError('Public artifact checksum mismatch: ' + str(path))
    if expected_bytes is not None and path.stat().st_size != expected_bytes:
        raise ValueError('Public artifact byte length mismatch: ' + str(path))


def fetch(url, path, expected_sha, expected_bytes=None):
    if not url.startswith('https://'):
        raise ValueError('Only HTTPS publisher URLs are accepted')
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        verify(path, expected_sha, expected_bytes)
        return
    partial = path.with_name(path.name + '.download')
    if partial.exists():
        raise ValueError('Prior incomplete download exists; use a clean cache: ' + str(partial))
    subprocess.run(['curl', '--fail', '--location', '--silent', '--show-error',
                    '--proto', '=https', '--proto-redir', '=https', '--retry', '2',
                    '--connect-timeout', '30', '--max-time', '240', url, '--output', str(partial)],
                   check=True, timeout=780)
    verify(partial, expected_sha, expected_bytes)
    partial.replace(path)


def validate_dependencies(entries):
    names = [p.name for p in entries]
    missing = REQUIRED - set(names)
    if missing:
        raise ValueError('Missing pinned original-runtime dependencies: ' + ', '.join(sorted(missing)))
    if len(names) != len(set(names)):
        raise ValueError('Ambiguous duplicate dependency basenames')
    protobuf = [name for name in names if name.startswith('protobuf-java-')
                and not name.startswith('protobuf-java-util-')]
    if protobuf != ['protobuf-java-3.11.4.jar']:
        raise ValueError('TF1 reference requires protobuf-java 3.11.4 only; got ' + str(protobuf))
    for path in entries:
        if not path.is_file() or not zipfile.is_zipfile(path):
            raise ValueError('Expected explicit dependency JAR, no directories/wildcards: ' + str(path))
        with zipfile.ZipFile(path) as archive:
            present = set(archive.namelist())
        if any(name in present for name in FORBIDDEN):
            raise ValueError('Fork/modern-worker contamination of original runtime: ' + str(path))


def prepare(root, dependencies, cache, output):
    if output.exists():
        raise ValueError('Refusing to overwrite runtime provenance/output: ' + str(output))
    raw = dependencies.read_text().strip().split(os.pathsep)
    if not raw or any(not part for part in raw):
        raise ValueError('Empty dependency classpath')
    entries = [Path(part).resolve() for part in raw]
    validate_dependencies(entries)
    plugins = json.loads((root / 'native-inference/validation/baseline/plugin-artifacts.json').read_text())
    fixtures = json.loads((root / 'native-inference/validation/cross-platform/fixture-manifest.json').read_text())
    downloaded = []
    for item in plugins:
        path = cache / 'plugins' / item['file']
        fetch(item['url'], path, item['sha256'], item.get('bytes'))
        downloaded.append(path.resolve())
    source = cache / 'fixtures/public-Hu.tif'
    fetch(fixtures['source']['url'], source, fixtures['source']['sha256'])
    models = {}
    for item in fixtures['cases']:
        name = item['model']
        if name in models and models[name] != item['model_sha256']:
            raise ValueError('Conflicting model pins: ' + name)
        models[name] = item['model_sha256']
    for name, digest in models.items():
        fetch(fixtures['model_source_base'] + name, cache / 'models' / name, digest)
    classpath = downloaded + entries
    validate_dependencies(classpath)
    output.mkdir(parents=True)
    (output / 'runtime-classpath.txt').write_text(os.pathsep.join(map(str, classpath)) + '\n')
    record = {'schema_version': 1, 'scope': 'public-assets-and-original-command-runtime-only',
              'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
              'model_execution': False,
              'legacy_plugins': plugins, 'fixture': fixtures['source'], 'models': models,
              'fixture_path': str(source.resolve()), 'models_directory': str((cache / 'models').resolve()),
              'runtime_artifacts': [{'name': p.name, 'sha256': sha(p), 'bytes': p.stat().st_size} for p in classpath]}
    (output / 'runtime-provenance.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dependencies-classpath', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    record = prepare(ROOT, args.dependencies_classpath, args.cache, args.output)
    print(json.dumps({'status': 'VERIFIED_PUBLIC_RUNTIME', 'artifacts': len(record['runtime_artifacts']),
                      'model_execution': False}))


if __name__ == '__main__':
    main()
