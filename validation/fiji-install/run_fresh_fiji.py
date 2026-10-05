#!/usr/bin/env python3
"""Review-only paired native-Mac fresh Fiji validation. Never touches an existing Fiji."""
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
import tempfile
import time
import zipfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / 'manifest.json').read_text())
STAGES = ['native_host', 'archive_download', 'archive_integrity', 'archive_extraction',
          'bundled_java', 'pristine_startup', 'official_updater', 'installed_inventory',
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
    """Never replace updater-installed model, descriptor, macro or JDLL files to meet pins."""
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
                if p.parts[0] not in ('plugins', 'gat-native-inference', 'gat-native-alignment',
                                     'BUILD_INFO.json', 'APPLE_SILICON.md', 'apple-silicon-workflow-matrix.md', 'GAT_LICENSE'):
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--original-jar', required=True, type=Path)
    parser.add_argument('--fork-archive', required=True, type=Path)
    parser.add_argument('--original-commit', default='1870d9e16e16fd6daeac0bd05122e851029ddedc')
    parser.add_argument('--fork-commit', required=True)
    args = parser.parse_args()
    if any(not re.fullmatch('[0-9a-f]{40}', s) for s in (args.original_commit, args.fork_commit)):
        parser.error('Provide full immutable commit SHAs')
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    report_path = args.output / 'fresh-fiji-report.json'
    if report_path.exists():
        parser.error('Output already contains a report; choose a new evidence directory')
    work = Path(tempfile.mkdtemp(prefix='gat-fresh-fiji-', dir=os.environ.get('RUNNER_TEMP')))
    home = work / 'home'; home.mkdir()
    env = clean_env(home)
    report = {'schema_version': 1, 'scope': 'Paired bounded installed-Fiji validation, not all GAT workflows',
              'prepared_manifest_sha256': sha256(HERE / 'manifest.json'), 'work_root': str(work),
              'stages': {stage: {'status': 'BLOCKED', 'reason': 'Not reached'} for stage in STAGES}}
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
        command([root / MANIFEST['fiji']['java_home'] / 'bin/javac', '--release', '11', '-cp', cp,
                 '-d', classes, HERE / 'Fresh_Ganglia_Probe.java', HERE / 'Fresh_Ganglia_Params.java'], 'ganglia-probe-compile.log')
        with zipfile.ZipFile(root / 'plugins' / 'Fresh_Fiji_Probe.jar', 'a') as z:
            for path in classes.glob('*.class'):
                z.write(path, path.name)
    def probe(root, variant, mode, fixture=None):
        name = variant + '_' + mode
        target = args.output / (name + '.json')
        macro = work / (name + '.ijm')
        macro.write_text('run("GAT Fresh Install Probe");\n')
        cmd = launch(root) + ['-Dgat.validation.root=' + str(root), '-Dgat.validation.mode=' + mode,
                             '-Dgat.validation.report=' + str(target),
                             '-Dgat.validation.expectedLabels=' + MANIFEST['expected_neuron_label_sha256']]
        if fixture:
            cmd += ['-Dgat.validation.fixture=' + str(fixture)]
        cmd += ['--run', str(macro)]
        execution = execute(cmd, args.output / (name + '.log'), clean_env(runtime_home(root)), 900 if mode == 'engine_install' else 300, root)
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
        if platform.system() != 'Darwin' or platform.machine() != 'arm64':
            stage(current, 'BLOCKED', reason='This lane requires a native macOS arm64 GUI runner; no emulation or Linux substitution')
            return 3
        if shutil.disk_usage(work).free < 12 * 1024**3:
            raise RuntimeError('Need at least 12 GiB free for one archive and three isolated installations')
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
            raise RuntimeError('Updater reported errors/conflicts; no force or hand-swapping fallback is allowed')
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
        fixture = work / 'public-Hu.tif'
        report['fixture'] = download(MANIFEST['fixture']['url'], fixture, env, args.output / 'fixture-download.log',
                                     expected_sha=MANIFEST['fixture']['sha256'], timeout=120)
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
        # Both source revisions use byte-identical updater output on the same native host.
        current = 'paired_overlays'; overlays = {}
        for variant in ('original','fork'):
            root = work / variant / 'Fiji'
            shutil.copytree(base, root, symlinks=True)
            evidence = args.output / variant; evidence.mkdir()
            overlays[variant] = overlay(root, plugin=args.original_jar.resolve() if variant=='original' else None,
                                      archive=args.fork_archive.resolve() if variant=='fork' else None,
                                      source_commit=args.original_commit if variant=='original' else args.fork_commit,
                                      evidence=evidence)
        stage(current, 'PASS', overlays=overlays)
        for variant in ('original','fork'):
            root = work / variant / 'Fiji'
            current = variant + '_startup'
            if probe(root, variant, 'startup') != 'PASS':
                continue
            current = variant + '_dashboard'
            probe(root, variant, 'dashboard')
            # A blocked dashboard remains blocked; the named API smokes are separate evidence.
            for mode in ('neuron','alignment','ganglia'):
                current = variant + '_' + mode
                if mode=='neuron' and any(p['status']!='MATCH' for p in pins if p['file']=='2D_enteric_neuron_v4_1.zip'):
                    stage(variant+'_neuron','BLOCKED',reason='Updater-installed neuron model differs from pinned reference; no substitution')
                else:
                    probe(root, variant, mode, fixture)
            (args.output / (variant+'-final-inventory.json')).write_text(json.dumps(inventory(root),indent=2)+'\n')
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
    states = [report['stages'][s]['status'] for s in required]
    return 0 if all(s == 'PASS' for s in states) else 2 if 'FAIL' in states else 3


if __name__ == '__main__':
    raise SystemExit(main())
