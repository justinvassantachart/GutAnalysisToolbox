#!/usr/bin/env python3
"""Prepare an isolated old Template Matching parent runtime; never launch Java.

The official ImageJ plugin and Maven Central JavaCV/OpenCV 1.4.4 artifacts are
pinned by SHA-256/length. The native adapter worker is deliberately separate.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
FORBIDDEN = ('Features/Macros/LegacyTemplateMatching.class',
             'Features/Inference/NativeAlignmentClient.class',
             'TemplateMatching/NativeAlignmentMain.class')


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def artifacts():
    return json.loads((HERE / 'alignment-artifacts.json').read_text())


def jar_names(path):
    if not path.is_file() or not zipfile.is_zipfile(path):
        raise ValueError('Explicit runtime JAR required: ' + str(path))
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
    if set(FORBIDDEN).intersection(names):
        raise ValueError('Fork/worker contamination of original runtime: ' + path.name)
    return names


def is_conflicting(path, names):
    return ('opencv' in path.name.lower() or path.name.startswith(('javacv-', 'javacpp-', 'openblas-'))
            or any(n.startswith(('org/bytedeco/', 'TemplateMatching/')) for n in names))


def validate(entries):
    if not entries or len(entries) != len(set(p.name for p in entries)):
        raise ValueError('Empty or duplicate runtime entries')
    pinned = {p['file']: p for p in artifacts()}
    if not set(pinned) <= {p.name for p in entries}:
        raise ValueError('All five pinned original Template Matching/JavaCV/OpenCV JARs are required')
    for path in entries:
        names = jar_names(path)
        if path.name in pinned:
            row = pinned[path.name]
            if sha(path) != row['sha256'] or path.stat().st_size != row['bytes']:
                raise ValueError('Changed pinned original dependency: ' + path.name)
        elif is_conflicting(path, names):
            raise ValueError('Conflicting unpinned OpenCV/JavaCPP/Template Matching dependency: ' + path.name)
    if 'ij-1.54p.jar' not in {p.name for p in entries}:
        raise ValueError('The pinned IJ1 1.54p foundation is required')


def fetch(row, cache):
    path = cache / row['file']
    if not path.exists():
        partial = path.with_name(path.name + '.download')
        if partial.exists():
            raise ValueError('Incomplete download exists; use a fresh cache: ' + str(partial))
        subprocess.run(['curl', '--fail', '--location', '--silent', '--show-error',
                        '--proto', '=https', '--proto-redir', '=https', '--connect-timeout', '30',
                        '--max-time', '180', '--retry', '2', row['url'], '--output', str(partial)],
                       check=True, timeout=600)
        if sha(partial) != row['sha256'] or partial.stat().st_size != row['bytes']:
            raise ValueError('Downloaded dependency hash/length mismatch: ' + row['file'])
        partial.replace(path)
    if sha(path) != row['sha256'] or path.stat().st_size != row['bytes']:
        raise ValueError('Cached dependency hash/length mismatch: ' + row['file'])
    return path.resolve()


def prepare(dependencies, cache, output):
    if output.exists():
        raise ValueError('Existing output is never overwritten')
    raw = dependencies.read_text().strip().split(os.pathsep)
    if not raw or not all(raw):
        raise ValueError('Empty classpath')
    kept, removed = [], []
    for text in raw:
        path = Path(text).resolve(); names = jar_names(path)
        if is_conflicting(path, names):
            removed.append({'name': path.name, 'sha256': sha(path), 'reason': 'isolated pinned legacy OpenCV replacement'})
        else:
            kept.append(path)
    cache.mkdir(parents=True, exist_ok=True)
    entries = [fetch(row, cache) for row in artifacts()] + kept
    validate(entries)
    output.mkdir(parents=True)
    (output / 'runtime-classpath.txt').write_text(os.pathsep.join(map(str, entries)) + '\n')
    report = {'schema_version': 1, 'scope': 'legacy-alignment-runtime-only', 'software_executed': False,
              'original_native_platform': 'linux-x86_64', 'pinned_artifacts': artifacts(),
              'removed_conflicting_dependencies': removed,
              'runtime_artifacts': [{'name': p.name, 'sha256': sha(p), 'bytes': p.stat().st_size} for p in entries]}
    (output / 'runtime-provenance.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dependencies-classpath', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    r = prepare(args.dependencies_classpath, args.cache, args.output)
    print('VERIFIED_LEGACY_ALIGNMENT_RUNTIME', len(r['runtime_artifacts']), 'JARs;',
          len(r['removed_conflicting_dependencies']), 'conflicting JARs excluded')


if __name__ == '__main__':
    main()
