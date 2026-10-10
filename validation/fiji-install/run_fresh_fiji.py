#!/usr/bin/env python3
"""Review-only matched native-Mac fresh Fiji validation. Never touches an existing Fiji."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import posixpath
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import zipfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / 'manifest.json').read_text())
OVERLAY_DOCUMENTS = ('BUILD_INFO.json', 'APPLE_SILICON.md',
                     'apple-silicon-workflow-matrix.md', 'GAT_LICENSE',
                     'PREVIEW_5_SETUP.md', 'MAINTAINER_REVIEW_2026-10-06.md',
                     'FORK_HARDENING_2026-10-06.md')
STAGES = ['native_host', 'archive_download', 'archive_integrity', 'archive_extraction',
          'bundled_java', 'pristine_startup', 'official_updater', 'installed_inventory', 'historical_runtime',
          'paired_overlays', 'original_startup', 'original_dashboard', 'original_neuron',
          'original_alignment', 'fork_startup', 'fork_dashboard', 'fork_neuron', 'fork_alignment',
          'official_engine_install', 'official_engine_inference', 'ganglia_engine_setup',
          'original_ganglia', 'fork_ganglia', 'ganglia_command', 'opencl_workflows', 'full_interactive_workflows']


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def safe_archive(path, required_prefix=None, allow_symlinks=False):
    """Validate before ditto/ZipFile extraction, including symlink ancestor attacks."""
    seen, links = set(), set()
    with zipfile.ZipFile(path) as z:
        total = 0
        for entry in z.infolist():
            name = entry.filename.rstrip('/')
            p = PurePosixPath(name)
            if (not name or p.is_absolute() or '..' in p.parts or '\\' in name
                    or (required_prefix and p.parts[0] != required_prefix)):
                raise ValueError('Unsafe archive member: ' + name)
            if str(p) in seen:
                raise ValueError('Duplicate archive member: ' + name)
            seen.add(str(p))
            if entry.flag_bits & 1:
                raise ValueError('Encrypted archive entry: ' + name)
            total += entry.file_size
            if total > 8 * 1024**3:
                raise ValueError('Archive expands beyond 8 GiB')
            mode = entry.external_attr >> 16
            if stat.S_ISLNK(mode):
                if not allow_symlinks:
                    raise ValueError('Symlinks forbidden in overlay')
                target = z.read(entry).decode('utf-8')
                resolved = posixpath.normpath(posixpath.join(str(p.parent), target))
                if (target.startswith('/') or '\\' in target or resolved.startswith('../')
                        or (required_prefix and not resolved.startswith(required_prefix + '/'))):
                    raise ValueError('Archive symlink escapes Fiji: ' + name)
                links.add(str(p))
            elif stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ValueError('Special file forbidden: ' + name)
        for name in seen:
            if any(str(parent) in links for parent in PurePosixPath(name).parents):
                raise ValueError('Archive member writes through symlink: ' + name)
    return total


def clean_env(home):
    env = os.environ.copy()
    # Preserve CI infrastructure but ignore inherited Java/plugin/runtime choices.
    for key in ('CLASSPATH', 'JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS', 'JAVA_HOME',
                'DYLD_LIBRARY_PATH', 'DYLD_FALLBACK_LIBRARY_PATH', 'JYTHONPATH', 'PYTHONPATH'):
        env.pop(key, None)
    env['HOME'] = str(home)
    return env


def execute(command, log, env, timeout=240, cwd=None):
    start = time.monotonic()
    with log.open('w') as f:
        p = subprocess.Popen([str(c) for c in command], stdout=f, stderr=subprocess.STDOUT,
                             env=env, cwd=cwd, stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            code = p.wait(timeout=timeout)
            expired = False
        except subprocess.TimeoutExpired:
            expired = True
            os.killpg(p.pid, signal.SIGTERM)
            try:
                code = p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                code = p.wait()
    return {'command': [str(c) for c in command], 'exit_code': code, 'timeout': expired,
            'seconds': time.monotonic() - start, 'log': log.name}


def download(url, path, env, log, expected_sha=None, expected_size=None, timeout=1200):
    if not url.startswith('https://'):
        raise ValueError('HTTPS is required')
    result = execute(['curl', '--fail', '--location', '--silent', '--show-error', '--proto', '=https',
                      '--proto-redir', '=https', '--retry', '2', '--connect-timeout', '30',
                      '--max-time', str(timeout - 15), '--output', path, url], log, env, timeout)
    if result['exit_code'] or result['timeout']:
        raise RuntimeError('Download failed; see ' + log.name)
    digest = sha256(path)
    if expected_size is not None and path.stat().st_size != expected_size:
        raise ValueError('Archive byte length does not match the pinned publisher record')
    if expected_sha is not None and digest != expected_sha:
        raise ValueError('SHA-256 mismatch: ' + path.name)
    return {'url': url, 'sha256': digest, 'bytes': path.stat().st_size, 'execution': result}


def inventory(root):
    records = []
    for folder in ('jars', 'plugins', 'models', 'engines', 'gat-native-inference', 'gat-native-alignment'):
        directory = root / folder
        if not directory.exists():
            continue
        for path in sorted(directory.rglob('*')):
            if path.is_file():
                if not path.resolve().is_relative_to(root.resolve()):
                    raise ValueError('Installed asset escaped fixture: ' + str(path))
                records.append({'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size,
                                'sha256': sha256(path)})
    return records


def compare_pins(records):
    rows = []
    for pin in MANIFEST['expected_plugin_artifacts'] + MANIFEST['models']:
        matches = [r for r in records if Path(r['path']).name == pin['file']]
        status = 'MATCH' if len(matches) == 1 and matches[0]['sha256'] == pin['sha256'] else 'MISSING' if not matches else 'CONFLICT'
        rows.append({'file': pin['file'], 'expected_sha256': pin['sha256'], 'status': status, 'installed': matches})
    return rows



def verify_required_assets(root, records):
    """Read-only strict verifier, including after the separate explicit CI runtime preparation."""
    verified = []
    for record in records:
        path = root / record['path']
        if not path.is_file() or sha256(path) != record['sha256']:
            raise ValueError('Updater asset conflicts with ganglia validation pin: ' + record['path'])
        verified.append({'path': record['path'], 'sha256': record['sha256']})
    return verified


def verify_engine_files(directory, artifacts, include_native=False):
    """An empty/partial engine folder can never satisfy initialization."""
    required = [a for a in artifacts if include_native or 'platform' not in a]
    expected = {a['filename'] for a in required}
    actual = {p.name for p in directory.glob('*.jar')}
    if actual != expected:
        raise ValueError('Engine jar inventory conflicts with pins: missing=' + str(sorted(expected-actual))
                         + ', extra=' + str(sorted(actual-expected)))
    return verify_required_assets(directory, [{'path': a['filename'], 'sha256': a['sha256']} for a in required])


def overlay(root, plugin=None, archive=None, source_commit=None, evidence=None):
    if (plugin is None) == (archive is None):
        raise ValueError('Exactly one explicit GAT plugin or preview archive is required')
    if archive:
        safe_archive(archive)
        with zipfile.ZipFile(archive) as z:
            info = json.loads(z.read('BUILD_INFO.json'))
            if info['source_commit'] != source_commit or info['source_worktree_modified']:
                raise ValueError('Fork BUILD_INFO must match a clean requested source commit')
            files = [n for n in z.namelist() if n.startswith('plugins/') and n.endswith('.jar')]
            if len(files) != 1:
                raise ValueError('Fork overlay must contain exactly one GAT plugin')
            for name in z.namelist():
                p = PurePosixPath(name)
                # Documentation is allowed only at these exact root paths, not
                # as a directory prefix that could admit an unrelated payload.
                if (p.parts[0] not in ('gat-native-inference', 'gat-native-alignment')
                        and name not in OVERLAY_DOCUMENTS and name not in (files[0], 'plugins/')):
                    raise ValueError('Unexpected overlay path: ' + name)
            import io
            with zipfile.ZipFile(io.BytesIO(z.read(files[0]))) as jar:
                validate_gat_jar(jar)
    else:
        with zipfile.ZipFile(plugin) as jar:
            validate_gat_jar(jar)
    backups = []
    for directory in ('plugins', 'jars'):
        for path in sorted((root / directory).rglob('*.jar')):
            with zipfile.ZipFile(path) as z:
                is_gat = 'UI/GatPluginUI.class' in z.namelist()
            if is_gat:
                relative = path.relative_to(root)
                target = evidence / 'displaced-updater-GAT' / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                backups.append({'path': relative.as_posix(), 'sha256': sha256(path)})
                shutil.move(str(path), str(target))
    if archive:
        with zipfile.ZipFile(archive) as z:
            z.extractall(root)
    else:
        shutil.copy2(plugin, root / 'plugins' / plugin.name)
    return {'source_commit': source_commit, 'overlay_sha256': sha256(archive or plugin),
            'displaced_GAT_only': backups, 'runtime_dependency_jars_changed': False}


def validate_gat_jar(jar):
    names = jar.namelist()
    if 'UI/GatPluginUI.class' not in names or 'plugins.config' not in names:
        raise ValueError('Missing GATV2 entry point or plugin registration')
    if any(n.startswith(('org/tensorflow/', 'org/bytedeco/')) for n in names):
        raise ValueError('Isolated worker runtime leaked into GAT plugin')


# No caller-supplied installation can enter the historical test path. These
# identities are populated only by this process's fresh-allocation/extraction flow.
_FRESH_WORKSPACES = {}
_FRESH_INSTALLATIONS = {}
HISTORICAL_URLS = {
    'jars/dl-modelrunner-0.6.4.jar': 'https://sites.imagej.net/DeepImageJ/jars/dl-modelrunner-0.6.4.jar-20261006095051',
    'plugins/DeepImageJ-3.2.1-SNAPSHOT.jar': 'https://sites.imagej.net/DeepImageJ/plugins/DeepImageJ-3.2.1-SNAPSHOT.jar-20261006085316',
}


def file_identity(path):
    st = path.lstat()
    return st.st_dev, st.st_ino


def create_work_root():
    parent = Path(os.environ.get('RUNNER_TEMP') or tempfile.gettempdir()).resolve(strict=True)
    work = Path(tempfile.mkdtemp(prefix='gat-fresh-fiji-', dir=parent))
    _FRESH_WORKSPACES[work] = file_identity(work)
    return work


def safe_fixture_path(path, ancestor):
    """Require literal, non-symlink paths beneath a trusted newly allocated root."""
    if not path.is_absolute() or '..' in path.parts or not path.is_relative_to(ancestor):
        raise ValueError('Path is outside the fresh temporary fixture: ' + str(path))
    current = path
    while True:
        if current.is_symlink():
            raise ValueError('Symlink forbidden in historical runtime target: ' + str(current))
        if current == ancestor:
            break
        current = current.parent
    if path.resolve() != path:
        raise ValueError('Historical runtime path is not canonical: ' + str(path))


def register_fresh_installation(root, work, archive_record):
    """Called only after the pinned distribution has been safely unpacked."""
    if (work not in _FRESH_WORKSPACES or file_identity(work) != _FRESH_WORKSPACES[work]
            or root != work / 'official' / 'Fiji'):
        raise ValueError('Historical runtime requires this process\'s fresh Fiji workspace')
    safe_fixture_path(root, work)
    if (archive_record['sha256'] != MANIFEST['fiji']['sha256']
            or archive_record['bytes'] != MANIFEST['fiji']['bytes']):
        raise ValueError('Cannot register an unverified Fiji extraction')
    _FRESH_INSTALLATIONS[root] = file_identity(root)


def historical_artifacts():
    """Exactly two official timestamped URLs, retaining the original ganglia pins."""
    records = MANIFEST['historical_runtime']['artifacts']
    if len(records) != 2 or {r['path'] for r in records} != set(HISTORICAL_URLS):
        raise ValueError('Historical runtime target allowlist must contain exactly the two dependency jars')
    pins = MANIFEST['ganglia_engine']['required_updater_assets']
    for record in records:
        matching = [p for p in pins if p['path'] == record['path']]
        if (record['url'] != HISTORICAL_URLS[record['path']] or len(matching) != 1
                or record['sha256'] != matching[0]['sha256']
                or not re.fullmatch('[0-9a-f]{64}', record['sha256'])
                or not isinstance(record['bytes'], int) or record['bytes'] <= 0):
            raise ValueError('Historical runtime URL/hash/length conflicts with the fixed allowlist')
    return records


def full_inventory(root):
    """All regular files and symlink targets, including files outside jars/models."""
    records = []
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            if not path.resolve().is_relative_to(root):
                raise ValueError('Installed symlink escaped fresh fixture: ' + relative)
            records.append({'path': relative, 'symlink': os.readlink(path)})
        elif path.is_file():
            records.append({'path': relative, 'bytes': path.stat().st_size, 'sha256': sha256(path)})
        elif not path.is_dir():
            raise ValueError('Special file in fresh fixture: ' + relative)
    return records


def historical_inventory_delta(before, after, artifacts):
    def index(records):
        rows = {r['path']: r for r in records}
        if len(rows) != len(records):
            raise ValueError('Duplicate inventory path')
        return rows
    old, new = index(before), index(after)
    if set(old) != set(new):
        raise ValueError('Historical runtime added or removed an installed file')
    allowed = {a['path']: a for a in artifacts}
    expected = {p for p, a in allowed.items() if old[p].get('sha256') != a['sha256']}
    changed = {p for p in old if old[p] != new[p]}
    if changed != expected:
        raise ValueError('Historical runtime inventory changed outside the exact expected dependency delta')
    for path, artifact in allowed.items():
        if new[path].get('sha256') != artifact['sha256'] or new[path].get('bytes') != artifact['bytes']:
            raise ValueError('Historical runtime final dependency hash/length mismatch: ' + path)
    return [{'path': p, 'before': old[p], 'after': new[p]} for p in sorted(changed)]


def validate_historical_targets(root, work, artifacts):
    if (work not in _FRESH_WORKSPACES or file_identity(work) != _FRESH_WORKSPACES[work]
            or root != work / 'official' / 'Fiji' or root not in _FRESH_INSTALLATIONS
            or file_identity(root) != _FRESH_INSTALLATIONS[root]):
        raise ValueError('Historical runtime only accepts the freshly unpacked temporary CI Fiji')
    safe_fixture_path(root, work)
    for artifact in artifacts:
        target = root / artifact['path']
        safe_fixture_path(target, work)
        if not target.is_file() or target.stat().st_nlink != 1:
            raise ValueError('Historical runtime requires one existing regular, unlinked jar: ' + artifact['path'])
        # Reject alternate versions/nested copies that could shadow the pinned jar.
        family = 'dl-modelrunner-[0-9]*.jar' if target.name.startswith('dl-modelrunner-') else 'DeepImageJ-*.jar'
        matches = sorted(p for folder in ('jars', 'plugins') for p in (root / folder).rglob(family))
        if matches != [target]:
            raise ValueError('Duplicate or shadowing historical runtime jar: ' + artifact['path'])


def configure_runtime(root, work_root, evidence, env, historical=False):
    if not historical:
        return {'mode': 'official-updater', 'status': 'SKIPPED',
                'reason': 'Explicit --historical-runtime was not supplied; updater dependencies unchanged'}
    return apply_historical_runtime(root, work_root, evidence, env)


def apply_historical_runtime(root, work_root, evidence, env):
    """Explicit CI-only experiment; never repairs the default official-updater lane."""
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise ValueError('--historical-runtime is restricted to disposable GitHub Actions CI')
    artifacts = historical_artifacts()
    validate_historical_targets(root, work_root, artifacts)
    if evidence.resolve().is_relative_to(work_root) or evidence.is_symlink():
        raise ValueError('Historical runtime evidence must be outside the temporary runtime workspace')
    staging = work_root / 'historical-runtime'
    staging.mkdir()  # No reuse, cached binaries or pre-existing symlink destinations.
    downloads = staging / 'downloads'; downloads.mkdir()
    backups = staging / 'displaced'; backups.mkdir()
    audit_path = evidence / 'historical-runtime-audit.json'
    for name in ('historical-runtime-audit.json', 'historical-runtime-before.json', 'historical-runtime-after.json'):
        if (evidence / name).exists() or (evidence / name).is_symlink():
            raise ValueError('Historical runtime evidence already exists: ' + name)
    audit = {'mode': 'historical-test-only', 'status': 'RUNNING',
             'scope': 'Two official historical dependencies in a disposable freshly unpacked CI Fiji only',
             'root': str(root), 'backup_root': str(backups), 'artifacts': [],
             'before_inventory': 'historical-runtime-before.json',
             'after_inventory': 'historical-runtime-after.json'}
    def save():
        audit_path.write_text(json.dumps(audit, indent=2) + '\n')
    before = full_inventory(root)
    (evidence / audit['before_inventory']).write_text(json.dumps(before, indent=2) + '\n')
    save()
    try:
        # Verify *both* downloads before displacing either installed jar.
        for index, artifact in enumerate(artifacts):
            source = downloads / Path(artifact['path']).name
            record = {**artifact, 'status': 'DOWNLOADING'}
            audit['artifacts'].append(record); save()
            fetched = download(artifact['url'], source, env,
                               evidence / ('historical-runtime-download-%d.log' % index),
                               expected_sha=artifact['sha256'], expected_size=artifact['bytes'], timeout=180)
            if (source.is_symlink() or not source.is_file() or sha256(source) != artifact['sha256']
                    or source.stat().st_size != artifact['bytes']):
                raise ValueError('Historical runtime downloaded hash/length mismatch: ' + artifact['path'])
            record['download'] = fetched
            record['status'] = 'VERIFIED'
            save()
        validate_historical_targets(root, work_root, artifacts)
        if full_inventory(root) != before:
            raise ValueError('Fresh Fiji changed while historical dependencies were downloading')
        for artifact in audit['artifacts']:
            target = root / artifact['path']
            artifact['displaced_sha256'] = sha256(target)
            artifact['replaced'] = artifact['displaced_sha256'] != artifact['sha256']
            if artifact['replaced']:
                backup = backups / artifact['path']; backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
                if sha256(backup) != artifact['displaced_sha256']:
                    raise ValueError('Historical runtime backup hash mismatch')
                artifact['backup'] = str(backup)
                # Replace the pathname, never modify an existing jar inode in place.
                os.replace(downloads / target.name, target)
            save()
        after = full_inventory(root)
        (evidence / audit['after_inventory']).write_text(json.dumps(after, indent=2) + '\n')
        audit['inventory_delta'] = historical_inventory_delta(before, after, artifacts)
        audit['status'] = 'PASS'
        save()
        return audit
    except Exception as exc:
        audit['status'] = 'FAIL'; audit['reason'] = str(exc)
        for record in audit['artifacts']:
            source = downloads / Path(record['path']).name
            if source.is_file() and not source.is_symlink():
                record['observed_download_sha256'] = sha256(source)
                record['observed_download_bytes'] = source.stat().st_size
        try:
            (evidence / audit['after_inventory']).write_text(json.dumps(full_inventory(root), indent=2) + '\n')
        except Exception as inventory_error:
            audit['after_inventory_error'] = str(inventory_error)
        save()
        raise


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--original-jar', required=True, type=Path)
    parser.add_argument('--fork-archive', required=True, type=Path)
    parser.add_argument('--original-commit', default='1870d9e16e16fd6daeac0bd05122e851029ddedc')
    parser.add_argument('--fork-commit', required=True)
    parser.add_argument('--historical-runtime', action='store_true',
                        help='CI-only: replace exactly two dependency jars with pinned official historical bytes')
    parser.add_argument('--control-jar', type=Path, help='Optional immutable preview-5 control plugin')
    parser.add_argument('--control-commit', help='Full immutable SHA paired with --control-jar')
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    if (args.control_jar is None) != (args.control_commit is None):
        parser.error('--control-jar and --control-commit must be provided together')
    commits = [args.original_commit, args.fork_commit] + ([args.control_commit] if args.control_commit else [])
    if any(not re.fullmatch('[0-9a-f]{40}', s) for s in commits):
        parser.error('Provide full immutable commit SHAs')
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    report_path = args.output / 'fresh-fiji-report.json'
    if report_path.exists():
        parser.error('Output already contains a report; choose a new evidence directory')
    work = create_work_root()
    variants = ('original', 'control', 'fork') if args.control_jar else ('original', 'fork')
    home = work / 'home'; home.mkdir()
    env = clean_env(home)
    report = {'schema_version': 1, 'scope': 'Matched bounded installed-Fiji validation, not all GAT workflows',
              'prepared_manifest_sha256': sha256(HERE / 'manifest.json'), 'work_root': str(work),
              'runtime_mode': 'historical-test-only' if args.historical_runtime else 'official-updater',
              'control_commit': args.control_commit,
              'stages': {stage: {'status': 'BLOCKED', 'reason': 'Not reached'} for stage in STAGES}}
    if args.control_jar:
        for name in ('control_startup', 'control_ganglia', 'original_parity', 'control_parity', 'fork_parity',
                     'parity_samples', 'ganglia_parity'):
            report['stages'][name] = {'status': 'BLOCKED', 'reason': 'Not reached'}
    def save():
        report_path.write_text(json.dumps(report, indent=2) + '\n')
    def stage(name, status, **data):
        report['stages'][name] = {'status': status, **data}; save(); print(name + ': ' + status, flush=True)
    def command(cmd, filename, timeout=240, cwd=None):
        execution = execute(cmd, args.output / filename, env, timeout, cwd)
        if execution['exit_code'] or execution['timeout']:
            raise RuntimeError('Command failed or timed out; inspect ' + filename)
        return execution
    def runtime_home(root):
        selected = work / ('home-' + root.parent.name)
        selected.mkdir(exist_ok=True)
        return selected
    def launch(root):
        return [root / MANIFEST['fiji']['launcher'], '--java-home=' + str(root / MANIFEST['fiji']['java_home']),
                '--allow-multiple', '--no-splash', '--heap=1536m', '-Duser.home=' + str(runtime_home(root)),
                '-XX:ActiveProcessorCount=2', '-Dai.djl.pytorch.num_threads=1', '-Dai.djl.pytorch.num_interop_threads=1']
    def install_probe(root):
        ij = list((root / 'jars').glob('ij-*.jar'))
        if len(ij) != 1:
            raise ValueError('Expected exactly one ImageJ1 core jar; do not guess among duplicates')
        classes = work / ('probe-classes-' + root.parent.name); classes.mkdir()
        command([root / MANIFEST['fiji']['java_home'] / 'bin/javac', '--release', '11', '-cp', ij[0],
                 '-d', classes, HERE / 'Fresh_Fiji_Probe.java'], 'probe-compile-' + root.parent.name + '.log')
        with zipfile.ZipFile(root / 'plugins' / 'Fresh_Fiji_Probe.jar', 'w') as z:
            for path in classes.glob('*.class'):
                z.write(path, path.name)
            z.writestr('plugins.config', 'Plugins>GAT Validation, "GAT Fresh Install Probe", Fresh_Fiji_Probe\n')
    def install_ganglia_probe(root):
        classes = work / 'ganglia-probe-classes'; classes.mkdir()
        jars = sorted((root / 'jars').rglob('*.jar')) + sorted((root / 'plugins').rglob('*.jar'))
        cp = os.pathsep.join(str(p) for p in jars)
        sources = [HERE / 'Fresh_Ganglia_Probe.java', HERE / 'Fresh_Ganglia_Params.java',
                   HERE / 'Fresh_Ganglia_Evidence.java']
        if (HERE / 'Fresh_Ganglia_Parity.java').is_file():
            sources.append(HERE / 'Fresh_Ganglia_Parity.java')
        command([root / MANIFEST['fiji']['java_home'] / 'bin/javac', '--release', '11', '-cp', cp,
                 '-d', classes] + sources, 'ganglia-probe-compile.log')
        with zipfile.ZipFile(root / 'plugins' / 'Fresh_Fiji_Probe.jar', 'a') as z:
            for path in classes.glob('*.class'):
                z.write(path, path.name)
    parity_samples = work / 'parity-samples'
    def probe(root, variant, mode, fixture=None):
        name = variant + '_' + mode
        target = args.output / (name + '.json')
        macro = work / (name + '.ijm')
        macro.write_text('run("GAT Fresh Install Probe");\n')
        cmd = launch(root) + ['-Dgat.validation.root=' + str(root), '-Dgat.validation.mode=' + mode,
                             '-Dgat.validation.report=' + str(target),
                             '-Dgat.validation.expectedLabels=' + MANIFEST['expected_neuron_label_sha256']]
        if mode == 'parity':
            cmd += ['-Dgat.validation.paritySamples=' + str(parity_samples)]
        if fixture:
            cmd += ['-Dgat.validation.fixture=' + str(fixture)]
        cmd += ['--run', str(macro)]
        execution = execute(cmd, args.output / (name + '.log'), clean_env(runtime_home(root)), 1200 if mode == 'parity' else 900 if mode == 'engine_install' else 300, root)
        if target.exists():
            result = json.loads(target.read_text())
            status = result.get('status')
            if status not in ('PASS', 'FAIL', 'BLOCKED'):
                status = 'FAIL'
            if status == 'PASS' and (execution['exit_code'] or execution['timeout']):
                status = 'FAIL'
            stage(name, status, execution=execution, evidence=target.name)
        else:
            stage(name, 'FAIL', reason='Launcher never produced its plugin evidence', execution=execution)
        return report['stages'][name]['status']
    current = 'native_host'
    try:
        save()
        if args.historical_runtime and os.environ.get('GITHUB_ACTIONS') != 'true':
            raise ValueError('--historical-runtime is restricted to disposable GitHub Actions CI')
        if platform.system() != 'Darwin' or platform.machine() != 'arm64':
            stage(current, 'BLOCKED', reason='This lane requires a native macOS arm64 GUI runner; no emulation or Linux substitution')
            return 3
        minimum_gib = 16 if args.control_jar else 12
        if shutil.disk_usage(work).free < minimum_gib * 1024**3:
            raise RuntimeError('Need at least %d GiB free for the isolated installations' % minimum_gib)
        command(['sh', '-c', 'uname -a; sw_vers; sysctl -n machdep.cpu.brand_string'], 'host.log')
        stage(current, 'PASS', evidence='host.log')
        current = 'archive_download'; archive = work / 'fiji.zip'
        record = download(MANIFEST['fiji']['url'], archive, env, args.output / 'download.log')
        stage(current, 'PASS', **record)
        current = 'archive_integrity'
        if record['sha256'] != MANIFEST['fiji']['sha256'] or record['bytes'] != MANIFEST['fiji']['bytes']:
            raise ValueError('Pinned publisher archive SHA-256/length mismatch; refusing extraction')
        expanded = safe_archive(archive, required_prefix='Fiji', allow_symlinks=True)
        stage(current, 'PASS', sha256=record['sha256'], expanded_bytes=expanded)
        current = 'archive_extraction'; base = work / 'official' / 'Fiji'
        (work / 'official').mkdir()
        command(['/usr/bin/ditto', '-x', '-k', archive, work / 'official'], 'extract.log', 180)
        for path in base.rglob('*'):
            if path.is_symlink() and not path.resolve().is_relative_to(base.resolve()):
                raise ValueError('Extracted symlink escaped Fiji')
        register_fresh_installation(base, work, record)
        stage(current, 'PASS', root=str(base), no_quarantine_or_security_changes=True)
        current = 'bundled_java'; java = base / MANIFEST['fiji']['java_home'] / 'bin/java'
        command(['/usr/bin/file', base / MANIFEST['fiji']['launcher'], java], 'native-binaries.log')
        result = command([java, '-XshowSettings:properties', '-version'], 'bundled-java.log')
        java_text=(args.output / 'bundled-java.log').read_text()
        if not re.search(r'os.arch\s*=\s*(aarch64|arm64)', java_text):
            raise ValueError('Bundled Java does not report arm64')
        stage(current, 'PASS', execution=result)
        install_probe(base)
        current = 'pristine_startup'
        if probe(base, 'pristine', 'startup') != 'PASS':
            raise RuntimeError('Pristine Fiji launcher startup failed; no updater/overlay was attempted')
        current = 'official_updater'
        command(launch(base) + ['--update', 'list-update-sites'], 'sites-before.log', 240, base)
        db_dir = args.output / 'updater-databases'; db_dir.mkdir()
        metadata = []
        for i, site in enumerate(MANIFEST['sites']):
            # Supported updater operation activates an existing site or creates an absent one.
            command(launch(base) + ['--update', 'edit-update-site', site['name'], site['url']],
                    'site-%02d.log' % i, 240, base)
            metadata.append(download(site['url'].rstrip('/') + '/db.xml.gz', db_dir / ('site-%02d.xml.gz' % i),
                                     env, args.output / ('site-db-%02d.log' % i), timeout=120))
        command(launch(base) + ['--update', 'update'], 'updater-install.log', 1800, base)
        text=(args.output / 'updater-install.log').read_text(errors='replace')
        if re.search(r'\[ERROR\]|Could not update due to conflicts|Error updating|IO error downloading|Skipping obsolete, but modified', text):
            raise RuntimeError('Updater reported errors/conflicts; historical mode never bypasses an updater failure')
        command(launch(base) + ['--update', 'list-update-sites'], 'sites-after.log', 240, base)
        command(launch(base) + ['--update', 'list-current'], 'updater-current.log', 240, base)
        command(launch(base) + ['--update', 'list-shadowed'], 'updater-shadowed.log', 240, base)
        if (base / 'db.xml.gz').exists():
            shutil.copy2(base / 'db.xml.gz', db_dir / 'installed.xml.gz')
        stage(current, 'PASS', site_database_snapshots=metadata,
              note='Supported updater resolution; live sites are inventory-locked, not a replayable historical snapshot')
        current = 'installed_inventory'; records = inventory(base)
        (args.output / 'installed-inventory.json').write_text(json.dumps(records, indent=2)+'\n')
        pins = compare_pins(records)
        (args.output / 'pin-comparison.json').write_text(json.dumps(pins, indent=2)+'\n')
        stage(current, 'PASS', evidence='installed-inventory.json', pin_comparison='pin-comparison.json',
              pin_conflicts=[p for p in pins if p['status'] != 'MATCH'])
        current = 'historical_runtime'
        audit = configure_runtime(base, work, args.output, env, historical=args.historical_runtime)
        if args.historical_runtime:
            stage(current, 'PASS', mode='historical-test-only', evidence='historical-runtime-audit.json',
                  changed_paths=[r['path'] for r in audit['inventory_delta']])
        else:
            stage(current, 'SKIPPED', mode='official-updater', reason='Explicit --historical-runtime was not supplied; updater dependencies unchanged')
        fixture = work / 'public-Hu.tif'
        report['fixture'] = download(MANIFEST['fixture']['url'], fixture, env, args.output / 'fixture-download.log',
                                     expected_sha=MANIFEST['fixture']['sha256'], timeout=120)
        if args.control_jar:
            current = 'parity_samples'
            parity_samples.mkdir()
            samples = []
            for index, sample in enumerate(MANIFEST['parity_samples']):
                if sample['file'] != Path(sample['file']).name or sample['file'] in ('.', '..'):
                    raise ValueError('Unsafe parity sample filename')
                samples.append(download(sample['url'], parity_samples / sample['file'], env,
                                        args.output / ('parity-sample-%d.log' % index),
                                        expected_sha=sample['sha256'], expected_size=sample['bytes'], timeout=180))
            stage(current, 'PASS', samples=samples)
        # Complete real DeepImageJ/JDLL engine setup before copying the matched installations.
        current = 'ganglia_engine_setup'
        config = MANIFEST['ganglia_engine']
        validated_assets = verify_required_assets(base, config['required_updater_assets'])
        if probe(base, 'official', 'engine_install') != 'PASS':
            raise RuntimeError('The supported JDLL installer failed; inspect official_engine_install evidence')
        current = 'ganglia_engine_setup'
        engine_dir = base / 'engines' / config['directory']
        installer_files = verify_engine_files(engine_dir, config['artifacts'])
        native = [a for a in config['artifacts'] if a.get('platform') == 'macosx-arm64']
        if len(native) != 1:
            raise ValueError('Exactly one pinned native CPU jar is required')
        native = native[0]
        native_stage = work / native['filename']
        native_download = download(native['url'], native_stage, env, args.output / 'ganglia-native-download.log',
                                   expected_sha=native['sha256'], timeout=300)
        # The supported installer has already created a real verified engine here.
        # Add its exact official native CPU binary; never fabricate readiness with an empty directory.
        shutil.copy2(native_stage, engine_dir / native['filename'])
        final_engine_files = verify_engine_files(engine_dir, config['artifacts'], include_native=True)
        install_ganglia_probe(base)
        if probe(base, 'official', 'engine_inference') != 'PASS':
            raise RuntimeError('Real full-model JDLL load/inference failed; engine setup is not validated')
        stage(current, 'PASS', installer='official_engine_install.json', inference='official_engine_inference.json',
              model_and_installed_runtime_pins=validated_assets, installer_files=installer_files,
              verified_engine_files=final_engine_files, native_cpu_download=native_download,
              note='Shipped JDLL installer plus exact pinned official native CPU jar; completed full model inference before copying either installation')
        (args.output / 'engine-ready-inventory.json').write_text(json.dumps(inventory(base), indent=2)+'\n')
        # All source revisions use the same audited dependency bytes on the same native host.
        current = 'paired_overlays'; overlays = {}
        for variant in variants:
            root = work / variant / 'Fiji'
            shutil.copytree(base, root, symlinks=True)
            evidence = args.output / variant; evidence.mkdir()
            plugin = args.original_jar if variant == 'original' else args.control_jar if variant == 'control' else None
            commit = args.original_commit if variant == 'original' else args.control_commit if variant == 'control' else args.fork_commit
            overlays[variant] = overlay(root, plugin=plugin.resolve() if plugin else None,
                                      archive=args.fork_archive.resolve() if variant=='fork' else None,
                                      source_commit=commit,
                                      evidence=evidence)
        stage(current, 'PASS', overlays=overlays)
        for variant in variants:
            root = work / variant / 'Fiji'
            current = variant + '_startup'
            if probe(root, variant, 'startup') != 'PASS':
                continue
            if variant != 'control':
                current = variant + '_dashboard'
                probe(root, variant, 'dashboard')
            # A blocked dashboard remains blocked; the named API smokes are separate evidence.
            modes = ('ganglia', 'parity') if variant == 'control' else (
                ('neuron', 'alignment', 'ganglia', 'parity') if args.control_jar else ('neuron', 'alignment', 'ganglia'))
            for mode in modes:
                current = variant + '_' + mode
                if mode=='neuron' and any(p['status']!='MATCH' for p in pins if p['file']=='2D_enteric_neuron_v4_1.zip'):
                    stage(variant+'_neuron','BLOCKED',reason='Updater-installed neuron model differs from pinned reference; no substitution')
                else:
                    probe(root, variant, mode, fixture)
            (args.output / (variant+'-final-inventory.json')).write_text(json.dumps(inventory(root),indent=2)+'\n')
        if args.control_jar:
            current = 'ganglia_parity'
            comparison = command([sys.executable, HERE / 'compare_ganglia_parity.py', '--directory', args.output],
                                 'ganglia-parity-comparison.log', 180)
            summary = json.loads((args.output / 'ganglia-parity-summary.json').read_text())
            if summary.get('status') != 'PASS':
                raise ValueError('Three-way ganglia parity summary did not report PASS')
            stage(current, 'PASS', evidence='ganglia-parity-summary.json', execution=comparison)
        stage('ganglia_command', report['stages']['fork_ganglia']['status'], evidence='fork_ganglia.json',
              note='Real installed-Fiji GAT command; original observation is separately recorded in original_ganglia.json')
        stage('opencl_workflows','BLOCKED',reason='Native virtual M1 runner has no exposed OpenCL devices; requires a physical-device lane')
        stage('full_interactive_workflows','BLOCKED',reason='Biological review, parameter UI, every workflow, and physical-Mac Finder/Gatekeeper first-open are outside this bounded lane')
    except Exception as exc:
        stage(current, 'FAIL', reason=str(exc))
    finally:
        report['complete_workflow_support'] = False
        report['no_existing_installation_modified'] = True
        report['interpretation'] = 'PASS applies only to a named completed stage. Original failures are observations, not automatically a successful before/after claim. No all-workflow PASS is possible in this lane.'
        save()
    # Expected original API failures do not fail the paired smoke acceptance gate.
    required = ['native_host','archive_download','archive_integrity','archive_extraction','bundled_java',
                'pristine_startup','official_updater','installed_inventory','paired_overlays',
                'original_startup','fork_startup','fork_dashboard','fork_neuron','fork_alignment',
                'ganglia_engine_setup','official_engine_inference','fork_ganglia']
    if args.historical_runtime:
        required.append('historical_runtime')
    if args.control_jar:
        required += ['control_startup', 'control_ganglia',
                     'original_parity', 'control_parity', 'fork_parity', 'parity_samples', 'ganglia_parity']
    states = [report['stages'][s]['status'] for s in required]
    return 0 if all(s == 'PASS' for s in states) else 2 if 'FAIL' in states else 3


if __name__ == '__main__':
    raise SystemExit(main())
