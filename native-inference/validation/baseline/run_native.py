#!/usr/bin/env python3
"""Observe actual old/fork public API behavior; never assert that old GAT must fail."""
import argparse
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

from run_workflows import validate_baseline

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(url, path, expected):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        partial = path.with_suffix(path.suffix + '.download')
        subprocess.run(['curl', '--fail', '--location', '--silent', '--show-error', '--proto', '=https',
                        '--retry', '3', '--max-time', '240', url, '-o', str(partial)], check=True)
        if sha(partial) != expected:
            raise ValueError('Downloaded checksum mismatch: ' + path.name)
        partial.replace(path)
    if sha(path) != expected:
        raise ValueError('Cached checksum mismatch: ' + path.name)


def run(args, log, timeout):
    spec = importlib.util.spec_from_file_location('gat_bounded_workflow_execution', HERE.parent / 'workflows/run_workflows.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    result = runner.execute(list(map(str, args)), log, timeout, os.environ.copy())
    result['timed_out'] = result.get('resource_stop_reason') == 'process deadline exceeded'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, required=True)
    parser.add_argument('--root-classpath', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache', type=Path, help='Shared pinned downloads, outside uploaded diagnostic directories')
    parser.add_argument('--allow-fork', action='store_true')
    parser.add_argument('--inference-directory', type=Path)
    parser.add_argument('--alignment-directory', type=Path)
    parser.add_argument('--maven', default='mvn')
    parser.add_argument('--java', default='java')
    parser.add_argument('--javac', default='javac')
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--bootstrap', choices=['app', 'url-system'], default='app', help='Additional URL-system-loader control; app reproduces the first-run launch')
    parser.add_argument('--full-legacy-context', action='store_true', help='Initialize actual ImageJ2 legacy context for alignment too')
    parser.add_argument('--component-probes', action='store_true', help='Also collect separate original TF1/OpenCV JNI and direct-plugin component evidence')
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error('--timeout must be a positive number of seconds')
    if not args.allow_fork and (args.inference_directory or args.alignment_directory):
        raise ValueError('Worker directories are allowed only with --allow-fork')
    project = args.project_root.resolve()
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Refusing to overwrite a nonempty --output directory')
    out.mkdir(parents=True, exist_ok=True)
    provenance = ({'mode': 'fork', 'revision': subprocess.check_output(['git', '-C', str(project), 'rev-parse', 'HEAD'], text=True).strip()}
                  if args.allow_fork else validate_baseline(project, args.root_classpath))
    cache = args.cache.resolve() if args.cache else out.parent / 'native-probe-cache'
    cache.mkdir(parents=True, exist_ok=True)
    plugins = cache / 'plugins'; plugins.mkdir(exist_ok=True)
    manifest = json.loads((HERE / 'plugin-artifacts.json').read_text())
    for item in manifest:
        fetch(item['url'], plugins / item['file'], item['sha256'])
    fixture_manifest = json.loads((HERE.parent / 'cross-platform/fixture-manifest.json').read_text())
    source = fixture_manifest['source']
    input_file = cache / 'fixtures' / 'public-Hu.tif'
    fetch(source['url'], input_file, source['sha256'])
    model_spec = fixture_manifest['cases'][0]
    model = cache / 'fixtures' / model_spec['model']
    fetch(fixture_manifest['model_source_base'] + model_spec['model'], model, model_spec['model_sha256'])
    old_platform = 'macosx-x86_64' if platform.system() == 'Darwin' else 'linux-x86_64'
    dependency_cp = cache / ('native-dependencies-' + old_platform + '-classpath.txt')
    maven = run([args.maven, '-B', '-ntp', '-f', HERE / 'dependencies-pom.xml',
                 'dependency:build-classpath', '-Dmdep.outputFile=' + str(dependency_cp),
                 '-Dbaseline.opencv.platform=' + old_platform], out / 'dependencies.log', 900)
    if maven['exit_code'] != 0 or not dependency_cp.exists():
        raise RuntimeError('Cannot prepare actual original dependencies; see dependencies.log')
    # Pin old backend/JavaCV entries before the original GAT UI/CLIJ classpath.
    entries = [str(project / 'target/classes')]
    entries += sorted(str(p) for p in plugins.glob('*.jar'))
    entries += dependency_cp.read_text().strip().split(os.pathsep)
    entries += args.root_classpath.read_text().strip().split(os.pathsep)
    entries = list(dict.fromkeys(entries))
    forbidden = [p for p in entries if 'tensorflow-core' in Path(p).name or 'tensorflow-ndarray' in Path(p).name or 'gat-native-' in Path(p).name]
    if forbidden:
        raise ValueError('Forbidden modern TensorFlow/native worker classpath entries: ' + ', '.join(forbidden))
    cp = os.pathsep.join(entries)
    classes = out / 'probe-classes'; classes.mkdir(exist_ok=True)
    sources = ['BaselineNativeProbe.java', 'BaselineUrlClassLoader.java', 'BaselineBootstrap.java', 'LegacyJniProbe.java', 'LegacyPluginProbe.java']
    compilation = run([args.javac, '-encoding', 'UTF-8', '-cp', cp, '-d', classes]
                      + [HERE / name for name in sources], out / 'compile.log', 180)
    if compilation['exit_code'] != 0:
        raise RuntimeError('Actual native probe compilation failed; see compile.log')
    patchers = [p for p in entries if Path(p).name == 'ij1-patcher-2.0.0.jar']
    if len(patchers) != 1:
        raise ValueError('Expected exactly one pinned ImageJ legacy patcher')
    prefix = [args.java, '--add-opens=java.base/java.lang=ALL-UNNAMED', '-Xmx3g', '-Djava.awt.headless=' + ('true' if platform.system() == 'Linux' and not os.environ.get('DISPLAY') else 'false'),
              '-Dimagej.dir=' + str(out / 'imagej-home')]
    (out / 'imagej-home').mkdir(exist_ok=True)
    if args.allow_fork:
        prefix += ['-Dgat.probe.allowFork=true']
        if args.inference_directory:
            prefix += ['-Dgat.stardist.backend=native', '-Dgat.inference.directory=' + str(args.inference_directory.resolve())]
        if args.alignment_directory:
            prefix += ['-Dgat.alignment.backend=native', '-Dgat.alignment.directory=' + str(args.alignment_directory.resolve())]
    if args.full_legacy_context:
        prefix += ['-Dgat.probe.fullLegacyContext=true']
    if args.component_probes:
        prefix += ['-Dgat.probe.debug=true']
    if args.bootstrap == 'url-system':
        prefix += ['-Djava.system.class.loader=BaselineUrlClassLoader']
    prefix += ['-cp', str(classes) + os.pathsep + cp]
    def launch(main, parameters, imagej=False):
        command = list(prefix)
        if args.bootstrap == 'url-system':
            command += ['BaselineBootstrap', main]
        else:
            # Only actual ImageJ API probes need the original app-loader agent.
            if imagej:
                command.insert(1, '-javaagent:' + patchers[0] + '=init')
            command += [main]
        return command + parameters
    observations = []
    component_observations = []
    probes = [('stardist', 'BaselineNativeProbe', ['stardist', input_file, model], True),
              ('alignment', 'BaselineNativeProbe', ['alignment'], True)]
    if args.component_probes:
        probes += [('tensorflow-jni', 'LegacyJniProbe', ['tensorflow'], False),
                   ('opencv-jni', 'LegacyJniProbe', ['opencv'], False),
                   ('template-plugin-direct', 'LegacyPluginProbe', [], False)]
    for name, main_class, parameters, actual_api in probes:
        report = out / (name + '.json')
        execution = run(launch(main_class, parameters + [report], actual_api or main_class == 'LegacyPluginProbe'), out / (name + '.log'), args.timeout)
        if report.exists():
            observation = json.loads(report.read_text())
        else:
            observation = {'probe': name, 'status': 'process_timeout' if execution['timed_out'] else 'process_failure_without_probe_report',
                           'actual_gat_method_invoked': None}
        if execution['timed_out'] or execution.get('resource_stop_reason'):
            observation['last_probe_status'] = observation.get('status')
            observation['status'] = 'process_timeout' if execution['timed_out'] else 'process_resource_stop'
        elif observation.get('status') == 'running':
            observation['status'] = 'process_failure_before_completion'
        observation['execution'] = execution
        (observations if actual_api else component_observations).append(observation)
    if not args.allow_fork:
        provenance['after_run'] = validate_baseline(project, args.root_classpath)
    evidence_complete = all(x.get('actual_gat_method_invoked') is True and x['status'] in ('success', 'workflow_failure') for x in observations)
    component_evidence_complete = all(x['status'] in ('success', 'native_component_failure', 'plugin_component_failure') for x in component_observations)
    summary = {'evidence_complete': evidence_complete, 'component_evidence_complete': component_evidence_complete,
               'bootstrap': args.bootstrap, 'full_legacy_context': args.full_legacy_context, 'provenance': provenance, 'platform': platform.platform(), 'old_opencv_native_classifier': old_platform,
               'input_sha256': sha(input_file), 'model_sha256': sha(model),
               'plugin_artifacts': manifest,
               'dependency_artifacts': [{'filename': Path(p).name, 'sha256': sha(Path(p))} for p in entries if Path(p).is_file()],
               'observations': observations, 'component_observations': component_observations,
               'interpretation': 'Observed API outcomes only. Setup failures/unavailable GUI are not native incompatibility; baseline success remains success. No fork classes or modern TensorFlow enter the original JVM.'}
    (out / 'native-summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'evidence_complete': evidence_complete, 'observations': [{'probe': x['probe'], 'status': x['status'], 'execution': x['execution']} for x in observations]}, indent=2))
    # Preserve negative and positive observed outcomes. Setup/build/isolation errors
    # still raise; plugin failures are evidence rather than an expected-failure test.
    return int(not evidence_complete or not component_evidence_complete or (args.allow_fork and any(x['status'] != 'success' for x in observations)))


if __name__ == '__main__':
    sys.exit(main())
