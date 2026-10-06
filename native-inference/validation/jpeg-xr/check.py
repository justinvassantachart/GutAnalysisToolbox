#!/usr/bin/env python3
"""Isolated JPEG-XR source rebuild and official-fixture decode validation.

Does not modify Fiji, application code, global Java libraries, or Maven artifacts.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tarfile
import time
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent
COMMIT = 'a8e7f81b8f13ef620049caddeb537b5ea5ecffda'
ARTIFACTS = {
    'swig-3.0.10-std_vector.i': (
        'https://raw.githubusercontent.com/swig/swig/d9875c6579efc8a56132313704c69e627c990dac/Lib/java/std_vector.i',
        '9616473e5f30d20de87528ddeba6a75596ea4cd6ae2459d90ffdef4203de50bf'),
    'jxrlib-v0.2.4.tar.gz': (
        'https://codeload.github.com/glencoesoftware/jxrlib/tar.gz/' + COMMIT,
        '3de034f3d0f1a408e2d7ea5ec497ec70edc632406910fac75a5bb8887dea2ee9'),
    'jxrlib-all-0.2.4.jar': (
        'https://maven.scijava.org/content/groups/public/ome/jxrlib-all/0.2.4/jxrlib-all-0.2.4.jar',
        'c5677ff87125def275cc996c982682a917dbef5a3bf0aa614a2081c68769a346'),
    'native-lib-loader-2.5.0.jar': (
        'https://repo.maven.apache.org/maven2/org/scijava/native-lib-loader/2.5.0/native-lib-loader-2.5.0.jar',
        '7ec0dcf847cabdd6487c4724c3cede107a46bdb6585a9dcb63f54c0276b04b40'),
    'slf4j-api-1.7.36.jar': (
        'https://repo.maven.apache.org/maven2/org/slf4j/slf4j-api/1.7.36/slf4j-api-1.7.36.jar',
        'd3ef575e3e4979678dc01bf1dcce51021493b4d11fb7f1be8ad982877c16a1c0'),
    'bioformats_package-8.5.0.jar': (
        'https://downloads.openmicroscopy.org/bio-formats/8.5.0/artifacts/bioformats_package.jar',
        'c6e60665d53a334b66e4d635340151f403dfe57a64704c573dd4c03b873befb9'),
}


def sha256(path):
    with Path(path).open('rb') as stream:
        h = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
        return h.hexdigest()


def run(command, log, cwd=None, env=None):
    print('+', ' '.join(map(str, command)), flush=True)
    with Path(log).open('w') as stream:
        subprocess.run(list(map(str, command)), cwd=cwd, env=env, stdout=stream,
                       stderr=subprocess.STDOUT, check=True, timeout=900)


def download(cache, name):
    url, expected = ARTIFACTS[name]
    path = cache / name
    if not path.exists():
        partial = path.with_suffix(path.suffix + '.partial')
        with urllib.request.urlopen(url, timeout=120) as response, partial.open('wb') as out:
            shutil.copyfileobj(response, out)
        if sha256(partial) != expected:
            raise ValueError('SHA-256 mismatch for ' + name)
        partial.replace(path)
    if sha256(path) != expected:
        raise ValueError('SHA-256 mismatch for cached ' + name)
    return path


def source_from_archive(archive, output):
    source = output / ('jxrlib-' + COMMIT)
    if source.exists():
        raise ValueError('Use a fresh output directory; refusing to reuse a source/build tree')
    # All sources and fixture bytes are pinned to the official source archive hash.
    with tarfile.open(archive) as tf:
        for member in tf.getmembers():
            relative = Path(member.name)
            if relative.is_absolute() or '..' in relative.parts or member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                raise ValueError('Unsafe source archive member: ' + member.name)
        tf.extractall(output)
    return source


def native_build(source, output, target, artifacts):
    env = os.environ.copy()
    # Fresh process has no DYLD/LD overrides; the actual test must load from its JAR resource.
    swig = shutil.which('swig')
    if not swig:
        raise RuntimeError('SWIG is required for --mode native (on Mac: brew install swig)')
    run([swig, '-version'], output / 'swig-version.log')
    java_home = env.get('JAVA_HOME')
    if not java_home:
        if platform.system() == 'Darwin':
            java_home = subprocess.check_output(['/usr/libexec/java_home'], text=True).strip()
        else:
            java_home = str(Path(shutil.which('javac')).resolve().parents[1])
    env['JAVA_HOME'] = java_home
    # Upstream omits these declarations. Supply their exact standard/source types;
    # no codec function body, constant, SIMD selection, or optimization is changed.
    (source / 'gat-compat.h').write_text('#include <wchar.h>\nextern unsigned int _byteswap_ulong(unsigned int);\n')
    if target == 'osx_arm64':
        env['MACOSX_DEPLOYMENT_TARGET'] = '11.0'
        cc = 'clang -arch arm64 -mmacosx-version-min=11.0 -include gat-compat.h -Wno-error=incompatible-pointer-types'
        cxx = 'clang++ -arch arm64 -mmacosx-version-min=11.0 -std=c++98'
        suffix = 'dylib'
        run(['clang', '--version'], output / 'compiler-version.log')
    else:
        cc, cxx, suffix = 'cc -include gat-compat.h -Wno-error=incompatible-pointer-types', 'c++ -std=c++98', 'so'
        run(['cc', '--version'], output / 'compiler-version.log')
    # Build the upstream JNI target, not the unrelated OpenSSL-dependent C++ CLI.
    # No codec or wrapper source edits; explicit C++98 retains pre-move SWIG wrapper semantics.
    legacy = source / 'gat-legacy-swig'
    legacy.mkdir()
    shutil.copyfile(artifacts['swig-3.0.10-std_vector.i'], legacy / 'std_vector.i')
    run(['make', 'swig', 'SWIG=' + swig + ' -I' + str(legacy)], output / 'swig.log', cwd=source, env=env)
    library = source / 'build' / ('libjxrjava.' + suffix)
    run(['make', '-j2', str(library), 'CC=' + cc, 'CXX=' + cxx],
        output / 'build.log', cwd=source, env=env)
    run(['file', str(library)], output / 'native-file.log')
    if target == 'osx_arm64':
        run(['lipo', '-info', library], output / 'native-architecture.log')
        arches = subprocess.check_output(['lipo', '-archs', str(library)], text=True).strip()
        if arches != 'arm64':
            raise AssertionError('Native library is not exclusively arm64: ' + arches)
        run(['otool', '-L', library], output / 'native-dependencies.log')
        run(['otool', '-l', library], output / 'native-load-commands.log')
    overlay = output / ('jxrlib-native-' + target + '-validation.jar')
    with zipfile.ZipFile(overlay, 'w', zipfile.ZIP_DEFLATED) as jar:
        jar.write(library, 'META-INF/lib/' + target + '/' + library.name)
        jar.writestr('VALIDATION-ONLY.txt',
                     'Experimental locally rebuilt JNI; not an upstream release or Fiji update.\n'
                     'Source: https://github.com/glencoesoftware/jxrlib/tree/' + COMMIT + '\n'
                     'Microsoft C codec has BSD terms. Glencoe C++ wrapper source has GPL-2.0-or-later notices.\n'
                     'See source archive for exact notices; do not relabel this binary BSD-only.\n')
    return overlay, library


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', required=True, choices=['reference', 'native'])
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--cache', type=Path)
    parser.add_argument('--expect-platform', choices=['linux_64', 'osx_arm64'])
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    cache = (args.cache or output / 'cache').resolve()
    cache.mkdir(parents=True, exist_ok=True)
    system, machine = platform.system(), platform.machine().lower()
    target = ('osx_arm64' if system == 'Darwin' and machine == 'arm64' else
              'linux_64' if system == 'Linux' and machine in ('x86_64', 'amd64') else None)
    if target is None or (args.expect_platform and target != args.expect_platform):
        raise RuntimeError('Unexpected host architecture: ' + system + '/' + machine)
    if args.mode == 'reference' and target != 'linux_64':
        raise RuntimeError('The pinned official release has no osx_arm64 native resource')
    artifacts = {name: download(cache, name) for name in ARTIFACTS}
    source = source_from_archive(artifacts['jxrlib-v0.2.4.tar.gz'], output)
    manifest = json.loads((HERE / 'fixtures.json').read_text())
    fields = ['filename', 'width', 'height', 'bytes_per_pixel', 'decoded_md5', 'input_sha256']
    with (output / 'fixtures.tsv').open('w') as stream:
        writer = csv.DictWriter(stream, fields, delimiter='\t', extrasaction='ignore')
        writer.writeheader()
        writer.writerows(manifest['fixtures'])
    cp = [artifacts[name] for name in ['native-lib-loader-2.5.0.jar', 'jxrlib-all-0.2.4.jar',
                                    'slf4j-api-1.7.36.jar', 'bioformats_package-8.5.0.jar']]
    report = {'mode': args.mode, 'target': target, 'upstream_commit': COMMIT,
              'status': 'running', 'artifacts': {n: {'url': ARTIFACTS[n][0], 'sha256': sha256(p)}
                                                for n, p in artifacts.items()}}
    try:
        if args.mode == 'native':
            overlay, library = native_build(source, output, target, artifacts)
            cp.insert(0, overlay)
            report['native_library_sha256'] = sha256(library)
            report['native_overlay_sha256'] = sha256(overlay)
            # SWIG4 changed std::vector helper APIs. Pin the old typemap and verify
            # every published JNI declaration, not only the decode methods exercised.
            abi_classes = output / 'abi-classes'
            abi_classes.mkdir()
            generated = sorted((source / 'java/target/swig/ome/jxrlib').glob('*.java'))
            run(['javac', '--release', '11', '-cp', artifacts['jxrlib-all-0.2.4.jar'],
                 '-d', abi_classes] + generated, output / 'abi-compile.log')
            def signatures(cp, name):
                log = output / name
                run(['javap', '-p', '-s', '-classpath', cp, 'ome.jxrlib.JXRJNI'], log)
                text = log.read_text()
                return set(re.findall(r'public static final native .*?;', text))
            old = signatures(artifacts['jxrlib-all-0.2.4.jar'], 'published-jni.log')
            new = signatures(abi_classes, 'generated-jni.log')
            if not old or old != new:
                raise AssertionError('Generated JNI API mismatch: missing=' + repr(old-new) + ', added=' + repr(new-old))
            report['published_jni_signatures_matched'] = len(old)
        classes = output / 'classes'
        classes.mkdir(exist_ok=True)
        classpath = os.pathsep.join(map(str, cp))
        run(['javac', '--release', '11', '-cp', classpath, '-d', classes, HERE / 'JpegXrProbe.java'],
            output / 'compile.log')
        env = os.environ.copy()
        for key in ['LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH', 'DYLD_FALLBACK_LIBRARY_PATH']:
            env.pop(key, None)
        empty = output / 'empty-native-search'
        empty.mkdir(exist_ok=True)
        temp = output / 'jni-tmp'
        temp.mkdir(exist_ok=True)
        run(['java', '-Xmx256m', '-Djava.library.path=' + str(empty), '-Djava.io.tmpdir=' + str(temp),
             '-cp', str(classes) + os.pathsep + classpath, 'JpegXrProbe', source,
             output / 'fixtures.tsv', output / 'actual.tsv', target], output / 'decode.log', env=env)
        with (output / 'actual.tsv').open() as stream:
            actual = list(csv.DictReader(stream, delimiter='\t'))
        with (HERE / 'linux-reference.tsv').open() as stream:
            expected = list(csv.DictReader(stream, delimiter='\t'))
        if actual != expected or len(actual) != 13:
            raise AssertionError('Exact dimensions, types or decoded hashes differ from official Linux reference')
        if args.mode == 'native':
            log = (output / 'decode.log').read_text()
            if ('native.resource=jar:file:' + str(overlay)) not in log:
                raise AssertionError('Probe did not resolve the experimental overlay native resource')
        report.update(status='pass', fixtures=len(actual), exact_linux_reference=True)
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        report['completed_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
