import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SPEC = importlib.util.spec_from_file_location('ci_runtime', Path(__file__).resolve().parents[1] / 'prepare_ci_runtime.py')
ci = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(ci)


class RuntimePreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def jar(self, name, entries=()):
        path = self.root / name
        with zipfile.ZipFile(path, 'w') as archive:
            for entry in entries:
                archive.writestr(entry, b'synthetic unit test only')
        return path
    def dependencies(self):
        return [self.jar(name) for name in sorted(ci.REQUIRED)]

    def test_pinned_parent_runtime_accepted(self):
        ci.validate_dependencies(self.dependencies())
    def test_modern_protobuf_rejected_before_a_model_can_run(self):
        paths = self.dependencies() + [self.jar('protobuf-java-4.32.0.jar')]
        with self.assertRaises(ValueError): ci.validate_dependencies(paths)
    def test_missing_legacy_tensorflow_rejected(self):
        paths = [p for p in self.dependencies() if p.name != 'libtensorflow-1.15.0.jar']
        with self.assertRaises(ValueError): ci.validate_dependencies(paths)
    def test_worker_or_fork_hidden_in_jar_rejected(self):
        for forbidden in ci.FORBIDDEN:
            paths = self.dependencies() + [self.jar('innocent.jar', [forbidden])]
            with self.subTest(forbidden=forbidden), self.assertRaises(ValueError):
                ci.validate_dependencies(paths)
    def test_cached_hash_mismatch_is_not_replaced(self):
        path = self.root / 'asset'; path.write_bytes(b'wrong')
        with patch.object(ci.subprocess, 'run') as run, self.assertRaises(ValueError):
            ci.fetch('https://publisher.invalid/public', path, hashlib.sha256(b'right').hexdigest())
        run.assert_not_called(); self.assertEqual(b'wrong', path.read_bytes())
    def test_cached_exact_asset_needs_no_download(self):
        path = self.root / 'asset'; path.write_bytes(b'public')
        with patch.object(ci.subprocess, 'run') as run:
            ci.fetch('https://publisher.invalid/public', path, hashlib.sha256(b'public').hexdigest(), 6)
        run.assert_not_called()
    def test_non_https_rejected(self):
        with self.assertRaises(ValueError):
            ci.fetch('http://publisher.invalid/public', self.root / 'asset', '0' * 64)
    def test_failed_download_is_not_committed(self):
        path = self.root / 'asset'
        def wrong_download(*args, **kwargs):
            path.with_name(path.name + '.download').write_bytes(b'incorrect')
        with patch.object(ci.subprocess, 'run', side_effect=wrong_download), self.assertRaises(ValueError):
            ci.fetch('https://publisher.invalid/public', path, '0' * 64)
        self.assertFalse(path.exists())


if __name__ == '__main__': unittest.main()
