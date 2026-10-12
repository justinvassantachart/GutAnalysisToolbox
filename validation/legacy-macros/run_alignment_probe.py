#!/usr/bin/env python3
"""Execute the registered legacy alignment macro boundary in disposable AWT.

Prepare a pinned parent classpath with alignment_runtime.py first. Six supported
8/16-bit cases and one actual unsupported 32-bit control run serially. This does
not test the surrounding calcium GUI workflow. Use a supported desktop/Xvfb;
this launcher never starts a display or installs anything into Fiji.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys

from alignment_runtime import sha, validate

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCOPE = 'registered-legacy-macro-alignment-boundary'


def macro_source(variant):
    row = next(x for x in json.loads((HERE / 'source-manifest.json').read_text())['files']
               if x['path'] == 'Calcium imaging/_Align_stack.ijm')
    source = ROOT / row['path']
    if sha(source) != row['sha256']:
        raise ValueError('Original calcium macro source differs from pinned legacy blob')
    lines = [line.strip() for line in source.read_text().splitlines()
             if line.strip().startswith('run("Align slices in stack...",')]
    if len(lines) != 2 or len(set(lines)) != 1 or lines[0].count('ref.slice=3') != 1:
        raise ValueError('Expected the two identical original macro alignment sites')
    line = lines[0]
    if variant != 'original':
        line = line.replace('run("Align slices in stack...",', 'gat_alignment_status=call("Features.Macros.LegacyTemplateMatching.run",')
        line += ' if(gat_alignment_status!="GAT_ALIGNMENT_OK") exit("MacroFork alignment failed: "+gat_alignment_status);'
    return line, row


def production_hashes(directory):
    required = ('Features/Macros/LegacyTemplateMatching.class', 'Features/Inference/NativeAlignmentClient.class',
                'Features/Inference/NativeInferenceClient.class', 'Features/Inference/InferenceBackend.class')
    if not directory.is_dir() or any(not (directory / name).is_file() for name in required):
        raise ValueError('Actual compiled production adapter and clients required')
    if (directory / 'TemplateMatching/NativeAlignmentMain.class').exists():
        raise ValueError('Worker must remain outside parent production classes')
    return {name: sha(directory / name) for name in required}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime-classpath', type=Path, required=True)
    p.add_argument('--variant', choices=('original', 'native', 'legacy-delegate'), required=True)
    p.add_argument('--production-classes', type=Path)
    p.add_argument('--native-worker', type=Path)
    p.add_argument('--fiji-directory', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--java', default='java'); p.add_argument('--javac', default='javac')
    p.add_argument('--compile-only', action='store_true')
    args = p.parse_args()
    native = args.variant == 'native'
    adapter = args.variant != 'original'
    if adapter != bool(args.production_classes) or native != bool(args.native_worker):
        p.error('Native requires classes/worker; legacy-delegate requires classes only; original forbids both')
    if not native and not args.compile_only and (platform.system(), platform.machine()) != ('Linux', 'x86_64'):
        p.error('Pinned original JNI reference requires Linux x86_64; native worker can run on its built platform')
    raw = args.runtime_classpath.read_text().strip().split(os.pathsep)
    if not raw or not all(raw):
        raise ValueError('Empty parent runtime classpath')
    entries = [Path(s).resolve() for s in raw]; validate(entries)
    parent_entries = list(entries)
    line, macro = macro_source(args.variant)
    hashes = {}
    if adapter:
        hashes = production_hashes(args.production_classes)
        entries.insert(0, args.production_classes.resolve())
    if native:
        if not (args.native_worker / 'gat-native-alignment.jar').is_file() or not (args.native_worker / 'lib').is_dir():
            raise ValueError('Separate native alignment worker is absent')
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    classes = out / 'classes'; classes.mkdir()
    baseline = ROOT / 'native-inference/validation/baseline'
    sources = [HERE / 'LegacyMacroAlignmentProbe.java', HERE / 'LegacyMacroModalState.java', baseline / 'BaselineUrlClassLoader.java', baseline / 'BaselineBootstrap.java']
    cp = os.pathsep.join(map(str, entries))
    argfile = out / 'javac.args'
    argfile.write_text('\n'.join('"' + str(x).replace('\\', '\\\\').replace('"', '\\"') + '"'
                                for x in ['-proc:none', '-encoding', 'UTF-8', '-cp', cp, '-d', classes, *sources]) + '\n')
    spec = importlib.util.spec_from_file_location('bounded_alignment_execution', ROOT / 'native-inference/validation/workflows/run_workflows.py')
    runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               JAVA_TOOL_OPTIONS='-XX:ActiveProcessorCount=1')
    schedule = json.loads((HERE / 'alignment-cases.json').read_text())
    report = {'schema_version': 1, 'scope': SCOPE, 'whole_calcium_macro_executed': False,
              'variant': args.variant, 'schedule': schedule, 'macro_source': macro,
              'sources': {str(s.relative_to(ROOT)): sha(s) for s in sources},
              'runtime_artifacts': [{'name': e.name, 'sha256': sha(e)} for e in parent_entries],
              'production_classes': hashes, 'status': 'COMPILING'}
    if native:
        report['worker_files'] = {str(f.relative_to(args.native_worker)): sha(f) for f in sorted(args.native_worker.rglob('*')) if f.is_file()}
    config = {'variant': args.variant, 'macro_line': line, 'macro_source': macro,
              'schedule': schedule, 'output': str(out / 'result')}
    config_path = out / 'run-config.json'; config_path.write_text(json.dumps(config, indent=2) + '\n')
    def save():
        (out / 'launcher.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    report['compilation'] = runner.execute([args.javac, '-J-Xmx256m', '-J-XX:ActiveProcessorCount=1', '@' + str(argfile)],
                                         out / 'compile.log', 180, env, rss_limit_kib=1048576)
    if report['compilation']['exit_code'] or report['compilation']['resource_stop_reason']:
        report['status'] = 'BLOCKED_COMPILE'; save(); return 2
    if args.compile_only:
        report['status'] = 'COMPILED_NOT_RUN'; save(); return 0
    home = out / 'imagej-home'; home.mkdir()
    empty_plugins = out / 'explicit-classpath-only-plugins'; empty_plugins.mkdir()
    runtime_home = args.fiji_directory.resolve() if args.fiji_directory else home
    command = [args.java, '--add-opens=java.base/java.lang=ALL-UNNAMED', '-Xmx256m', '-XX:ActiveProcessorCount=1',
               '-Djava.awt.headless=false', '-Djava.system.class.loader=BaselineUrlClassLoader',
               '-Dimagej.updater.disableAutocheck=true', '-Dimagej.dir=' + str(runtime_home), '-Dfiji.dir=' + str(runtime_home),
               '-Dplugins.dir=' + str(empty_plugins), '-Duser.home=' + str(home), '-Djava.util.prefs.userRoot=' + str(out / 'prefs')]
    if args.variant == 'legacy-delegate':
        command += ['-Dgat.alignment.backend=legacy']
    if native:
        command += ['-Dgat.alignment.backend=native', '-Dgat.alignment.directory=' + str(args.native_worker.resolve()),
                    '-Dgat.alignment.timeoutSeconds=60']
    command += ['-cp', str(classes) + os.pathsep + cp, 'BaselineBootstrap', 'LegacyMacroAlignmentProbe', str(config_path)]
    report['execution'] = runner.execute(command, out / 'runtime.log', 180, env, rss_limit_kib=1048576)
    evidence = out / 'result/report.json'
    actual = json.loads(evidence.read_text()) if evidence.exists() else {}
    report['status'] = actual.get('status', 'NO_REPORT')
    if report['execution']['exit_code'] or report['execution']['resource_stop_reason']:
        report['status'] = 'INCOMPLETE_OR_FAILED'
    save(); print(report['status'])
    return 0 if report['status'] == 'PASS_ALIGNMENT_BOUNDARY' else 1


if __name__ == '__main__':
    sys.exit(main())
