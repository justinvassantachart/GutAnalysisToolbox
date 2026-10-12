#!/usr/bin/env python3
"""Launch one isolated, already-compiled real Fiji top-menu gate.

Local use must be through the supported GUI Terminal and serialized resource
scheduler. No virtual/guessed display route is created. The production script
is discovered by Fiji and invoked by its actual menu; never rewritten here.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

import prepare_topmenu
from run_inference_probe import validate_classpath, validate_legacy_dependencies

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installation', type=Path, required=True)
    parser.add_argument('--variant', choices=('original', 'native'), required=True)
    args = parser.parse_args()
    root = args.installation.resolve() / args.variant
    fiji = root / 'Fiji'
    config = json.loads((root / 'config.json').read_text())
    if sys.platform != 'darwin' and not os.environ.get('DISPLAY'):
        raise ValueError('Use the supported GUI Terminal with its inherited display')
    if (root / 'launcher.json').exists():
        raise ValueError('Refusing to overwrite an earlier GUI attempt')
    entries = sorted([*fiji.joinpath('jars').rglob('*.jar'), *fiji.joinpath('plugins').rglob('*.jar')])
    validate_classpath(entries, args.variant)
    validate_legacy_dependencies(entries)
    fixture_manifest = json.loads((ROOT / 'native-inference/validation/cross-platform/fixture-manifest.json').read_text())
    for case in fixture_manifest['cases']:
        if prepare_topmenu.sha(fiji / 'models' / case['model']) != case['model_sha256']:
            raise ValueError('Wrong pinned public model: ' + case['model'])
    url_loader = fiji / 'jars/LegacyValidationUrlLoader.jar'
    if not url_loader.is_file():
        raise ValueError('Proven validation-only URL system loader JAR is required for original TF1')
    probe_jar = config.get('probe_jar', 'LegacyMacroTopMenuProbe.jar')
    if probe_jar not in ('LegacyMacroTopMenuProbe.jar', 'LegacyMacroMarkerMenuProbe.jar', 'LegacyMacroBatchMenuProbe.jar'):
        raise ValueError('Unrecognized validation probe')
    plugin = fiji / 'plugins' / probe_jar
    if not plugin.is_file():
        raise ValueError('Compile and install the validation-only probe first')
    if prepare_topmenu.verify(args.installation / 'installation.json'):
        raise ValueError('Runtime/script bytes changed before launch')
    home = root / 'home'
    for folder in ('tmp', 'cache', 'home/.java', 'home/.config', 'home/.local/share'):
        (root / folder).mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, HOME=str(home), XDG_CACHE_HOME=str(root / 'cache'), XDG_CONFIG_HOME=str(home / '.config'),
               XDG_DATA_HOME=str(home / '.local/share'), DJL_CACHE_DIR=str(root / 'cache/djl'),
               POCL_CACHE_DIR=str(root / 'cache/pocl'), OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               TF_NUM_INTRAOP_THREADS='1', TF_NUM_INTEROP_THREADS='1', POCL_MAX_PTHREAD_COUNT='1',
               POCL_CPU_MAX_CU_COUNT='1', CUDA_VISIBLE_DEVICES='-1',
               JAVA_TOOL_OPTIONS='-Xmx768m -XX:ActiveProcessorCount=1')
    command = [str(fiji / 'fiji'), '--heap=768m', '-XX:ActiveProcessorCount=1',
               '-Duser.home=' + str(home), '-Djava.util.prefs.userRoot=' + str(home / '.java'),
               '-Djava.io.tmpdir=' + str(root / 'tmp'), '-Dimagej.updater.disableAutocheck=true',
               '-Djava.system.class.loader=BaselineUrlClassLoader', '--add-opens=java.base/java.lang=ALL-UNNAMED']
    if args.variant == 'native':
        command += ['-Dgat.stardist.backend=native', '-Dgat.inference.directory=' + config['native_worker']]
    command += ['--run', str(root / 'driver.ijm')]
    launcher = {'schema_version': 1, 'status': 'RUNNING', 'scope': 'real-top-menu-whole-workflow',
                'variant': args.variant, 'command': command, 'source_sha256': prepare_topmenu.sha(Path(config['source_script'])),
                'harness_sha256': prepare_topmenu.sha(plugin), 'url_loader_sha256': prepare_topmenu.sha(url_loader),
                'models': {}, 'candidate_sha256': None}
    for name in ('2D_enteric_neuron_v4_1.zip', '2D_enteric_neuron_subtype_v4.zip'):
        launcher['models'][name] = prepare_topmenu.sha(fiji / 'models' / name)
    if args.variant == 'native':
        launcher['candidate_sha256'] = prepare_topmenu.sha(fiji / 'plugins/GAT_MacroFork.jar')
    (root / 'launcher.json').write_text(json.dumps(launcher, indent=2) + '\n')
    spec = importlib.util.spec_from_file_location('bounded_topmenu_execution', ROOT / 'native-inference/validation/workflows/run_workflows.py')
    runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
    execution = runner.execute(command, root / 'runtime.log', 600, env, cwd=str(fiji))
    launcher['execution'] = execution
    immutable = prepare_topmenu.verify(args.installation / 'installation.json') == 0
    report_path = root / 'evidence/report.json'
    report = json.loads(report_path.read_text()) if report_path.is_file() else {}
    passed = execution.get('exit_code') == 0 and immutable and report.get('status') == 'PASS_TOP_MENU_WORKFLOW_SCOPE'
    launcher['status'] = 'PASS_TOP_MENU_WORKFLOW_SCOPE' if passed else 'FAIL_OR_INCOMPLETE'
    (root / 'launcher.json').write_text(json.dumps(launcher, indent=2) + '\n')
    print(json.dumps({'status': launcher['status'], 'report': str(report_path)}))
    return 0 if passed else 2

if __name__ == '__main__':
    raise SystemExit(main())
