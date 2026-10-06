import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock

import check


class ValidationTests(unittest.TestCase):
    def test_cached_hash_mismatch_is_rejected_without_network(self):
        with tempfile.TemporaryDirectory() as root:
            cache = Path(root)
            name = 'native-lib-loader-2.5.0.jar'
            (cache / name).write_bytes(b'corrupted')
            with mock.patch('urllib.request.urlopen') as fetch:
                with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                    check.download(cache, name)
                fetch.assert_not_called()

    def test_exact_cached_hash_is_accepted_without_network(self):
        with tempfile.TemporaryDirectory() as root:
            cache = Path(root)
            data = b'fixture'
            (cache / 'x').write_bytes(data)
            with mock.patch.dict(check.ARTIFACTS, {'x': ('unused', hashlib.sha256(data).hexdigest())}):
                with mock.patch('urllib.request.urlopen') as fetch:
                    self.assertEqual(check.download(cache, 'x'), cache / 'x')
                    fetch.assert_not_called()

    def test_path_traversal_archive_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            archive = root / 'bad.tar'
            with tarfile.open(archive, 'w') as tf:
                entry = tarfile.TarInfo('../outside')
                entry.size = 1
                tf.addfile(entry, io.BytesIO(b'x'))
            with self.assertRaisesRegex(ValueError, 'Unsafe source archive'):
                check.source_from_archive(archive, root)

    def test_source_tree_never_reused(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / ('jxrlib-' + check.COMMIT)).mkdir()
            with self.assertRaisesRegex(ValueError, 'fresh output directory'):
                check.source_from_archive(root / 'unused', root)

    def test_golden_manifest_matches_recorded_reference(self):
        import csv
        manifest = json.loads((check.HERE / 'fixtures.json').read_text())
        with (check.HERE / 'linux-reference.tsv').open() as stream:
            reference = list(csv.DictReader(stream, delimiter='\t'))
        self.assertEqual(len(manifest['fixtures']), 13)
        self.assertEqual(len(reference), 13)
        for fixture, row in zip(manifest['fixtures'], reference):
            for field in ('filename', 'width', 'height', 'bytes_per_pixel', 'input_sha256', 'decoded_md5'):
                self.assertEqual(str(fixture[field]), row[field])
            self.assertEqual(row['status'], 'PASS')
            self.assertEqual(len(row['decoded_sha256']), 64)
            self.assertEqual(len(row['bioformats_sha256']), 64)


if __name__ == '__main__':
    unittest.main()
