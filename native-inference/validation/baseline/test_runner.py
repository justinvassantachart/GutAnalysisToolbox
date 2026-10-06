import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('baseline_runner', Path(__file__).with_name('run_workflows.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

class BaselineIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'original'
        self.root.mkdir()
        self.cp = Path(self.temp.name) / 'classpath.txt'
        self.cp.write_text(str(Path(self.temp.name) / 'ij-1.54p.jar'))
    def invoke(self, answers):
        with patch.object(runner, 'command', side_effect=answers):
            return runner.validate_baseline(self.root, self.cp)
    def test_exact_clean_baseline_accepted(self):
        self.assertFalse(self.invoke([runner.BASELINE_COMMIT, ''])['tracked_source_changes'])
    def test_wrong_revision_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Wrong baseline'):
            self.invoke(['0'*40])
    def test_modified_source_rejected(self):
        with self.assertRaisesRegex(ValueError, 'modified'):
            self.invoke([runner.BASELINE_COMMIT, ' M src/main/java/Features/Core/PluginCalls.java'])
    def test_fork_classes_rejected(self):
        (self.root / 'target/classes/Features/Inference').mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, 'Fork inference'):
            self.invoke([runner.BASELINE_COMMIT, ''])
    def test_modern_tf_dependency_rejected(self):
        self.cp.write_text('/some/cache/tensorflow-core-api-1.2.0.jar')
        with self.assertRaisesRegex(ValueError, 'Modern native-worker'):
            self.invoke([runner.BASELINE_COMMIT, ''])
    def test_fork_classpath_entry_rejected(self):
        self.cp.write_text(str(runner.FORK / 'target/classes'))
        with self.assertRaisesRegex(ValueError, 'Fork classpath'):
            self.invoke([runner.BASELINE_COMMIT, ''])

if __name__ == '__main__': unittest.main()
