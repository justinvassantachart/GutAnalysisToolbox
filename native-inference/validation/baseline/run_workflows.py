#!/usr/bin/env python3
"""Run the same read-only workflow probes against a verified unchanged GAT checkout."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BASELINE_COMMIT = '1870d9e16e16fd6daeac0bd05122e851029ddedc'
FORK = HERE.parents[2]


def command(*args):
    return subprocess.check_output(list(map(str, args)), text=True).strip()


def validate_baseline(root, classpath):
    root = root.resolve()
    revision = command('git', '-C', root, 'rev-parse', 'HEAD')
    if revision != BASELINE_COMMIT:
        raise ValueError('Wrong baseline revision: ' + revision)
    dirty = command('git', '-C', root, 'status', '--porcelain', '--untracked-files=no')
    if dirty:
        raise ValueError('Baseline tracked sources are modified: ' + dirty)
    if root == FORK or FORK in root.parents:
        raise ValueError('Use a separate original checkout outside the fork checkout')
    if (root / 'target/classes/Features/Inference').exists():
        raise ValueError('Fork inference classes are present in baseline target/classes; clean build required')
    import os
    entries = [Path(p).resolve() for p in classpath.read_text().strip().split(os.pathsep)]
    for entry in entries:
        if entry == FORK or FORK in entry.parents:
            raise ValueError('Fork classpath contamination: ' + str(entry))
        if 'tensorflow-core' in entry.name or 'gat-native-' in entry.name:
            raise ValueError('Modern native-worker dependency on original baseline classpath: ' + entry.name)
    return {'revision': revision, 'tracked_source_changes': False,
            'fork_inference_classes_present': False,
            'fixture_and_probe_source': 'Current validation harness only; production classes from unchanged baseline'}


def main():
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument('--project-root', type=Path, required=True)
    parser.add_argument('--root-classpath', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args, remaining = parser.parse_known_args()
    provenance = validate_baseline(args.project_root, args.root_classpath)
    spec = importlib.util.spec_from_file_location('gat_workflow_comparator', HERE.parent / 'workflows/run_workflows.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    # Reuse the exact fork probes and pinned dependencies, replacing only the
    # production root/classes. No baseline source or shared runner is edited.
    runner.ROOT = args.project_root.resolve()
    sys.argv = [str(HERE.parent / 'workflows/run_workflows.py'),
                '--root-classpath', str(args.root_classpath.resolve()),
                '--output', str(args.output.resolve())] + remaining
    result = runner.main()
    provenance['after_run'] = validate_baseline(args.project_root, args.root_classpath)
    provenance['workflow_comparator_exit_code'] = result
    provenance['interpretation'] = ('Actual observed checks, not expected-failure assertions. A baseline PASS remains PASS; '
        'FAIL, BLOCKED, NOT_RUN and process resource limits remain distinct. A successful evidence job does not imply old GAT passed.')
    (args.output / 'baseline-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    # Old workflow failures are evidence, not a reason to erase other suite logs.
    # Missing reports or source contamination still fail the evidence job.
    summary = json.loads((args.output / 'run-summary.json').read_text())
    if not summary.get('suites'):
        raise RuntimeError('No baseline workflow observations were recorded')
    observed = all('execution' in suite for suite in summary['suites'])
    print(json.dumps({'baseline_revision': BASELINE_COMMIT, 'observed_status': summary['status'],
                      'evidence_complete': observed, 'comparator_exit_code': result}, indent=2))
    if not observed:
        raise RuntimeError('One or more baseline suites did not execute; inspect setup/compilation diagnostics')


if __name__ == '__main__':
    main()
