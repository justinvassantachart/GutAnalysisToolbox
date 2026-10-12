import importlib.util
import json
import ast
import inspect
from pathlib import Path
import tempfile
import unittest
import zipfile

SPEC = importlib.util.spec_from_file_location('installation_gate', Path(__file__).with_name('run_fresh_fiji.py'))
fresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fresh)


class InstallationGateTests(unittest.TestCase):
    def test_installation_scope_is_initialized_only_in_main(self):
        helper = inspect.getsource(fresh.apply_historical_runtime)
        self.assertNotIn('args.installation_only', helper)
        main = inspect.getsource(fresh.main)
        self.assertIn("report['required_stages'] = list(INSTALLATION_REQUIRED)", main)
        ast.parse(main)

    def test_missing_and_failed_stages_cannot_pass(self):
        required = fresh.INSTALLATION_REQUIRED
        report = {'stages': {k: {'status': 'PASS'} for k in required}}
        self.assertEqual(0, fresh.stage_exit_code(report, required))
        for state, code in [('FAIL', 2), ('BLOCKED', 3), ('NOT_IN_SCOPE', 3), ('NOT_RUN', 3)]:
            report['stages']['fork_registration']['status'] = state
            self.assertEqual(code, fresh.stage_exit_code(report, required))
        del report['stages']['fork_registration']
        self.assertEqual(3, fresh.stage_exit_code(report, required))

    def test_installation_mode_is_explicit_and_does_not_require_original(self):
        parsed = fresh.build_parser().parse_args(['--output', '/tmp/evidence', '--fork-archive', '/tmp/package.zip',
                                                 '--fork-commit', 'a' * 40, '--installation-only'])
        self.assertTrue(parsed.installation_only)
        self.assertIsNone(parsed.original_jar)

    def test_actual_registration_requires_all_commands_and_packaged_class_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'test.zip'
            names = ['scripts/GAT MacroFork/Case %d [MacroFork].ijm' % i for i in range(47)]
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('MACROFORK_BUILD_INFO.json', json.dumps({'source_commit': 'a' * 40}))
                z.writestr('plugins/GutAnalysisToolbox_test.jar', b'test-only')
                for name in names:
                    z.writestr(name, b'test-only')
            commands = {'GATV2': 'registered'}
            commands.update({'Case %d [MacroFork]' % i: 'script:' + n[len('scripts/'):] for i, n in enumerate(names)})
            classes = ('UI.GatPluginUI', 'Features.Macros.LegacyMacroStarDist',
                       'Features.Macros.LegacyTemplateMatching', 'Features.Inference.NativeAlignmentClient')
            startup = {'status': 'PASS', 'mode': 'startup', 'errors': [], 'imagej_root': '/fresh/Fiji',
                       'os.arch': 'aarch64', 'os.name': 'Mac OS X', 'registered_commands': commands,
                       'class_sources': {c: {'source': 'file:/fresh/Fiji/plugins/GutAnalysisToolbox_test.jar'} for c in classes}}
            self.assertEqual(47, fresh.verify_installed_registration(startup, path)['macro_count'])
            startup['status'] = 'RUNNING'
            with self.assertRaises(ValueError): fresh.verify_installed_registration(startup, path)
            startup['status'] = 'PASS'
            saved = commands.pop('Case 1 [MacroFork]')
            with self.assertRaises(ValueError): fresh.verify_installed_registration(startup, path)
            commands['Case 1 [MacroFork]'] = saved
            commands['Duplicate [MacroFork]'] = saved
            with self.assertRaises(ValueError): fresh.verify_installed_registration(startup, path)
            del commands['Duplicate [MacroFork]']
            startup['class_sources'][classes[0]]['source'] = 'file:/old/plugins/GutAnalysisToolbox_test.jar'
            with self.assertRaises(ValueError): fresh.verify_installed_registration(startup, path)

    def test_new_workflow_cannot_publish_release_or_claim_full_workflow_pass(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (root / '.github/workflows/native-mac-final-package.yml').read_text()
        self.assertIn('--installation-only', workflow)
        self.assertIn('contents: read', workflow)
        self.assertNotIn('contents: write', workflow)
        self.assertNotIn('gh release', workflow)
        self.assertIn('gat-unreleased-final-candidate-', workflow)
        self.assertNotIn('--historical-runtime', workflow)
        diagnostic = (root / '.github/workflows/native-mac-fresh-fiji.yml').read_text()
        self.assertIn("github.event_name == 'workflow_dispatch'", diagnostic)
        self.assertIn('run_fresh_fiji.py', diagnostic)


if __name__ == '__main__':
    unittest.main()
