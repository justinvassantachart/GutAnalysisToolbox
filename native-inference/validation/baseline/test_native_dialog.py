"""Synthetic dialog controls only; these are not actual GAT workflow evidence."""
import os
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


HERE = Path(__file__).resolve().parent


class NativeDialogObserverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        java_home = Path(os.environ['JAVA_HOME']) / 'bin' if os.environ.get('JAVA_HOME') else None
        cls.java = shutil.which('java') or (str(java_home / 'java') if java_home else None)
        javac = shutil.which('javac') or (str(java_home / 'javac') if java_home else None)
        if not cls.java or not javac:
            raise unittest.SkipTest('Java/Javac required for observer regression controls')
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        subprocess.run([javac, '-encoding', 'UTF-8', '-d', cls.temp.name,
                        str(HERE / 'CsbdeepTensorFlowDialogObserver.java'),
                        str(HERE / 'CsbdeepTensorFlowDialogObserverTest.java')],
                       check=True, capture_output=True, text=True, timeout=30)
        cls.headless = cls.control('headless').stdout.strip() == 'true'

    @classmethod
    def control(cls, mode):
        return subprocess.run([cls.java, '-cp', cls.temp.name,
                               'CsbdeepTensorFlowDialogObserverTest', mode],
                              capture_output=True, text=True, timeout=15)

    def test_exact_signature_and_near_misses(self):
        result = self.control('matchers')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PASS exact match', result.stdout)

    def test_real_visible_modal_is_recorded_without_dismissal(self):
        if self.headless:
            self.skipTest('GUI display required; matcher controls still run headless')
        result = self.control('exact')
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('no option selected or dialog dismissed', result.stdout)
        self.assertNotIn('Library Management action would now be reached', result.stderr)

    def test_other_visible_dialogs_are_not_classified(self):
        if self.headless:
            self.skipTest('GUI display required; matcher controls still run headless')
        for mode in ('precall', 'alignment', 'setup', 'preexisting-visible', 'preexisting-hidden',
                     'wrong-title', 'wrong-message', 'warning', 'nonmodal'):
            with self.subTest(mode=mode):
                result = self.control(mode)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('PASS unclassified GUI control: ' + mode, result.stdout)


class NativeDialogFailurePersistenceTests(unittest.TestCase):
    """Optional actual-handler tests using the same dependencies as the native probe."""
    @classmethod
    def setUpClass(cls):
        dependency_cp = os.environ.get('GAT_BASELINE_TEST_CLASSPATH')
        if not dependency_cp:
            raise unittest.SkipTest('Set GAT_BASELINE_TEST_CLASSPATH to compiled GAT plus native-probe dependencies')
        dependency_cp = os.pathsep.join(dict.fromkeys(dependency_cp.split(os.pathsep)))
        java_home = Path(os.environ['JAVA_HOME']) / 'bin' if os.environ.get('JAVA_HOME') else None
        cls.java = shutil.which('java') or (str(java_home / 'java') if java_home else None)
        javac = shutil.which('javac') or (str(java_home / 'javac') if java_home else None)
        if not cls.java or not javac:
            raise unittest.SkipTest('Java/Javac required for callback controls')
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.cp = cls.temp.name + os.pathsep + dependency_cp
        patchers = [path for path in dependency_cp.split(os.pathsep)
                    if Path(path).name == 'ij1-patcher-2.0.0.jar']
        if len(patchers) != 1:
            raise ValueError('Expected one pinned ImageJ legacy patcher in control classpath')
        cls.patcher = patchers[0]
        subprocess.run([javac, '-encoding', 'UTF-8', '-cp', dependency_cp, '-d', cls.temp.name,
                        str(HERE / 'BaselineNativeProbe.java'),
                        str(HERE / 'CsbdeepTensorFlowDialogObserver.java'),
                        str(HERE / 'BaselineNativeProbeFailureControl.java')],
                       check=True, capture_output=True, text=True, timeout=60)

    def control(self, mode):
        directory = Path(self.temp.name) / mode
        directory.mkdir()
        report = directory / 'synthetic-control.json'
        result = subprocess.run([self.java, '-javaagent:' + self.patcher + '=init',
                                 '--add-opens=java.base/java.lang=ALL-UNNAMED',
                                 '-Djava.awt.headless=true', '-cp', self.cp,
                                 'BaselineNativeProbeFailureControl', mode, str(report)],
                                capture_output=True, text=True, timeout=30)
        return result, json.loads(report.read_text()), report

    def test_failure_evidence_is_saved_before_nonzero_exit(self):
        result, report, path = self.control('recognized')
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertTrue(report['synthetic_validation_control'])
        self.assertEqual(report['status'], 'workflow_failure')
        self.assertEqual(report['stage'], 'observed_CSBDeep_TensorFlow_load_failure_dialog')
        self.assertTrue(report['actual_gat_method_invoked'])
        self.assertEqual(report['native_load_failure_dialog']['message_type'], 0)
        self.assertEqual(report['native_load_failure_dialog']['selected_value'], 'JOptionPane.UNINITIALIZED_VALUE')
        self.assertIn('threads_at_native_load_failure_dialog', report)
        self.assertFalse(path.with_name(path.name + '.pending').exists())
        self.assertFalse(path.with_name('shutdown-hook-ran').exists())

    def test_failed_persistence_keeps_incomplete_previous_snapshot(self):
        result, report, path = self.control('persistence-failure')
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn('Could not persist probe snapshot', result.stderr)
        self.assertEqual(report['status'], 'running')
        self.assertTrue(report['actual_gat_method_invoked'])
        self.assertNotIn('native_load_failure_dialog', report)
        self.assertTrue(path.with_name(path.name + '.pending').is_dir())
        self.assertFalse(path.with_name('shutdown-hook-ran').exists())


if __name__ == '__main__':
    unittest.main()
