import importlib.util
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

spec = importlib.util.spec_from_file_location('package_preview', Path(__file__).parents[1] / 'package-apple-silicon-preview.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class BundleChecks(unittest.TestCase):
    def archive(self, names):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            for name in names:
                z.writestr(name, b'fixture')
        buf.seek(0)
        return zipfile.ZipFile(buf)

    def test_nested_source_preserved(self):
        with self.archive(['worker/', 'worker/source/src/Main.java', 'worker/lib/runtime.jar']) as z:
            self.assertEqual(len(p.checked_entries(z, 'worker')), 2)

    def test_unsafe_paths(self):
        for name in ['../worker/a', '/worker/a', 'worker/../../a', 'other/a', 'worker\\a', 'worker//a', 'worker/./a']:
            with self.subTest(name=name), self.archive([name]) as z:
                with self.assertRaises(ValueError):
                    p.checked_entries(z, 'worker')

    def test_duplicates_rejected(self):
        with self.archive(['worker/a', 'worker/a']) as z:
            with self.assertRaises(ValueError):
                p.checked_entries(z, 'worker')

    def test_symlink_rejected(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            entry = zipfile.ZipInfo('worker/link')
            entry.external_attr = 0o120777 << 16
            z.writestr(entry, 'outside')
        buf.seek(0)
        with zipfile.ZipFile(buf) as z:
            with self.assertRaises(ValueError):
                p.checked_entries(z, 'worker')

    def test_missing_source_and_wrong_platform(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'bundle.zip'
            for names in [
                ['worker/main.jar', 'worker/lib/native-macosx-arm64.jar'],
                ['worker/main.jar', 'worker/source/pom.xml', 'worker/lib/native-linux-x86_64.jar'],
                ['worker/main.jar', 'worker/source/pom.xml', 'worker/lib/native-macosx-arm64.jar', 'worker/lib/native-linux-x86_64.jar'],
            ]:
                with zipfile.ZipFile(path, 'w') as z:
                    for name in names:
                        z.writestr(name, b'fixture')
                with self.subTest(names=names), self.assertRaises(ValueError):
                    p.validate_bundle(path, 'worker', ['worker/main.jar', 'worker/source/pom.xml'], ['native-'])

    def test_jar_class_bytes_must_match_tested_classes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            classes = root / 'classes'
            classes.mkdir()
            (classes / 'Main.class').write_bytes(b'tested')
            jar = root / 'plugin.jar'
            with zipfile.ZipFile(jar, 'w') as z:
                z.writestr('Main.class', b'tested')
            self.assertEqual(p.verify_compiled_classes(jar, classes), 1)
            (classes / 'Main.class').write_bytes(b'different')
            with self.assertRaises(ValueError):
                p.verify_compiled_classes(jar, classes)

    def test_valid_arm_distribution(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'bundle.zip'
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('worker/main.jar', b'fixture')
                z.writestr('worker/source/pom.xml', b'fixture')
                z.writestr('worker/lib/native-macosx-arm64.jar', b'fixture')
            p.validate_bundle(path, 'worker', ['worker/main.jar', 'worker/source/pom.xml'], ['native-'])


if __name__ == '__main__':
    unittest.main()
