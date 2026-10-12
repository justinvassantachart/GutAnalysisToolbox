#!/usr/bin/env python3
"""Run public actual-macro command cases in isolated original/native AWT JVMs.

No dependency downloads, installation changes, private image inputs or GUI stubs.
Supply the pinned original ImageJ/StarDist runtime classpath. Run via Xvfb on
hosted Linux or a supported native Mac/cloud desktop. Models execute here.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SMOKE = ('neuron-01', 'neuron-07', 'neuron-13', 'subtype-04', 'subtype-05', 'subtype-08', 'subtype-12')
PROTOBUF_3_11_4_SHA256 = '42e98f58f53d1a49fd734c2dd193880f2dfec3436a2993a00d06b8800a22a3f2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_classpath(entries, variant):
    forbidden = ('org/tensorflow/types/TFloat32.class', 'org/gatanalysis/inference/NativeInferenceMain.class')
    if variant == 'original':
        forbidden += ('Features/Inference/NativeStarDist.class', 'Features/Macros/LegacyMacroStarDist.class')
    for path in entries:
        if not path.exists():
            raise ValueError('Missing explicit classpath entry: ' + str(path))
        if path.is_dir():
            present = [name for name in forbidden if (path / name).exists()]
        elif zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as jar:
                names = set(jar.namelist())
                present = [name for name in forbidden if name in names]
        else:
            raise ValueError('Classpath must contain explicit JARs/directories, no wildcards: ' + str(path))
        if present:
            raise ValueError('Contaminated %s runtime: %s in %s' % (variant, present, path.name))


def pinned_macro_line(variant):
    manifest = json.loads((HERE / 'source-manifest.json').read_text())
    row = next(f for f in manifest['files'] if f['path'] == '_Analyse Neurons.ijm')
    path = ROOT / row['path']
    if sha(path) != row['sha256']:
        raise ValueError('Original macro source is not the pinned pre-deletion blob')
    lines = [line for line in path.read_text().splitlines()
             if line.lstrip().startswith('run("Command From Macro",') and 'de.csbdresden.stardist.StarDist2D]' in line]
    if len(lines) != 1:
        raise ValueError('Expected one exact original macro call line')
    line = lines[0]
    if variant == 'native':
        line = line.replace('de.csbdresden.stardist.StarDist2D]', 'Features.Macros.LegacyMacroStarDist]')
    return line, row


def validate_legacy_dependencies(entries):
    """TF1 generated descriptors fail against protobuf4 despite a loaded JNI."""
    protobuf = [p for p in entries if p.name.startswith('protobuf-java-') and not p.name.startswith('protobuf-java-util-')]
    if len(protobuf) != 1 or protobuf[0].name != 'protobuf-java-3.11.4.jar' or sha(protobuf[0]) != PROTOBUF_3_11_4_SHA256:
        raise ValueError('Use the pinned protobuf-java3.11.4 runtime; newer protobuf4 cannot run original TF1 descriptors')
    required = {'StarDist_-0.3.0.jar', 'csbdeep-0.6.0.jar', 'imagej-tensorflow-1.1.6.jar', 'Clipper-6.4.2.jar'}
    artifacts = json.loads((ROOT / 'native-inference/validation/baseline/plugin-artifacts.json').read_text())
    for artifact in artifacts:
        if artifact['file'] in required:
            matches = [p for p in entries if p.name == artifact['file']]
            if len(matches) != 1 or sha(matches[0]) != artifact['sha256']:
                raise ValueError('Missing/duplicate/changed pinned legacy plugin: ' + artifact['file'])


def selected_cases(preset, selected=None):
    cases = json.loads((HERE / 'coverage-matrix.json').read_text())['layers']['inference']['cases']
    allowed = {c['id'] for c in cases}
    ids = set(selected or (SMOKE if preset == 'smoke' else allowed))
    if not ids or not ids <= allowed:
        raise ValueError('Unknown or empty case selection: ' + str(sorted(ids - allowed)))
    return [{k: v for k, v in c.items() if k != 'status'} for c in cases if c['id'] in ids]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-classpath', type=Path, required=True)
    parser.add_argument('--fiji-directory', type=Path, help='Existing runtime root for full Fiji distributions; command plugins still come only from explicit classpath')
    parser.add_argument('--production-classes', type=Path, help='Native variant only; must contain actual compiled adapter/plugin index')
    parser.add_argument('--variant', choices=('original', 'native'), required=True)
    parser.add_argument('--native-worker', type=Path)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--model-directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--java', default='java')
    parser.add_argument('--javac', default='javac')
    parser.add_argument('--preset', choices=('smoke', 'matrix'), default='smoke')
    parser.add_argument('--cases', nargs='+')
    parser.add_argument('--timeout', type=int, default=600)
    parser.add_argument('--compile-only', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.timeout <= 1800:
        parser.error('Use a bounded 1–1800 second per-case deadline')
    native = args.variant == 'native'
    if native != bool(args.production_classes) or native != bool(args.native_worker):
        parser.error('Native needs production classes and worker; original forbids both')
    entries = [Path(p).resolve() for p in args.runtime_classpath.read_text().strip().split(os.pathsep)]
    if native:
        entries.insert(0, args.production_classes.resolve())
        index = args.production_classes / 'META-INF/json/org.scijava.plugin.Plugin'
        if not index.is_file() or 'Features.Macros.LegacyMacroStarDist' not in index.read_text():
            raise ValueError('Actual annotation-generated adapter plugin index is missing')
    validate_classpath(entries, args.variant)
    validate_legacy_dependencies(entries)
    fixtures = json.loads((ROOT / 'native-inference/validation/cross-platform/fixture-manifest.json').read_text())
    if sha(args.fixture) != fixtures['source']['sha256']:
        raise ValueError('Only the pinned public Hu fixture is accepted; never upload private inputs')
    models = {'neuron': fixtures['cases'][0], 'subtype': fixtures['cases'][1]}
    cases = selected_cases(args.preset, args.cases)
    for model in {c['model'] for c in cases}:
        item = models[model]
        if sha(args.model_directory / item['model']) != item['model_sha256']:
            raise ValueError('Pinned model hash mismatch: ' + model)
    line, source = pinned_macro_line(args.variant)
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    classes = out / 'classes'; classes.mkdir()
    spec = importlib.util.spec_from_file_location('bounded_macro_execution', ROOT / 'native-inference/validation/workflows/run_workflows.py')
    runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
    env = dict(os.environ, OMP_NUM_THREADS='1', TF_NUM_INTRAOP_THREADS='1', TF_NUM_INTEROP_THREADS='1',
               OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', CUDA_VISIBLE_DEVICES='-1')
    # Applies to the real child worker too, without changing its production code.
    env['JAVA_TOOL_OPTIONS'] = '-XX:ActiveProcessorCount=1 -Xmx768m'
    cp = os.pathsep.join(map(str, dict.fromkeys(entries)))
    sources = [HERE / 'LegacyMacroInferenceProbe.java', ROOT / 'native-inference/validation/baseline/BaselineBootstrap.java',
               ROOT / 'native-inference/validation/baseline/BaselineUrlClassLoader.java']
    argfile = out / 'javac.args'
    argfile.write_text('\n'.join('"' + str(p).replace('\\', '\\\\').replace('"', '\\"') + '"'
                                for p in ['-encoding', 'UTF-8', '-cp', cp, '-d', classes, *sources]) + '\n')
    summary = {'schema_version': 1, 'scope': 'registered-legacy-macro-inference-boundary',
               'whole_analysis_macro_executed': False, 'variant': args.variant, 'selected_cases': [c['id'] for c in cases],
               'macro_source': source, 'public_fixture_sha256': sha(args.fixture),
               'harness_sha256': {p.name: sha(p) for p in sources},
               'runtime_artifacts': [{'name': p.name, 'sha256': sha(p)} for p in entries if p.is_file()],
               'cases': [], 'status': 'COMPILING'}
    summary_path = out / 'summary.json'
    def save():
        summary_path.write_text(json.dumps(summary, indent=2) + '\n')
    save()
    compile_env = dict(env, JAVA_TOOL_OPTIONS='-XX:ActiveProcessorCount=1 -Xmx256m')
    result = runner.execute([args.javac, '@' + str(argfile)], out / 'compile.log', 180, compile_env)
    summary['compilation'] = result
    if result['exit_code'] or result['resource_stop_reason']:
        summary['status'] = 'BLOCKED_COMPILE'; save(); return 2
    if args.compile_only:
        summary['status'] = 'COMPILED_NOT_RUN'; save(); return 0
    if native:
        worker_files = sorted(p for p in args.native_worker.rglob('*') if p.is_file())
        if not (args.native_worker / 'gat-native-inference.jar').is_file():
            raise ValueError('Missing actual native worker JAR')
        summary['native_worker_artifacts'] = [{'name': str(p.relative_to(args.native_worker)), 'sha256': sha(p)} for p in worker_files]
    try:
        for case in cases:
            directory = out / case['id']; directory.mkdir()
            config = {'variant': args.variant, 'case': case, 'fixture': str(args.fixture.resolve()),
                      'model': str((args.model_directory / models[case['model']]['model']).resolve()),
                      'macro_line': line, 'output': str(directory / 'evidence')}
            config_path = directory / 'config.json'; config_path.write_text(json.dumps(config, indent=2) + '\n')
            home = directory / 'imagej-home'; home.mkdir()
            empty_plugins = directory / 'explicit-classpath-only-plugins'; empty_plugins.mkdir()
            user_home = directory / 'user-home'; user_home.mkdir()
            fiji_home = args.fiji_directory.resolve() if args.fiji_directory else home
            command = [args.java, '--add-opens=java.base/java.lang=ALL-UNNAMED', '-Xmx768m', '-XX:ActiveProcessorCount=1',
                       '-Djava.awt.headless=false', '-Djava.system.class.loader=BaselineUrlClassLoader',
                       '-Dimagej.updater.disableAutocheck=true',
                       '-Dimagej.dir=' + str(fiji_home), '-Dfiji.dir=' + str(fiji_home),
                       '-Dplugins.dir=' + str(empty_plugins), '-Duser.home=' + str(user_home),
                       '-Djava.util.prefs.userRoot=' + str(directory / 'prefs')]
            if native:
                command += ['-Dgat.stardist.backend=native', '-Dgat.inference.directory=' + str(args.native_worker.resolve()),
                            '-Dgat.inference.timeoutSeconds=' + str(max(1, args.timeout - 30))]
            command += ['-cp', str(classes) + os.pathsep + cp, 'BaselineBootstrap', 'LegacyMacroInferenceProbe', str(config_path)]
            execution = runner.execute(command, directory / 'runtime.log', args.timeout, env)
            evidence = directory / 'evidence/report.json'
            observation = json.loads(evidence.read_text()) if evidence.exists() else {'status': 'NO_REPORT'}
            status = observation['status']
            if execution['exit_code'] != 0 or execution['resource_stop_reason']:
                status = 'INCOMPLETE_OR_FAILED'
            summary['cases'].append({'id': case['id'], 'status': status, 'execution': execution,
                                     'report': str(evidence.relative_to(out))})
            summary['status'] = 'RUNNING'; save()
        summary['status'] = 'PASS_SELECTED_CASES' if all(c['status'] == 'PASS_MACRO_INFERENCE_CASE' for c in summary['cases']) else 'FAIL_OR_INCOMPLETE'
    finally:
        save()
    print(summary['status'], len(summary['cases']), 'actual macro inference cases')
    return 0 if summary['status'] == 'PASS_SELECTED_CASES' else 1


if __name__ == '__main__':
    sys.exit(main())
