#!/usr/bin/env python3
"""Package a successful native check as an optional resource-only JPEG-XR overlay.

Offline: consumes check.py output/cache. Does not install, publish, modify source,
change Mach-O install IDs, fetch dependencies, or trust a pass label alone.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import struct
import subprocess
import tarfile
import zipfile
import check

HERE = Path(__file__).resolve().parent
ASSETS = HERE / 'overlay'
RESOURCE = 'META-INF/lib/osx_arm64/libjxrjava.dylib'
JAR_NAME = 'gat-jxrlib-0.2.4-osx-arm64-test-overlay.jar'
SOURCE_NAME = 'gat-jxrlib-0.2.4-corresponding-source.zip'
PACKAGE_NAME = 'gat-jpeg-xr-0.2.4-macos-arm64-test-overlay.zip'
COMPAT = b'#include <wchar.h>\nextern unsigned int _byteswap_ulong(unsigned int);\n'
SYSTEM_LIBRARIES = {'/usr/lib/libc++.1.dylib', '/usr/lib/libSystem.B.dylib'}
# Deliberate release allowlist, not a minimum-version check. Adding a release
# requires reviewing its official, commit-pinned notices and exact regeneration.
REVIEWED_SWIG_GENERATORS = {
    '4.5.0': 'd598176759f5d199e288cf78413cfaa3bf84449f',
    '4.5.1': '88649f559942c29a228fa783dd01581e217bcb20',
}
# These four official files are byte-identical in the two reviewed releases.
SWIG_NOTICE_SHA256 = {
    'LICENSE': 'f53abaeed775018d519a1b9615f0ca17894772bd9ca21c2a156bf340ac41c13e',
    'COPYRIGHT': '0ecb0b7b8363a337f1dc42d4b735983c08b1b65a462e778419d8b4fa5e541961',
    'LICENSE-UNIVERSITIES': '7f50d942373a871211c5efee03f3db2f9efd1cff1002b0ef8e3748baa611a5c2',
    'LICENSE-GPL': '8ceb4b9ee5adedde47b31e975c1d90c73ad27b6b165a1dcd80c7c545eb65b903',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(name):
    p = PurePosixPath(name)
    if not name or '\\' in name or ':' in name or p.is_absolute() or '..' in p.parts or '.' in name.split('/') or '' in name.split('/'):
        raise ValueError('Unsafe archive path: ' + name)
    return name


def local_file(root, relative):
    safe_name(relative)
    # The caller chooses a trusted root. Canonicalize its location once: macOS
    # legitimately aliases /var to /private/var outside a temporary source root.
    # Only components BELOW that boundary must be free of symlinks.
    root = Path(root).resolve(strict=True)
    path = root
    for component in PurePosixPath(relative).parts:
        path = path / component
        if path.is_symlink():
            raise ValueError('Missing file or unsafe symlink: ' + str(path))
    if not path.is_file():
        raise ValueError('Missing file or unsafe symlink: ' + str(path))
    if root not in path.resolve(strict=True).parents:
        raise ValueError('Path escaped source root')
    return path.read_bytes()


def zip_bytes(entries):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(entries.items()):
            safe_name(name)
            entry = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.create_system = 3
            entry.external_attr = (0o100755 if name.endswith('.sh') else 0o100644) << 16
            archive.writestr(entry, data)
    return out.getvalue()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def checksums(entries):
    return ''.join(digest(data) + '  ' + name + '\n' for name, data in sorted(entries.items())).encode()


def audit_macho(data):
    if len(data) < 32 or data[:4] != b'\xcf\xfa\xed\xfe':
        raise ValueError('Expected thin little-endian Mach-O 64-bit dylib')
    magic, cpu, subtype, kind, ncmds, size, flags, reserved = struct.unpack_from('<8I', data)
    if cpu != 0x0100000c or kind != 6:
        raise ValueError('Expected exclusively arm64 MH_DYLIB')
    if 32 + size > len(data) or ncmds > size // 8:
        raise ValueError('Truncated Mach-O commands')
    dependencies, ids, rpaths = [], [], []
    pos = 32
    for unused in range(ncmds):
        if pos + 8 > 32 + size:
            raise ValueError('Truncated Mach-O command')
        cmd, length = struct.unpack_from('<II', data, pos)
        if length < 8 or pos + length > 32 + size:
            raise ValueError('Invalid Mach-O command length')
        base = cmd & 0x7fffffff
        if base == 0x27:
            raise ValueError('Unexpected Mach-O dynamic-loader environment override')
        if base in (0xc, 0xd, 0x18, 0x1f, 0x20, 0x23, 0x1c):
            if length < (12 if base == 0x1c else 24):
                raise ValueError('Truncated Mach-O path command')
            offset = struct.unpack_from('<I', data, pos + 8)[0]
            if offset < 12 or offset >= length:
                raise ValueError('Invalid Mach-O path offset')
            value = data[pos + offset:pos + length].split(b'\0', 1)[0].decode('utf-8')
            if base == 0xd:
                ids.append(value)  # Its own LC_ID_DYLIB is not a runtime dependency.
            elif base == 0x1c:
                rpaths.append(value)
            else:
                dependencies.append(value)
        pos += length
    if pos != 32 + size or len(ids) != 1:
        raise ValueError('Malformed Mach-O command table or dylib identity')
    if set(dependencies) != SYSTEM_LIBRARIES or rpaths:
        raise ValueError('Unexpected runtime dependency/search path: ' + repr((dependencies, rpaths)))
    return {'architecture': 'arm64', 'runtime_dependencies': dependencies, 'rpaths': rpaths,
            'install_id': ids[0], 'install_id_note': 'Preserved LC_ID_DYLIB identifies this library; it is not a dependency. No install_name_tool mutation.'}


def verify_pass(report):
    expected = {'mode': 'native', 'target': 'osx_arm64', 'status': 'pass',
                'upstream_commit': check.COMMIT, 'fixtures': 13,
                'published_jni_signatures_matched': 59, 'exact_linux_reference': True}
    for key, value in expected.items():
        if report.get(key) != value:
            raise ValueError('Successful native check required: ' + key)
    for name, (url, sha) in check.ARTIFACTS.items():
        if report.get('artifacts', {}).get(name) != {'url': url, 'sha256': sha}:
            raise ValueError('Check artifact provenance mismatch: ' + name)


def reviewed_swig_generator(version):
    if version not in REVIEWED_SWIG_GENERATORS:
        raise ValueError('Review/include matching generator notices before packaging another SWIG version')
    commit = REVIEWED_SWIG_GENERATORS[version]
    return {'version': version, 'upstream_commit': commit,
            'source_url': 'https://github.com/swig/swig/tree/' + commit,
            'notice_sha256': dict(SWIG_NOTICE_SHA256)}


def parse_swig_version(log):
    lines = [line for line in log.splitlines() if line.startswith('SWIG Version ')]
    match = re.fullmatch(r'SWIG Version ([0-9]+\.[0-9]+\.[0-9]+)', lines[0]) if len(lines) == 1 else None
    if not match:
        raise ValueError('Exactly one unambiguous SWIG release version required')
    version = match.group(1)
    reviewed_swig_generator(version)
    return version


def legal_assets(swig_version):
    generator = reviewed_swig_generator(swig_version)
    manifest = json.loads((ASSETS / 'license-manifest.json').read_text())
    result, records = {}, {}
    for item in manifest['files']:
        if item['path'] in result:
            raise ValueError('Duplicate license asset: ' + item['path'])
        data = local_file(ASSETS, item['path'])
        if digest(data) != item['sha256']:
            raise ValueError('License asset checksum mismatch: ' + item['path'])
        result[item['path']] = data
        records[item['path']] = item
    required = {'LICENSES/GPL-2.0.txt', 'LICENSES/MICROSOFT-CODEC-HEADER.txt',
                'LICENSES/GLENCOE-WRAPPER-HEADER.txt', 'LICENSES/SWIG-3-LICENSE',
                'LICENSES/SWIG-3-COPYRIGHT', 'LICENSES/SWIG-3-LICENSE-UNIVERSITIES',
                'LICENSES/SWIG-GPL-3.0.txt', 'LICENSES/GAT-BSD-3-Clause.txt'}
    required.update('LICENSES/SWIG-' + swig_version + '-' + name
                    for name in SWIG_NOTICE_SHA256 if name != 'LICENSE-GPL')
    if not required.issubset(result):
        raise ValueError('Required source license notices are missing')
    for name, sha in SWIG_NOTICE_SHA256.items():
        path = 'LICENSES/SWIG-GPL-3.0.txt' if name == 'LICENSE-GPL' else 'LICENSES/SWIG-' + swig_version + '-' + name
        if digest(result[path]) != sha:
            raise ValueError('Reviewed SWIG notice checksum mismatch: ' + path)
        # GPL3 is shared with the pinned SWIG3 notice; retain that original URL.
        if name != 'LICENSE-GPL' and records[path]['source_url'] != (
                'https://raw.githubusercontent.com/swig/swig/' + generator['upstream_commit'] + '/' + name):
            raise ValueError('Reviewed SWIG notice source provenance mismatch: ' + path)
    if b'GNU GENERAL PUBLIC LICENSE' not in result['LICENSES/GPL-2.0.txt']:
        raise ValueError('Missing complete GPL license')
    if b'either version 2' not in result['LICENSES/GLENCOE-WRAPPER-HEADER.txt']:
        raise ValueError('Wrapper GPL-2.0-or-later notice missing')
    result['license-manifest.json'] = json_bytes(manifest)
    result['THIRD_PARTY_NOTICES.md'] = local_file(ASSETS, 'THIRD_PARTY_NOTICES.md')
    return result


def corresponding_source(archive, source, license_entries, swig_version):
    generator = reviewed_swig_generator(swig_version)
    if check.sha256(archive) != check.ARTIFACTS['jxrlib-v0.2.4.tar.gz'][1]:
        raise ValueError('Upstream source archive hash mismatch')
    prefix = 'jxrlib-' + check.COMMIT + '/'
    entries, omitted, original_hashes = {}, [], {}
    with tarfile.open(archive) as tf:
        for item in tf.getmembers():
            safe_name(item.name.rstrip('/'))
            if not item.name.startswith(prefix) and item.name.rstrip('/') != prefix.rstrip('/'):
                raise ValueError('Unexpected source archive root')
            if item.issym() or item.islnk() or not (item.isfile() or item.isdir()):
                raise ValueError('Unsafe source archive entry')
            if not item.isfile():
                continue
            relative = item.name[len(prefix):]
            if relative.split('/')[0] in ('fixtures', 'bin', 'doc') or relative == 'gradle/wrapper/gradle-wrapper.jar':
                omitted.append(relative)
                continue
            if relative.endswith(('.class', '.jar', '.exe', '.dll', '.so', '.dylib', '.a')):
                raise ValueError('Unexpected prebuilt binary in corresponding source: ' + relative)
            data = tf.extractfile(item).read()
            if local_file(source, relative) != data:
                raise ValueError('Upstream source changed after validation: ' + relative)
            entries['jxrlib/' + relative] = data
            original_hashes[relative] = digest(data)
    for relative in ('gat-compat.h', 'gat-legacy-swig/std_vector.i'):
        data = local_file(source, relative)
        if relative == 'gat-compat.h' and data != COMPAT:
            raise ValueError('Compatibility header changed')
        if relative.endswith('std_vector.i') and digest(data) != check.ARTIFACTS['swig-3.0.10-std_vector.i'][1]:
            raise ValueError('Pinned SWIG3 typemap changed')
        entries['jxrlib/' + relative] = data
    generated = sorted((source / 'java/target/swig').rglob('*'))
    copied = []
    for path in generated:
        if path.is_file() and path.suffix in ('.java', '.cxx'):
            relative = path.relative_to(source).as_posix()
            entries['jxrlib/' + relative] = local_file(source, relative)
            copied.append(relative)
    if 'java/target/swig/JXR_wrap.cxx' not in copied or not any(x.endswith('/JXRJNI.java') for x in copied):
        raise ValueError('Generated JNI corresponding source missing')
    entries.update(license_entries)
    entries['rebuild.sh'] = local_file(ASSETS, 'rebuild.sh')
    entries['REBUILD.md'] = local_file(ASSETS, 'REBUILD.md')
    entries['SWIG_VERSION'] = (swig_version + '\n').encode()
    entries['SOURCE_PROVENANCE.json'] = json_bytes({'upstream_commit': check.COMMIT,
        'swig_generator': generator,
        'source_url': check.ARTIFACTS['jxrlib-v0.2.4.tar.gz'][0],
        'source_archive_sha256': check.ARTIFACTS['jxrlib-v0.2.4.tar.gz'][1],
        'unchanged_original_source_sha256': original_hashes, 'included_generated_sources': copied,
        'excluded_not_required_for_native_build': omitted,
        'exclusion_reason': 'No upstream fixture-image redistribution permission is asserted. Also omit prebuilt executables, the unnecessary Gradle wrapper binary, and unrelated binary documentation. All JNI/C/C++ build sources and generated wrappers are included.'})
    entries['SHA256SUMS'] = checksums(entries)
    return zip_bytes(entries)


def verify_generated_sources(source_zip, output, expected_swig):
    """Regenerate from the supplied preferred source; reject changed generated JNI."""
    reviewed_swig_generator(expected_swig)
    root = output / 'source-regeneration'
    root.mkdir()
    expected = {}
    with zipfile.ZipFile(io.BytesIO(source_zip)) as archive:
        if archive.read('SWIG_VERSION') != (expected_swig + '\n').encode():
            raise ValueError('Corresponding source SWIG version mismatch')
        for name in archive.namelist():
            safe_name(name)
            if not name.startswith('jxrlib/'):
                continue
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))
            if name.startswith('jxrlib/java/target/swig/'):
                expected[name] = archive.read(name)
    swig = shutil.which('swig')
    if not swig or parse_swig_version(subprocess.check_output([swig, '-version'], text=True)) != expected_swig:
        raise ValueError('Matching SWIG ' + expected_swig + ' required to verify corresponding generated source')
    tree = root / 'jxrlib'
    check.run(['make', 'swig', 'SWIG=' + swig + ' -I' + str(tree / 'gat-legacy-swig')],
              output / 'source-regeneration.log', cwd=tree)
    for name, data in expected.items():
        if (root / name).read_bytes() != data:
            raise ValueError('Generated source does not match preferred interface/typemap: ' + name)
    shutil.rmtree(root)


def rerun_probe(check_output, cache, source, jar, output):
    jars = ['native-lib-loader-2.5.0.jar', 'jxrlib-all-0.2.4.jar',
            'slf4j-api-1.7.36.jar', 'bioformats_package-8.5.0.jar']
    for name in jars:
        if check.sha256(cache / name) != check.ARTIFACTS[name][1]:
            raise ValueError('Cached probe dependency mismatch: ' + name)
    classes = output / 'probe-classes'; classes.mkdir()
    cp = os.pathsep.join([str(cache / name) for name in jars] + [str(jar)])
    # Overlay last: this tests normal resource resolution, not replacing Java classes.
    env = os.environ.copy()
    for key in ['LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH', 'DYLD_FALLBACK_LIBRARY_PATH']:
        env.pop(key, None)
    check.run(['javac', '--release', '11', '-cp', cp, '-d', classes, HERE / 'JpegXrProbe.java'], output / 'final-overlay-compile.log', env=env)
    empty, temp = output / 'empty-native-search', output / 'jni-tmp'
    empty.mkdir(); temp.mkdir()
    check.run(['java', '-Xmx256m', '-Djava.library.path=' + str(empty), '-Djava.io.tmpdir=' + str(temp),
               '-cp', str(classes) + os.pathsep + cp, 'JpegXrProbe', source,
               check_output / 'fixtures.tsv', output / 'final-overlay-actual.tsv', 'osx_arm64'],
              output / 'final-overlay-decode.log', env=env)
    def rows(path):
        with path.open() as stream:
            return list(csv.DictReader(stream, delimiter='\t'))
    actual = rows(output / 'final-overlay-actual.tsv')
    if len(actual) != 13 or actual != rows(HERE / 'linux-reference.tsv'):
        raise ValueError('Final overlay golden decode mismatch')
    if ('native.resource=jar:file:' + str(jar)) not in (output / 'final-overlay-decode.log').read_text():
        raise ValueError('Final resource-only JAR was not used')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-output', type=Path, required=True)
    parser.add_argument('--cache', type=Path, help='Original check dependency cache; defaults to CHECK_OUTPUT/cache')
    parser.add_argument('--output', type=Path, required=True, help='New empty packaging directory')
    args = parser.parse_args()
    if (platform.system(), platform.machine().lower()) != ('Darwin', 'arm64'):
        raise ValueError('Package and revalidate on native macOS arm64 only')
    origin, output = args.check_output.resolve(), args.output.resolve()
    cache = (args.cache or origin / 'cache').resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a new empty output directory; never overwrite package/evidence')
    output.mkdir(parents=True, exist_ok=True)
    report = json.loads(local_file(origin, 'report.json'))
    verify_pass(report)
    source = origin / ('jxrlib-' + check.COMMIT)
    library = local_file(source, 'build/libjxrjava.dylib')
    if digest(library) != report['native_library_sha256']:
        raise ValueError('Validated native binary changed')
    swig_log = local_file(origin, 'swig-version.log').decode()
    swig_version = parse_swig_version(swig_log)
    macho = audit_macho(library)
    legal = legal_assets(swig_version)
    src = corresponding_source(cache / 'jxrlib-v0.2.4.tar.gz', source, legal, swig_version)
    verify_generated_sources(src, output, swig_version)
    entries = {RESOURCE: library, 'META-INF/MANIFEST.MF': b'Manifest-Version: 1.0\nImplementation-Title: GAT optional JPEG-XR arm64 test overlay\nImplementation-Version: 0.2.4-gat-test.1\n\n'}
    entries.update({'META-INF/' + name: value for name, value in legal.items()})
    jar_data = zip_bytes(entries)
    if any(name.endswith('.class') for name in entries):
        raise ValueError('Resource overlay must never contain Java classes')
    jar = output / JAR_NAME; jar.write_bytes(jar_data)
    (output / SOURCE_NAME).write_bytes(src)
    rerun_probe(origin, cache, source, jar, output)
    info = {'schema_version': 1, 'status': 'pass', 'optional_test_overlay': True,
            'upstream_commit': check.COMMIT, 'native_sha256': digest(library),
            'jar_sha256': digest(jar_data), 'corresponding_source_sha256': digest(src),
            'resource': RESOURCE, 'java_classes': 0, 'macho': macho,
            'source_check_report_sha256': check.sha256(origin / 'report.json'),
            'check_artifacts': report['artifacts'], 'golden_fixtures_passed': 13,
            'published_jni_signatures_matched': 59,
            'swig_generator': swig_log,
            'swig_generator_provenance': reviewed_swig_generator(swig_version),
            'generated_sources_regenerated_and_identical': True,
            'compiler': local_file(origin, 'compiler-version.log').decode(),
            'install_requires': ['native macOS arm64 Fiji/Java', 'jxrlib-all 0.2.4', 'native-lib-loader 2.5.0', 'Bio-Formats 8.5.0'],
            'scope': 'Final resource JAR decode/vector/JNI via published Java bindings and Bio-Formats service/codec. Full Fiji updater/classloader and full microscopy container GUI testing remain required.'}
    package = {'jars/' + JAR_NAME: jar_data, 'source/' + SOURCE_NAME: src,
               'README.md': local_file(ASSETS, 'README.md'), 'BUILD_INFO.json': json_bytes(info)}
    package.update(legal)
    for name in ('final-overlay-decode.log', 'final-overlay-actual.tsv', 'final-overlay-compile.log', 'source-regeneration.log'):
        package['validation/' + name] = (output / name).read_bytes()
    package['validation/original-check-report.json'] = json_bytes(report)
    package['SHA256SUMS'] = checksums(package)
    archive = output / PACKAGE_NAME; archive.write_bytes(zip_bytes(package))
    (output / 'package-report.json').write_bytes(json_bytes(info))
    for path in (jar, output / SOURCE_NAME, archive):
        path.with_suffix(path.suffix + '.sha256').write_text(check.sha256(path) + '  ' + path.name + '\n')
    print(str(archive)); print(check.sha256(archive))


if __name__ == '__main__':
    main()
