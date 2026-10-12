#!/usr/bin/env python3
"""Assemble the native-Mac test overlay from separately built, pinned artifacts."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile


def checked_entries(archive, prefix):
    """Reject unsafe/duplicate entries before copying a companion distribution."""
    result, seen = [], set()
    for entry in archive.infolist():
        name = entry.filename
        parts = PurePosixPath(name).parts
        canonical = name[:-1] if entry.is_dir() else name
        if (str(PurePosixPath(canonical)) != canonical or not parts or name.startswith('/') or '\\' in name or '..' in parts
                or parts[0] != prefix or name in seen
                or ((entry.external_attr >> 16) & 0o170000) == 0o120000):
            raise ValueError('Unsafe or duplicate companion archive entry: ' + name)
        seen.add(name)
        if not entry.is_dir():
            result.append(entry)
    return result


def validate_bundle(path, prefix, required, classifiers):
    with zipfile.ZipFile(path) as archive:
        entries = checked_entries(archive, prefix)
        names = {e.filename for e in entries}
        if not set(required).issubset(names):
            raise ValueError('Incomplete distribution: ' + str(sorted(set(required) - names)))
        for classifier in classifiers:
            matches = [n for n in names if n.startswith(prefix + '/lib/' + classifier)
                       and n.endswith('-macosx-arm64.jar')]
            if len(matches) != 1:
                raise ValueError('Expected one native ARM64 classifier: ' + classifier)
        libraries = [n for n in names if n.startswith(prefix + '/lib/')]
        if any('-linux-' in n or '-windows-' in n or '-macosx-x86_64' in n for n in libraries):
            raise ValueError('Mixed native runtime platforms in ' + prefix)


def copy_bundle(source_path, output, prefix):
    with zipfile.ZipFile(source_path) as source:
        for entry in checked_entries(source, prefix):
            with source.open(entry) as src, output.open(entry.filename, 'w') as dst:
                shutil.copyfileobj(src, dst)


def verify_compiled_classes(plugin, classes):
    paths = sorted(classes.rglob('*.class'))
    if not paths:
        raise ValueError('No compiled classes to compare with plugin JAR')
    with zipfile.ZipFile(plugin) as archive:
        for path in paths:
            name = path.relative_to(classes).as_posix()
            if archive.read(name) != path.read_bytes():
                raise ValueError('Plugin class differs from compiled class: ' + name)
    return len(paths)


def verify_macro_registration(archive):
    """SciJava writes concatenated JSON objects, not a JSON array."""
    try:
        remaining = archive.read('META-INF/json/org.scijava.plugin.Plugin').decode('utf-8')
    except KeyError as error:
        raise ValueError('Missing generated SciJava macro command index') from error
    entries, decoder = [], json.JSONDecoder()
    while remaining.strip():
        remaining = remaining.lstrip()
        item, end = decoder.raw_decode(remaining)
        entries.append(item)
        remaining = remaining[end:]
    matches = [item for item in entries if item.get('class') == 'Features.Macros.LegacyMacroStarDist'
               and item.get('values', {}).get('type') == 'org.scijava.command.Command']
    if len(matches) != 1:
        raise ValueError('Expected one generated LegacyMacroStarDist command registration')


def macro_overlay(root):
    """Generate only tracked, allowlisted legacy assets in a separate menu."""
    spec = importlib.util.spec_from_file_location('gat_macro_overlay', root / 'legacy-macros/build_overlay.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.generated_files(root=root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('dist'))
    parser.add_argument('--allow-dirty', action='store_true', help='For local candidates only; records dirty provenance')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    version = ET.parse(root / 'pom.xml').getroot().findtext('{http://maven.apache.org/POM/4.0.0}version')
    plugin = root / 'target' / ('GutAnalysisToolbox_-' + version + '.jar')
    inference = root / 'native-inference/target/gat-native-inference-macosx-arm64.zip'
    alignment = root / 'native-alignment/target/gat-native-alignment-macosx-arm64.zip'
    if not all(p.is_file() for p in [plugin, inference, alignment]):
        raise SystemExit('Build the root plugin and clean-build BOTH macosx-arm64 worker modules first.')
    with zipfile.ZipFile(plugin) as archive:
        names = set(archive.namelist())
        if not {'Features/Inference/NativeStarDist.class', 'Features/Inference/NativeAlignmentClient.class',
                'Features/Macros/LegacyMacroStarDist.class', 'Features/Macros/LegacyTemplateMatching.class'}.issubset(names):
            raise ValueError('Missing native adapters')
        verify_macro_registration(archive)
        if any(n.startswith(('org/tensorflow/', 'org/bytedeco/')) for n in names):
            raise ValueError('Native worker dependencies must not enter the Fiji plugin classpath')
    class_count = verify_compiled_classes(plugin, root / 'target/classes')
    validate_bundle(inference, 'gat-native-inference',
                    ['gat-native-inference/gat-native-inference.jar', 'gat-native-inference/THIRD_PARTY_NOTICES.md'],
                    ['tensorflow-core-native-'])
    validate_bundle(alignment, 'gat-native-alignment',
                    ['gat-native-alignment/gat-native-alignment.jar', 'gat-native-alignment/LICENSE',
                     'gat-native-alignment/THIRD_PARTY_NOTICES.md', 'gat-native-alignment/source/pom.xml',
                     'gat-native-alignment/source/src/main/java/TemplateMatching/NativeAlignmentMain.java',
                     'gat-native-alignment/source/src/main/java/TemplateMatching/Align_slices.java',
                     'gat-native-alignment/source/src/main/java/TemplateMatching/cvMatch_Template.java'],
                    ['opencv-', 'openblas-', 'javacpp-'])
    source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True).strip())
    if dirty and not args.allow_dirty:
        raise SystemExit('Release packaging requires a clean source checkout. Use --allow-dirty only for labelled local candidates.')
    macro_files, macro_metadata = macro_overlay(root)
    if macro_metadata['source_commit'] != source_commit:
        raise ValueError('Macro overlay source revision differs from plugin package revision')
    args.output.mkdir(parents=True, exist_ok=True)
    destination = args.output / ('GAT-' + version + '-macos-arm64-preview.zip')
    metadata = {
        'version': version, 'source_commit': source_commit, 'source_worktree_modified': dirty,
        'alignment_protocol_version': 2,
        'legacy_macro_overlay': True,
        'legacy_macro_manifest_sha256': hashlib.sha256(macro_files['MACROFORK_BUILD_INFO.json']).hexdigest(),
        'legacy_macro_script_assets': len(macro_metadata['files']),
        'legacy_macro_settings': 'Repository defaults; existing original installation is not changed',
        'target': 'macos-arm64', 'minimum_macos': '14', 'minimum_java': '11', 'experimental': True,
        'install_root': 'ImageJ data root containing jars and plugins; current Fiji Latest uses outer Fiji/, not inner Fiji.app/',
        'plugin_classes_match_compiled_classes': True, 'plugin_classes_compared': class_count,
        'plugin_sha256': hashlib.sha256(plugin.read_bytes()).hexdigest(),
        'inference_bundle_sha256': hashlib.sha256(inference.read_bytes()).hexdigest(),
        'alignment_bundle_sha256': hashlib.sha256(alignment.read_bytes()).hexdigest(),
        'validation_note': 'Class comparison establishes build consistency only. Test execution and outcomes are recorded separately; see START_HERE_PREVIEW_7.md and PREVIEW_7_RELEASE_NOTES.md. The older Java V2 workflow matrix is historical context.',
    }
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as output:
        output.write(plugin, 'plugins/' + plugin.name)
        for name, data in sorted(macro_files.items()):
            output.writestr(name, data)
        copy_bundle(inference, output, 'gat-native-inference')
        copy_bundle(alignment, output, 'gat-native-alignment')
        output.write(root / 'docs/preview-7-setup.md', 'APPLE_SILICON.md')
        output.write(root / 'docs/apple-silicon-workflow-matrix.md', 'apple-silicon-workflow-matrix.md')
        output.write(root / 'docs/preview-7-setup.md', 'START_HERE_PREVIEW_7.md')
        output.write(root / 'docs/preview-7-release-notes.md', 'PREVIEW_7_RELEASE_NOTES.md')
        output.write(root / 'docs/validation/maintainer-review-2026-10-06.md', 'MAINTAINER_REVIEW_2026-10-06.md')
        output.write(root / 'docs/validation/fork-hardening-2026-10-06.md', 'FORK_HARDENING_2026-10-06.md')
        output.write(root / 'LICENSE', 'GAT_LICENSE')
        output.writestr('BUILD_INFO.json', json.dumps(metadata, indent=2) + '\n')
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(destination.suffix + '.sha256').write_text(digest + '  ' + destination.name + '\n')
    print(destination)
    print(digest)


if __name__ == '__main__':
    main()
